#!/usr/bin/env python3
"""
sktop/sktop.py

A Textual TUI for managing Slurm jobs.
To run as 'sltop', create a symlink or alias.
"""

import argparse
import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from typing import List, Dict, Optional, Any

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Label, Static, Button, Log, LoadingIndicator

# Configure logging
logging.basicConfig(level=logging.ERROR, filename="sktop.log")
logger = logging.getLogger("sktop")


class JobManager:
    """Handles interactions with Slurm commands."""

    def __init__(self, user: str):
        self.user = user

    async def get_jobs(self) -> List[Dict[str, Any]]:
        """Fetches jobs for the current user using squeue --json."""
        cmd = ["squeue", "-u", self.user, "--json"]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"squeue error: {stderr.decode()}")
                return []

            data = json.loads(stdout.decode())
            # squeue --json returns a dict with key "jobs" which is a list.
            jobs = data.get("jobs", [])
            return jobs
        except Exception as e:
            logger.error(f"Failed to fetch jobs: {e}")
            return []

    async def cancel_jobs(self, job_ids: List[str]) -> bool:
        """Cancels the specified jobs using scancel."""
        if not job_ids:
            return False
        
        cmd = ["scancel"] + job_ids
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"scancel error: {stderr.decode()}")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to cancel jobs: {e}")
            return False

    async def get_job_details(self, job_id: str) -> Dict[str, str]:
        """Fetches detailed info for a job using scontrol."""
        cmd = ["scontrol", "show", "job", job_id]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"scontrol error: {stderr.decode()}")
                return {}

            # Parse key=value pairs
            details = {}
            output = stdout.decode()
            # Basic parsing - improved regex might be needed for quoted values with spaces
            # But specific fields like StdOut are usually unquoted paths
            for line in output.splitlines():
                parts = line.strip().split()
                for part in parts:
                    if "=" in part:
                        key, value = part.split("=", 1)
                        details[key] = value
            return details
        except Exception as e:
            logger.error(f"Failed to get job details: {e}")
            return {}


class ConfirmScreen(ModalScreen[bool]):
    """A modal screen to confirm an action."""

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(classes="confirm_dialog"):
            yield Label(self.message, classes="confirm_message")
            with Horizontal(classes="confirm_buttons"):
                yield Button("Yes", variant="error", id="yes")
                yield Button("No", variant="primary", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        else:
            self.dismiss(False)


class LogScreen(ModalScreen):
    """A screen to view logs."""
    
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, job_id: str, log_path: str):
        super().__init__()
        self.job_id = job_id
        self.log_path = log_path
        self._tail_process = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(f"Logs for Job {self.job_id}: {self.log_path}", classes="log_title")
        yield Log(id="log_view", highlight=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Log).write(f"Tailing {self.log_path}...\n")
        self.tail_logs()

    @work(exclusive=True, thread=True)
    def tail_logs(self) -> None:
        if not os.path.exists(self.log_path):
            self.app.call_from_thread(self.query_one(Log).write, "Log file not found yet.\n")
            return

        # Use tail -f
        try:
            self._tail_process = subprocess.Popen(
                ["tail", "-f", "-n", "100", self.log_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            if self._tail_process.stdout is None:
                 self.app.call_from_thread(self.query_one(Log).write, "Error: Could not capture stdout.\n")
                 return

            while self._tail_process.poll() is None:
                line = self._tail_process.stdout.readline()
                if line:
                    self.app.call_from_thread(self.query_one(Log).write, line)
                else:
                    # Avoid tight loop if no output
                    import time
                    time.sleep(0.1)
        except Exception as e:
            self.app.call_from_thread(self.query_one(Log).write, f"Error tailing logs: {e}\n")

    async def action_dismiss(self, result: Any = None) -> None:
        if self._tail_process:
            self._tail_process.terminate()
        self.dismiss()


class InspectScreen(ModalScreen):
    """A screen to inspect job details."""
    
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, job_id: str, details: Dict[str, Any]):
        super().__init__()
        self.job_id = job_id
        self.details = details

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(f"Details for Job {self.job_id}", classes="inspect_title")
        
        # Create a clean text representation
        text = "\n".join([f"{k}: {v}" for k, v in self.details.items()])
        
        container = VerticalScroll(classes="inspect_container")
        with container:
            yield Static(text)
        
        yield Footer()

    async def action_dismiss(self, result: Any = None) -> None:
        self.dismiss()


class SltopApp(App):
    """The main application class."""

    CSS = """
    Screen {
        layout: vertical;
    }
    
    DataTable {
        height: 1fr;
        border: solid green;
    }
    
    .confirm_dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 60;
        height: 11;
        border: thick $background 80%;
        background: $surface;
    }
    
    .confirm_message {
        column-span: 2;
        height: 1fr;
        content-align: center middle;
    }
    
    .confirm_buttons {
        column-span: 2;
        align: center bottom;
    }

    .log_title {
        padding: 1;
        background: $boost;
    }

    Log {
        height: 1fr;
        border: solid blue;
    }

    .inspect_container {
        height: 1fr;
        border: solid green;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("space", "toggle_select", "Select"),
        Binding("x", "kill_job", "Kill"),
        Binding("u", "view_logs", "Logs"),
        Binding("i", "inspect_job", "Inspect"),
        Binding("r", "refresh_now", "Refresh"),
    ]

    def __init__(self, user: str, refresh_rate: float):
        super().__init__()
        self.user = user
        self.refresh_rate = refresh_rate
        self.job_manager = JobManager(user)
        self.selected_jobs = set()  # Set of job IDs

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield DataTable(cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"Slurm-Top (User: {self.user})"
        table = self.query_one(DataTable)
        table.add_columns("JOBID", "PARTITION", "NAME", "STATE", "TIME", "NODELIST(REASON)")
        
        # Initial load
        self.refresh_jobs()
        # Set interval
        self.set_interval(self.refresh_rate, self.refresh_jobs)

    def format_time_used(self, start_time: int, state: str) -> str:
        if state != "RUNNING":
            return "0:00"
        
        now = int(time.time())
        diff = now - start_time
        
        if diff < 0:
            return "0:00"
            
        m, s = divmod(diff, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        
        if d > 0:
            return f"{d}-{h:02d}:{m:02d}:{s:02d}"
        elif h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        else:
            return f"{m}:{s:02d}"

    @work(exclusive=True)
    async def refresh_jobs(self) -> None:
        await self.refresh_jobs_async()

    async def refresh_jobs_async(self) -> None:
        jobs = await self.job_manager.get_jobs()
        
        table = self.query_one(DataTable)
        
        # Store current cursor/selection state if needed, but for now simple clear/add
        # To make it smoother, we could update rows, but clear() is easier for MVP
        
        # Preserve selection
        current_row_key = None
        try:
            if table.row_count > 0:
                current_row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        except:
            pass

        table.clear()
        
        for job in jobs:
            # Map JSON keys to columns
            # Keys from squeue --json: "job_id", "partition", "name", "job_state", "time_used", "nodes" (or "reason" if pending)
            
            job_id = str(job.get("job_id", ""))
            partition = job.get("partition", "")
            name = job.get("name", "")
            state = job.get("job_state", "")
            start_time = job.get("start_time", 0)
            time_used = self.format_time_used(start_time, state)
            
            # Filter out cancelled/completed jobs if desired
            if state in ["CANCELLED", "COMPLETED", "FAILED", "TIMEOUT"]:
                continue
            
            # Logic for NodeList vs Reason
            nodes = job.get("nodes", "")
            reason = job.get("job_reason", "") # specific reason field if present
            
            # If state is PENDING, show reason, else nodes
            if state == "PENDING":
                last_col = f"({reason})" if reason else "(PENDING)"
            else:
                last_col = nodes
            
            # Styling row if selected
            label = None
            if job_id in self.selected_jobs:
                # Textual DataTable doesn't support row styling easily via simple add_row
                # We can use styled text
                # Or just mark it in the UI with a symbol
                job_id_display = f"[bold green]* {job_id}[/]"
            else:
                job_id_display = job_id

            table.add_row(
                job_id_display, 
                partition, 
                name, 
                state, 
                time_used, 
                last_col, 
                key=job_id
            )

        # Restore cursor if possible
        if current_row_key:
            try:
                row_index = table.get_row_index(current_row_key)
                table.move_cursor(row=row_index)
            except Exception:
                pass

    def action_toggle_select(self) -> None:
        table = self.query_one(DataTable)
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            job_id = row_key.value
            
            if job_id in self.selected_jobs:
                self.selected_jobs.remove(job_id)
            else:
                self.selected_jobs.add(job_id)
            
            self.refresh_jobs()
        except Exception:
            pass

    def action_kill_job(self) -> None:
        table = self.query_one(DataTable)
        targets = list(self.selected_jobs)
        
        if not targets:
            # If no selection, target the highlighted row
            try:
                row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
                targets = [row_key.value]
            except:
                return

        if not targets:
            return

        def check_confirm(confirmed: Optional[bool]) -> None:
            if confirmed:
                self.do_kill_jobs(targets)

        self.push_screen(
            ConfirmScreen(f"Are you sure you want to cancel {len(targets)} job(s)?"),
            check_confirm
        )

    @work
    async def do_kill_jobs(self, job_ids: List[str]) -> None:
        success = await self.job_manager.cancel_jobs(job_ids)
        if success:
            self.notify(f"Cancelled {len(job_ids)} jobs.")
            self.selected_jobs.clear() # Clear selection after action
            await self.refresh_jobs_async()
        else:
            self.notify("Failed to cancel some jobs.", severity="error")

    @work
    async def action_view_logs(self) -> None:
        table = self.query_one(DataTable)
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            job_id = row_key.value
        except:
            return

        details = await self.job_manager.get_job_details(job_id)
        # Scontrol keys are usually PascalCase or similar
        # StdOut, StdErr, or WorkDir/JobName to guess
        log_path = details.get("StdOut")
        
        if not log_path or log_path == "(null)":
            # Fallback check WorkDir + Name
            work_dir = details.get("WorkDir", ".")
            job_name = details.get("JobName", "slurm")
            # This is a guess, standard Slurm defaults are slurm-%j.out
            log_path = os.path.join(work_dir, f"slurm-{job_id}.out")

        self.app.push_screen(LogScreen(job_id, log_path))

    @work
    async def action_inspect_job(self) -> None:
        table = self.query_one(DataTable)
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            job_id = row_key.value
        except:
            return

        details = await self.job_manager.get_job_details(job_id)
        self.app.push_screen(InspectScreen(job_id, details))

    def action_refresh_now(self) -> None:
        self.refresh_jobs()


def main():
    parser = argparse.ArgumentParser(description="Slurm-Top: A TUI for Slurm.")
    parser.add_argument("-r", "--refresh", type=float, default=5.0, help="Refresh interval in seconds")
    parser.add_argument("-u", "--user", type=str, default=os.getenv("USER"), help="User to monitor")
    
    args = parser.parse_args()

    app = SltopApp(user=args.user, refresh_rate=args.refresh)
    app.run()


if __name__ == "__main__":
    main()
