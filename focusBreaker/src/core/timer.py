"""
Timer Module - Work and Break Timer Logic
"""

import logging
import time
import threading
from datetime import datetime
from typing import Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)

class TimerState(Enum):
    """Timer states"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"

class Timer:
    """Base timer class for tracking time intervals"""
    
    def __init__(self, duration_minutes: float, on_tick: Optional[Callable] = None, 
                 on_complete: Optional[Callable] = None):
        """Initialize timer"""
        try:
            self.duration_minutes = duration_minutes
            self.duration_seconds = duration_minutes * 60
            self.on_tick = on_tick
            self.on_complete = on_complete
            self.state = TimerState.STOPPED
            self.start_time = None
            self.pause_time = None
            self.paused_duration = 0.0
            self.elapsed_seconds = 0
            self._thread = None
            self._stop_event = threading.Event()

            self._start_monotonic = None
            self._pause_monotonic = None
        except Exception as e:
            logger.error(f"Error initializing timer: {e}")
            raise
    
    def start(self):
        """Start the timer"""
        try:
            if self.state == TimerState.RUNNING:
                return
            
            self.start_time = datetime.now()
            self._start_monotonic = time.perf_counter()
            self.state = TimerState.RUNNING
            self._stop_event.clear()

            self._thread = threading.Thread(target=self._run, daemon = True, name = "TimerThread")

            self._thread.start()
        except Exception as e:
            logger.error(f"Error starting timer: {e}")
            self.state = TimerState.STOPPED
    
    def pause(self):
        """Pause the timer"""
        try:
            if self.state != TimerState.RUNNING:
                return
            self.pause_time = datetime.now()
            self._pause_monotonic = time.perf_counter()
            self.state = TimerState.PAUSED
        except Exception as e:
            logger.error(f"Error pausing timer: {e}")

    def resume(self):
        """Resume from pause"""
        try:
            if self.state != TimerState.PAUSED:
                return
           
            assert self._pause_monotonic is not None
            paused_for = time.perf_counter() - self._pause_monotonic
            self.paused_duration += paused_for
            self._pause_monotonic = None
            self.pause_time = None
            self.state = TimerState.RUNNING
        except Exception as e:
            logger.error(f"Error resuming timer: {e}")
            self.state = TimerState.PAUSED

    def stop(self):
        """Stop the timer"""
        try:
            self.state = TimerState.STOPPED

            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout = 1.0)
        except Exception as e:
            logger.error(f"Error stopping timer: {e}")
            self.state = TimerState.STOPPED
    
    def reset(self):
        """Reset to initial state"""
        try:
            self.stop()

            self.start_time = None
            self._start_monotonic = None
            self.pause_time = None
            self._pause_monotonic = None
            self.paused_duration = 0.0
            self.elapsed_seconds = 0
            self.state = TimerState.STOPPED
        except Exception as e:
            logger.error(f"Error resetting timer: {e}")
            # Force reset state even if error
            self.state = TimerState.STOPPED
    
    def get_elapsed_seconds(self) -> int:
        """Get elapsed time in seconds"""
        try:
            if self.state == TimerState.STOPPED:
                return 0
            
            elif self.state == TimerState.PAUSED:
                return self.elapsed_seconds
            
            elif self.state == TimerState.COMPLETED:
                return int(self.duration_seconds)
            
            elif self.state == TimerState.RUNNING:
                assert self._start_monotonic is not None
                total_time = time.perf_counter() - self._start_monotonic
                elapsed = total_time - self.paused_duration
                return int(elapsed)
            
            else:
                return int(self.elapsed_seconds)
        except Exception as e:
            logger.error(f"Error getting elapsed seconds: {e}")
            return 0
    
    def get_remaining_seconds(self) -> int:
        """Get remaining time in seconds"""
        try:
            remaining = self.duration_seconds - self.get_elapsed_seconds()

            return int(max(0, remaining))
        except Exception as e:
            logger.error(f"Error getting remaining seconds: {e}")
            return 0
    
    def get_elapsed_minutes(self) -> float:
        """Get elapsed time in minutes"""
        try:
            elapsed_seconds = self.get_elapsed_seconds()
            elapsed_minutes = elapsed_seconds / 60.0

            return elapsed_minutes
        except Exception as e:
            logger.error(f"Error getting elapsed minutes: {e}")
            return 0.0
    
    def get_remaining_minutes(self) -> int:
        """Get remaining time in minutes"""
        try:
            remaining_seconds = self.get_remaining_seconds()
            remaining_minutes = remaining_seconds // 60

            return int(remaining_minutes)
        except Exception as e:
            logger.error(f"Error getting remaining minutes: {e}")
            return 0
    
    def get_progress_percentage(self) -> float:
        """Get progress as percentage (0-100)"""
        try:
            if self.duration_seconds == 0:
                return 100.0
            
            progress = (self.get_elapsed_seconds() / self.duration_seconds) * 100
            
            return max(0.0, min(100.0, progress))
        except Exception as e:
            logger.error(f"Error getting progress percentage: {e}")
            return 0.0
    
    def is_completed(self) -> bool:
        """Check if timer completed"""
        try:
            return self.state == TimerState.COMPLETED
        except Exception as e:
            logger.error(f"Error checking if timer is completed: {e}")
            return False
    
    def is_running(self) -> bool:
        """Check if timer is running"""
        try:
            return self.state == TimerState.RUNNING
        except Exception as e:
            logger.error(f"Error checking if timer is running: {e}")
            return False
    
    def is_paused(self) -> bool:
        """Check if timer is paused"""
        try:
            return self.state == TimerState.PAUSED
        except Exception as e:
            logger.error(f"Error checking if timer is paused: {e}")
            return False
    
    def _run(self):
        """Internal - runs in background thread"""
        try:
            while not self._stop_event.is_set():
                if self.state == TimerState.RUNNING:
                    self.elapsed_seconds = self.get_elapsed_seconds()

                    # Check if completed
                    if self.elapsed_seconds >= self.duration_seconds:
                        self.state = TimerState.COMPLETED
                        if self.on_complete:
                            self.on_complete()
                        break
                    
                    # Call tick callback
                    if self.on_tick:
                        self.on_tick(self.elapsed_seconds)
                    
                    time.sleep(1)
                else:
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in timer background thread: {e}")
            self.state = TimerState.STOPPED

class WorkTimer(Timer):
    """Timer for work intervals - tracks when breaks should occur"""
    
    def __init__(self, duration_minutes: float, break_times: list[float], 
                 on_tick: Optional[Callable] = None,
                 on_complete: Optional[Callable] = None,
                 on_break_time: Optional[Callable] = None):
        """Initialize work timer with break times"""
        try:
            super().__init__(duration_minutes, on_tick, on_complete)
            self.break_times = sorted(break_times)
            self.on_break_time = on_break_time
            self.triggered_breaks = set()
        except Exception as e:
            logger.error(f"Error initializing work timer: {e}")
            raise
    
    def check_break_time(self) -> Optional[int]:
        """Check if it's time for a break - returns break index or None"""
        try:
            elapsed_minutes = self.get_elapsed_minutes()

            for i, break_time in enumerate(self.break_times):
                if elapsed_minutes >= break_time and i not in self.triggered_breaks:
                    self.triggered_breaks.add(i)  
                    return i
            return None
        except Exception as e:
            logger.error(f"Error checking break time: {e}")
            return None
    
    def update_break_times(self, new_break_times: list):
        """Update break times (for snooze redistribution)"""
        try:
            self.break_times = sorted(new_break_times)
        except Exception as e:
            logger.error(f"Error updating break times: {e}")
            self.break_times = []

    def _run(self):
        """Override to add break checking"""
        try:
            while not self._stop_event.is_set():
                if self.state == TimerState.RUNNING:
                    self.elapsed_seconds = self.get_elapsed_seconds()
                    
                    # Check for break time
                    break_index = self.check_break_time()
                    if break_index is not None and self.on_break_time:
                        self.on_break_time(break_index)
                    
                    # Check if completed
                    if self.elapsed_seconds >= self.duration_seconds:
                        self.state = TimerState.COMPLETED
                        if self.on_complete:
                            self.on_complete()
                        break
                    
                    # Call tick callback
                    if self.on_tick:
                        self.on_tick(self.elapsed_seconds)
                
                    time.sleep(1)

                else:
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in work timer background thread: {e}")
            self.state = TimerState.STOPPED

class BreakTimer(Timer):
    """Timer for break intervals - counts down break duration"""
    
    def __init__(self, duration_minutes: float,
                 on_tick: Optional[Callable] = None,
                 on_complete: Optional[Callable] = None,
                 on_warning: Optional[Callable] = None,
                 warning_seconds: int = 60):
        """Initialize break timer with optional warning"""
        try:
            super().__init__(duration_minutes, on_tick, on_complete)
            self.on_warning = on_warning
            self.warning_seconds = warning_seconds
            self.warning_triggered = False
        except Exception as e:
            logger.error(f"Error initializing break timer: {e}")
            raise

    def _run(self):
        """Internal - runs in background thread"""
        try:
            while not self._stop_event.is_set():
                if self.state == TimerState.RUNNING:
                    self.elapsed_seconds = self.get_elapsed_seconds()
                    
                    remaining_seconds = self.get_remaining_seconds()
                    
                    # Check for warnings
                    if not self.warning_triggered and remaining_seconds <= self.warning_seconds:
                        self.warning_triggered = True
                        if self.on_warning:
                            self.on_warning(remaining_seconds)
                
                    # Check if completed
                    if self.elapsed_seconds >= self.duration_seconds:
                        self.state = TimerState.COMPLETED
                        if self.on_complete:
                            self.on_complete()
                        break

                    # Call tick callback
                    if self.on_tick:
                        self.on_tick(self.elapsed_seconds)
            
                    time.sleep(1)
                
                else:
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in break timer background thread: {e}")
            self.state = TimerState.STOPPED

# Utility functions
def format_time(seconds: int) -> str:
    """Format seconds into MM:SS or HH:MM:SS"""
    try:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    except Exception as e:
        logger.error(f"Error formatting time for {seconds} seconds: {e}")
        return "00:00"

def seconds_to_minutes(seconds: int) -> int:
    """Convert seconds to minutes"""
    try:
        return (seconds + 59) // 60
    except Exception as e:
        logger.error(f"Error converting {seconds} seconds to minutes: {e}")
        return 0

def minutes_to_seconds(minutes: int) -> int:
    """Convert minutes to seconds"""
    try:
        return minutes * 60
    except Exception as e:
        logger.error(f"Error converting {minutes} minutes to seconds: {e}")
        return 0