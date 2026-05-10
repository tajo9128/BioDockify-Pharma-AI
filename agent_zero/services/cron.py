"""
Cron Service for Agent Zero.
Allows the agent to schedule recurring tasks.
Ported from NanoBot.
"""
import asyncio
import json
import time
import uuid
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Coroutine, Any

logger = logging.getLogger(__name__)

# --- Types ---

@dataclass
class CronJob:
    id: str
    name: str
    schedule_expr: str # "every 10s", "at 12:00", or cron string
    instruction: str
    enabled: bool = True
    next_run: float = 0.0

# --- Service ---

class CronService:
    def __init__(self, workspace_path: str, on_trigger: Callable[[str], Coroutine]):
        self.store_path = os.path.join(workspace_path, "cron_jobs.json")
        self.on_trigger = on_trigger
        self.jobs: List[CronJob] = []
        self._running = False
        self._task = None
        
    async def start(self):
        self._load()
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("CronService started.")

    async def stop(self):
        self._running = False
        if self._task: self._task.cancel()

    def _load(self):
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, 'r') as f:
                    data = json.load(f)
                    self.jobs = [CronJob(**j) for j in data]
            except Exception as e:
                logger.error(f"Failed to load cron jobs: {e}")

    def _save(self):
        try:
            with open(self.store_path, 'w') as f:
                json.dump([j.__dict__ for j in self.jobs], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cron jobs: {e}")

    def add_job(self, name: str, schedule: str, instruction: str) -> str:
        job = CronJob(
            id=str(uuid.uuid4())[:8],
            name=name,
            schedule_expr=schedule,
            instruction=instruction,
            next_run=time.time() + self._parse_schedule(schedule)
        )
        self.jobs.append(job)
        self._save()
        return f"Job '{name}' added (ID: {job.id})"

    def list_jobs(self) -> str:
        if not self.jobs: return "No scheduled jobs."
        return "\n".join([f"[{j.id}] {j.name} ({j.schedule_expr}): {j.instruction}" for j in self.jobs])

    def remove_job(self, job_id: str) -> str:
        self.jobs = [j for j in self.jobs if j.id != job_id]
        self._save()
        return f"Job {job_id} removed."

    def _parse_schedule(self, expr: str) -> float:
        # Simple parser for "every X [s|m|h]"
        # Robust parsing would use croniter, but kept simple for now
        try:
            parts = expr.split()
            if parts[0] == "every":
                val = int(parts[1])
                unit = parts[2].lower() if len(parts) > 2 else "s"
                if "m" in unit: val *= 60
                elif "h" in unit: val *= 3600
                return val
        except:
            pass
        return 60.0 # Default 60s fallback

    async def _loop(self):
        while self._running:
            now = time.time()
            for job in self.jobs:
                if job.enabled and job.next_run <= now:
                    logger.info(f"Triggering cron job: {job.name}")
                    # Trigger Agent
                    asyncio.create_task(self.on_trigger(
                        f"SYSTEM ALERT (CRON): Time to run scheduled task '{job.name}'.\nInstruction: {job.instruction}"
                    ))
                    
                    # Reschedule
                    interval = self._parse_schedule(job.schedule_expr)
                    job.next_run = now + interval
                    self._save()
            
            await asyncio.sleep(5)
