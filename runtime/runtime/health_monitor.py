"""
BioDockify Health Monitor
part of Phase 1: The Body

Responsible for keeping the "Always-On" agent healthy and unobtrusive.
- Monitors Ollama connectivity
- Checks Battery status to prevent drain
- Manages resource usage (placeholder)
"""

import time
import requests
import psutil
import logging
import threading
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class HealthMonitor:
    def __init__(self, check_url: str = "http://localhost:1234/v1/models"):
        self.check_url = check_url
        self.running = False
        self.status = {
            "local_ai_connected": False,
            "on_battery": False,
            "battery_percent": 100,
            "paused_by_system": False
        }
        self.thread = None
        self._pause_callbacks = []
        self._resume_callbacks = []

    def start(self):
        """Starts the background monitoring thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("Health Monitor started.")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def on_pause_request(self, callback: Callable):
        """Register a callback to be triggered when system needs to pause."""
        self._pause_callbacks.append(callback)

    def on_resume_request(self, callback: Callable):
        """Register a callback for resuming."""
        self._resume_callbacks.append(callback)

    def _monitor_loop(self):
        while self.running:
            self._check_local_ai()
            self._check_battery()
            time.sleep(60) # Check every minute

    def _check_local_ai(self):
        try:
            prev_status = self.status["local_ai_connected"]
            # Just a fast ping to LM Studio
            requests.get(self.check_url, timeout=2)
            self.status["local_ai_connected"] = True
            
            if not prev_status:
                logger.info("Local AI (LM Studio) connection restored.")
                
        except requests.ConnectionError:
            if self.status["local_ai_connected"]:
                logger.warning("Local AI (LM Studio) connection lost!")
            self.status["local_ai_connected"] = False

    def _check_battery(self):
        try:
            battery = psutil.sensors_battery()
            if battery:
                self.status["on_battery"] = not battery.power_plugged
                self.status["battery_percent"] = battery.percent
                
                # Logic: Pause if < 20% and not plugged in
                should_pause = self.status["on_battery"] and self.status["battery_percent"] < 20
                
                if should_pause and not self.status["paused_by_system"]:
                    logger.warning(f"Low Battery ({battery.percent}%) detected. Requesting agent pause.")
                    self.status["paused_by_system"] = True
                    self._trigger_pause()
                elif not should_pause and self.status["paused_by_system"]:
                    logger.info("Power restored. Resuming agent.")
                    self.status["paused_by_system"] = False
                    self._trigger_resume()
                    
        except Exception as e:
            logger.error(f"Battery check failed: {e}")

    def _trigger_pause(self):
        for cb in self._pause_callbacks:
            try:
                cb()
            except Exception as e:
                logger.error(f"Error in pause callback: {e}")

    def _trigger_resume(self):
        for cb in self._resume_callbacks:
            try:
                cb()
            except Exception as e:
                logger.error(f"Error in resume callback: {e}")

if __name__ == "__main__":
    # Test run
    logging.basicConfig(level=logging.INFO)
    hm = HealthMonitor()
    hm.start()
    try:
        while True:
            print(hm.status)
            time.sleep(5)
    except KeyboardInterrupt:
        hm.stop()
