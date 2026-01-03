"""
Session Manager Module - Core Session Lifecycle Management
Handles creating, running, pausing, extending, and completing work sessions
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any
from data.db import DBManager
from data.models import WorkSession, Break
from core.timer import WorkTimer, BreakTimer
from core.scheduler import get_work_interval_for_mode, get_break_duration_for_mode
from core.mode_controller import (
    can_extend_session, requires_cooldown, get_cooldown_duration,
    has_breaks_during_work
)
from core.streak_manager import update_streaks_after_session

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages the complete lifecycle of a work session"""
    
    def __init__(self, db: DBManager):
        """Initialize session manager"""
        self.db = db
        self.active_session_id: Optional[int] = None
        self.work_timer: Optional[WorkTimer] = None
        self.break_timer: Optional[BreakTimer] = None
        self.cooldown_timer: Optional[BreakTimer] = None
        self.current_break_id: Optional[int] = None
        self.is_in_break = False
        self.is_in_cooldown = False
        
        self.on_work_tick: Optional[Callable[[int], None]] = None
        self.on_break_tick: Optional[Callable[[int], None]] = None
        self.on_break_warning: Optional[Callable[[int], None]] = None
        self.on_break_triggered: Optional[Callable[[int], None]] = None
        self.on_break_complete: Optional[Callable[[], None]] = None
        self.on_session_complete: Optional[Callable[[], None]] = None
        self.on_cooldown_tick: Optional[Callable[[int], None]] = None
        self.on_cooldown_complete: Optional[Callable[[], None]] = None
        
        logger.info("SessionManager initialized")
    
    # =================================== SESSION CREATION ====================================
    def create_session(self, task_id: int) -> int:
        """Create a new work session for a given task"""
        try:
            # Get task details
            task = self.db.getTask(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            # Get settings for snooze passes
            settings = self.db.getSettings()
            if not settings:
                raise ValueError("Settings not found")
            
            # Create session object
            now = datetime.now()
            session = WorkSession(
                id=None,
                task_id=task_id,
                start_time=now.isoformat(),
                end_time=None,
                planned_duration_minutes=task.allocated_time_minutes,
                actual_duration_minutes=None,
                mode=task.mode,
                status='in_progress',
                breaks_taken=0,
                breaks_snoozed=0,
                breaks_skipped=0,
                extended_count=0,
                emergency_exits=0,
                snooze_passes_remaining=settings.max_snooze_passes,
                archived=False,
                created_at=now.isoformat()
            )
            
            # Save to database
            session_id = self.db.createSession(session)
            
            # Schedule breaks if mode has breaks during work
            if has_breaks_during_work(task.mode):
                self.db.scheduleBreaksForSessions(
                    session_id,
                    task.mode,
                    task.allocated_time_minutes
                )
            
            # Log event
            self.db.logSessionEvent(
                'session_created',
                session_id,
                details={
                    'mode': task.mode,
                    'duration': task.allocated_time_minutes,
                    'task_name': task.name
                },
                user_message=f"Started {task.mode} session: {task.name}"
            )
            
            logger.info(f"Created session {session_id} for task {task_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session for task {task_id}: {e}")
            raise

    def start_session(self, session_id: int):
        """
        Start an active work session with timer
        
        Args:
            session_id: ID of session to start
            
        Raises:
            ValueError: If session not found or already active
        """
        try:
            # Check if another session is active
            if self.active_session_id is not None:
                raise ValueError("Another session is already active")
            
            # Get session details
            session = self.db.getSession(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            # Get break schedule
            break_times = []
            if has_breaks_during_work(session.mode):
                breaks = self.db.getSessionBreaks(session_id)
                start_time = datetime.fromisoformat(session.start_time)
                
                for break_obj in breaks:
                    scheduled = datetime.fromisoformat(break_obj.scheduled_time)
                    minutes_until = (scheduled - start_time).total_seconds() / 60
                    break_times.append(minutes_until)
            
            # Create work timer
            self.work_timer = WorkTimer(
                duration_minutes=session.planned_duration_minutes,
                break_times=break_times,
                on_tick=self._on_work_timer_tick,
                on_complete=self._on_work_timer_complete,
                on_break_time=self._on_break_time_triggered
            )
            
            # Start timer
            self.active_session_id = session_id
            self.work_timer.start()
            
            # Log event
            self.db.logSessionEvent(
                'session_started',
                session_id,
                user_message=f"Work session started in {session.mode} mode"
            )
            
            logger.info(f"Started session {session_id}")
            
        except Exception as e:
            logger.error(f"Error starting session {session_id}: {e}")
            self.active_session_id = None
            self.work_timer = None
            raise
        
    # ==================================== TIMER CALLBACKS ====================================
    def _on_work_timer_tick(self, elapsed_seconds: int):
        """Called every second during work"""
        if self.on_work_tick:
            self.on_work_tick(elapsed_seconds)
    
    def _on_work_timer_complete(self):
        """Called when work session time is complete"""
        try:
            if self.active_session_id is None:
                return
            
            session = self.db.getSession(self.active_session_id)
            if not session:
                return
            
            # Calculate actual duration
            start_time = datetime.fromisoformat(session.start_time)
            now = datetime.now()
            actual_duration = int((now - start_time).total_seconds() / 60)
            
            # Update session
            self.db.updateSession(
                self.active_session_id,
                end_time=now.isoformat(),
                actual_duration_minutes=actual_duration
            )
            
            # Check if cooldown is required
            if requires_cooldown(session.mode):
                self._start_cooldown()
            else:
                # Complete session immediately
                self._complete_session_internal()
            
            logger.info(f"Work timer completed for session {self.active_session_id}")
            
        except Exception as e:
            logger.error(f"Error handling work timer completion: {e}")
    
    def _on_break_time_triggered(self, break_index: int):
        """Called when it's time for a break"""
        try:
            if self.active_session_id is None:
                return
            
            # Get the next pending break
            next_break = self.db.getNextPendingBreak(self.active_session_id)
            if not next_break:
                logger.warning("Break triggered but no pending break found")
                return
            
            # Pause work timer
            if self.work_timer:
                self.work_timer.pause()
            
            if next_break.id is None:
                logger.warning("Next break has no ID")
                return
    
            # Start break
            self._start_break(next_break.id)
            
            # Notify UI
            if self.on_break_triggered:
                self.on_break_triggered(next_break.id)
            
            logger.info(f"Break triggered for session {self.active_session_id}")
            
        except Exception as e:
            logger.error(f"Error triggering break: {e}")

    # =================================== BREAK MANAGEMENT ====================================
    def _start_break(self, break_id: int):
        """Start a break timer"""
        try:
            break_obj = self.db.getBreak(break_id)
            if not break_obj:
                raise ValueError(f"Break {break_id} not found")
            
            # Create break timer
            self.break_timer = BreakTimer(
                duration_minutes=break_obj.duration_minutes,
                on_tick=self._on_break_timer_tick,
                on_complete=self._on_break_timer_complete,
                on_warning=self._on_break_warning,
                warning_seconds=60
            )
            
            # Update state
            self.current_break_id = break_id
            self.is_in_break = True
            
            # Update database
            self.db.updateBreak(
                break_id,
                actual_time=datetime.now().isoformat(),
                status='in_progress'
            )
            
            # Start timer
            self.break_timer.start()
            
            # Log event
            if self.active_session_id:
                self.db.logBreakEvent(
                    'break_started',
                    self.active_session_id,
                    break_id,
                    user_message="Break started"
                )
            
            logger.info(f"Started break {break_id}")
            
        except Exception as e:
            logger.error(f"Error starting break {break_id}: {e}")
            raise
    
    def _on_break_timer_tick(self, elapsed_seconds: int):
        """Called every second during break"""
        if self.on_break_tick:
            self.on_break_tick(elapsed_seconds)
    
    def _on_break_warning(self, remaining_seconds: int):
        """Called when break is about to end (1 minute warning)"""
        if self.on_break_warning:
            self.on_break_warning(remaining_seconds)
    
    def _on_break_timer_complete(self):
        """Called when break timer completes"""
        try:
            if self.current_break_id is None:
                return
            
            # Mark break as completed
            self.db.updateBreak(self.current_break_id, status='completed')
            
            # Update session
            if self.active_session_id:
                session = self.db.getSession(self.active_session_id)
                if session:
                    self.db.updateSession(
                        self.active_session_id,
                        breaks_taken=session.breaks_taken + 1
                    )
            
            # Log event
            if self.active_session_id:
                self.db.logBreakEvent(
                    'break_completed',
                    self.active_session_id,
                    self.current_break_id,
                    user_message="Break completed naturally"
                )
            
            # Clean up
            self._cleanup_break()
            
            # Resume work timer
            if self.work_timer:
                self.work_timer.resume()
            
            # Notify UI
            if self.on_break_complete:
                self.on_break_complete()
            
            logger.info(f"Break {self.current_break_id} completed")
            
        except Exception as e:
            logger.error(f"Error completing break: {e}")
    
    def take_break(self):
        """User chose to take the break (Normal mode)"""
        try:
            if not self.is_in_break or self.current_break_id is None:
                return
            
            # Let timer run naturally - do nothing
            logger.info("User taking break")
            
        except Exception as e:
            logger.error(f"Error in take_break: {e}")
    
    def snooze_break(self, snooze_duration_minutes: Optional[int] = None):
        """
        User chose to snooze the break
        
        Args:
            snooze_duration_minutes: Optional custom snooze duration
        """
        try:
            if not self.is_in_break or self.current_break_id is None:
                return
            
            if self.active_session_id is None:
                return
            
            # Get settings
            settings = self.db.getSettings()
            if not settings:
                return
            
            if snooze_duration_minutes is None:
                snooze_duration_minutes = settings.normal_snooze_duration_minutes
            
            # Attempt to snooze
            success = self.db.snoozeBreak(
                self.current_break_id,
                self.active_session_id,
                snooze_duration_minutes
            )
            
            if success:
                # Stop break timer
                if self.break_timer:
                    self.break_timer.stop()
                
                # Log event
                self.db.logBreakEvent(
                    'break_snoozed',
                    self.active_session_id,
                    self.current_break_id,
                    details={'snooze_duration': snooze_duration_minutes},
                    user_message=f"Break snoozed for {snooze_duration_minutes} minutes"
                )
                
                # Clean up
                self._cleanup_break()
                
                # Resume work timer
                if self.work_timer:
                    self.work_timer.resume()
                
                logger.info(f"Break {self.current_break_id} snoozed for {snooze_duration_minutes} minutes")
            else:
                logger.warning("Snooze failed - no passes remaining")
                
        except Exception as e:
            logger.error(f"Error snoozing break: {e}")
    
    def skip_break(self):
        """User chose to skip the break (Normal mode only)"""
        try:
            if not self.is_in_break or self.current_break_id is None:
                return
            
            if self.active_session_id is None:
                return
            
            # Mark break as skipped
            self.db.updateBreak(self.current_break_id, status='skipped')
            
            # Update session
            session = self.db.getSession(self.active_session_id)
            if session:
                self.db.updateSession(
                    self.active_session_id,
                    breaks_skipped=session.breaks_skipped + 1
                )
            
            # Stop break timer
            if self.break_timer:
                self.break_timer.stop()
            
            # Log event
            self.db.logBreakEvent(
                'break_skipped',
                self.active_session_id,
                self.current_break_id,
                user_message="Break skipped"
            )
            
            # Clean up
            self._cleanup_break()
            
            # Resume work timer
            if self.work_timer:
                self.work_timer.resume()
            
            logger.info(f"Break {self.current_break_id} skipped")
            
        except Exception as e:
            logger.error(f"Error skipping break: {e}")
    
    def _cleanup_break(self):
        """Clean up break state"""
        self.current_break_id = None
        self.is_in_break = False
        self.break_timer = None

    # ================================= COOLDOWN MANAGEMENT ===================================
    def _start_cooldown(self):
        """Start mandatory cooldown period (Strict/Focused modes)"""
        try:
            if self.active_session_id is None:
                return
            
            session = self.db.getSession(self.active_session_id)
            if not session:
                return
            
            settings = self.db.getSettings()
            if not settings:
                return
            
            # Get cooldown duration
            cooldown_minutes = get_cooldown_duration(session.mode, settings)
            
            # Create cooldown timer
            self.cooldown_timer = BreakTimer(
                duration_minutes=cooldown_minutes,
                on_tick=self._on_cooldown_tick,
                on_complete=self._on_cooldown_complete
            )
            
            # Update state
            self.is_in_cooldown = True
            
            # Start timer
            self.cooldown_timer.start()
            
            # Log event
            self.db.logSessionEvent(
                'cooldown_started',
                self.active_session_id,
                details={'duration': cooldown_minutes},
                user_message=f"Mandatory {cooldown_minutes}-minute cooldown started"
            )
            
            logger.info(f"Started cooldown for session {self.active_session_id}")
            
        except Exception as e:
            logger.error(f"Error starting cooldown: {e}")
    
    def _on_cooldown_tick(self, elapsed_seconds: int):
        """Called every second during cooldown"""
        if self.on_cooldown_tick:
            self.on_cooldown_tick(elapsed_seconds)
    
    def _on_cooldown_complete(self):
        """Called when cooldown completes"""
        try:
            # Log event
            if self.active_session_id:
                self.db.logSessionEvent(
                    'cooldown_completed',
                    self.active_session_id,
                    user_message="Cooldown period completed"
                )
            
            # Clean up cooldown
            self.is_in_cooldown = False
            self.cooldown_timer = None
            
            # Complete session
            self._complete_session_internal()
            
            # Notify UI
            if self.on_cooldown_complete:
                self.on_cooldown_complete()
            
            logger.info("Cooldown completed")
            
        except Exception as e:
            logger.error(f"Error completing cooldown: {e}")
        
    # ================================== SESSION COMPLETION ===================================
    def _complete_session_internal(self):
        """Internal method to complete session"""
        try:
            if self.active_session_id is None:
                return
            
            # Update session status
            self.db.updateSession(
                self.active_session_id,
                status='completed'
            )
            
            # Update streaks
            update_streaks_after_session(self.active_session_id, self.db)
            
            # Log event
            self.db.logSessionEvent(
                'session_completed',
                self.active_session_id,
                user_message="Work session completed successfully"
            )
            
            # Notify UI
            if self.on_session_complete:
                self.on_session_complete()
            
            logger.info(f"Session {self.active_session_id} completed")
            
            # Clean up
            self._cleanup_session()
            
        except Exception as e:
            logger.error(f"Error completing session: {e}")
    
    def complete_session(self):
        """Public method to complete session (called by UI)"""
        self._complete_session_internal()
    
    def _cleanup_session(self):
        """Clean up session state"""
        self.active_session_id = None
        self.work_timer = None
        self.break_timer = None
        self.cooldown_timer = None
        self.current_break_id = None
        self.is_in_break = False
        self.is_in_cooldown = False
    
    # =================================== SESSION EXTENSION ===================================    
    def extend_session(self, additional_minutes: int):
        """
        Extend the current session (Normal mode only)
        
        Args:
            additional_minutes: Minutes to add to session
        """
        try:
            if self.active_session_id is None:
                raise ValueError("No active session")
            
            session = self.db.getSession(self.active_session_id)
            if not session:
                raise ValueError("Session not found")
            
            # Check if mode allows extension
            if not can_extend_session(session.mode):
                raise ValueError(f"Cannot extend session in {session.mode} mode")
            
            # Update session duration
            new_duration = session.planned_duration_minutes + additional_minutes
            self.db.updateSession(
                self.active_session_id,
                planned_duration_minutes=new_duration,
                extended_count=session.extended_count + 1
            )
            
            # Reset snooze passes
            self.db.resetSnoozePasses(self.active_session_id)
            
            # Schedule additional breaks
            settings = self.db.getSettings()
            if settings:
                work_interval = get_work_interval_for_mode(session.mode, settings)
                num_new_breaks = additional_minutes // work_interval
                
                if num_new_breaks > 0:
                    # Calculate when new breaks should occur
                    start_time = datetime.fromisoformat(session.start_time)
                    current_duration = session.planned_duration_minutes - additional_minutes
                    
                    for i in range(num_new_breaks):
                        break_time = start_time + timedelta(
                            minutes=current_duration + (i + 1) * work_interval
                        )
                        
                        break_obj = Break(
                            id=None,
                            session_id=self.active_session_id,
                            scheduled_time=break_time.isoformat(),
                            actual_time=None,
                            duration_minutes=get_break_duration_for_mode(session.mode, settings),
                            status='pending',
                            snooze_count=0,
                            snooze_duration_minutes=0,
                            created_at=datetime.now().isoformat()
                        )
                        
                        self.db.createBreak(break_obj)
            
            # Update work timer
            if self.work_timer:
                self.work_timer.duration_minutes = new_duration
                self.work_timer.duration_seconds = new_duration * 60
                
                # Update break times
                breaks = self.db.getSessionBreaks(self.active_session_id)
                start_time = datetime.fromisoformat(session.start_time)
                break_times = []
                for break_obj in breaks:
                    if break_obj.status == 'pending':
                        scheduled = datetime.fromisoformat(break_obj.scheduled_time)
                        minutes_until = (scheduled - start_time).total_seconds() / 60
                        break_times.append(minutes_until)
                
                self.work_timer.update_break_times(break_times)
            
            # Log event
            self.db.logSessionEvent(
                'session_extended',
                self.active_session_id,
                details={'additional_minutes': additional_minutes},
                user_message=f"Session extended by {additional_minutes} minutes"
            )
            
            logger.info(f"Extended session {self.active_session_id} by {additional_minutes} minutes")
            
        except Exception as e:
            logger.error(f"Error extending session: {e}")
            raise

    # ===================================== STATE QUERIES =====================================
    def get_active_session_id(self) -> Optional[int]:
        """Get ID of active session"""
        return self.active_session_id
    
    def is_session_active(self) -> bool:
        """Check if a session is active"""
        return self.active_session_id is not None
    
    def is_break_active(self) -> bool:
        """Check if currently in a break"""
        return self.is_in_break
    
    def is_cooldown_active(self) -> bool:
        """Check if currently in cooldown"""
        return self.is_in_cooldown
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get current status of session"""
        if self.active_session_id is None:
            return {'active': False}
        
        session = self.db.getSession(self.active_session_id)
        if not session:
            return {'active': False}
        
        status = {
            'active': True,
            'session_id': self.active_session_id,
            'mode': session.mode,
            'is_in_break': self.is_in_break,
            'is_in_cooldown': self.is_in_cooldown,
            'breaks_taken': session.breaks_taken,
            'breaks_snoozed': session.breaks_snoozed,
            'breaks_skipped': session.breaks_skipped,
            'emergency_exits': session.emergency_exits,
            'snooze_passes_remaining': session.snooze_passes_remaining
        }
        
        # Add timer info
        if self.work_timer:
            status['work_elapsed'] = self.work_timer.get_elapsed_seconds()
            status['work_remaining'] = self.work_timer.get_remaining_seconds()
            status['work_progress'] = self.work_timer.get_progress_percentage()
        
        if self.break_timer:
            status['break_elapsed'] = self.break_timer.get_elapsed_seconds()
            status['break_remaining'] = self.break_timer.get_remaining_seconds()
        
        if self.cooldown_timer:
            status['cooldown_elapsed'] = self.cooldown_timer.get_elapsed_seconds()
            status['cooldown_remaining'] = self.cooldown_timer.get_remaining_seconds()
        
        return status
      
    # ===================================== EMERGENCY EXIT ====================================
    def handle_emergency_exit(self, reason: str = "user_triggered"):
        """
        Handle emergency exit during break or cooldown
        
        Args:
            reason: Reason for emergency exit
        """
        try:
            if self.active_session_id is None:
                return
            
            session = self.db.getSession(self.active_session_id)
            if not session:
                return
            
            # Update emergency exit count
            self.db.updateSession(
                self.active_session_id,
                emergency_exits=session.emergency_exits + 1
            )
            
            # Log event
            self.db.logSessionEvent(
                'emergency_exit_used',
                self.active_session_id,
                details={'reason': reason},
                user_message=f"Emergency exit used: {reason}"
            )
            
            # Stop current timers
            if self.is_in_break and self.break_timer:
                self.break_timer.stop()
                self._cleanup_break()
            
            if self.is_in_cooldown and self.cooldown_timer:
                self.cooldown_timer.stop()
                self.is_in_cooldown = False
                self.cooldown_timer = None
            
            # Resume work if in break
            if self.work_timer and self.work_timer.is_running():
                self.work_timer.resume()
            
            logger.info(f"Emergency exit handled for session {self.active_session_id}")
            
        except Exception as e:
            logger.error(f"Error handling emergency exit: {e}")