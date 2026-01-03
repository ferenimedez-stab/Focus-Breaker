"""
Comprehensive test suite for SessionManager using unittest
"""
import unittest
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
sys.path.insert(0, 'i:\\py\\projectBreaker\\focusBreaker\\src')

from typing import Optional
from data.db import DBManager
from data.models import WorkSession, Task, Settings, Break
from core.timer import TimerState
from core.session_manager import SessionManager


class MockDBManager(DBManager):
    """Mock DBManager for testing - inherits from real DBManager"""

    def __init__(self):
        # Don't call super().__init__() to avoid database setup
        self.db_path = ":memory:"
        self.conn = None
        self.sessions: dict[int, WorkSession] = {}
        self.tasks: dict[int, Task] = {}
        self.breaks: dict[int, Break] = {}
        self.settings: Optional[Settings] = None
        self.session_counter = 1
        self.break_counter = 1
        self.events = []

    def getTask(self, task_id: int) -> Optional[Task]:
        return self.tasks.get(task_id)

    def getSettings(self) -> Optional[Settings]:
        return self.settings

    def createSession(self, session):
        session_id = self.session_counter
        self.session_counter += 1
        session.id = str(session_id)  # WorkSession.id is Optional[str]
        self.sessions[session_id] = session
        return session_id

    def getSession(self, session_id: int) -> Optional[WorkSession]:
        return self.sessions.get(session_id)

    def updateSession(self, session_id: int, **kwargs) -> bool:
        if session_id in self.sessions:
            session = self.sessions[session_id]
            for key, value in kwargs.items():
                setattr(session, key, value)
            
            # If completing session, set end_time and actual_duration if not provided
            if kwargs.get('status') == 'completed':
                if not hasattr(session, 'end_time') or session.end_time is None:
                    session.end_time = datetime.now().isoformat()
                if not hasattr(session, 'actual_duration_minutes') or session.actual_duration_minutes is None:
                    start_time = datetime.fromisoformat(session.start_time)
                    session.actual_duration_minutes = int((datetime.now() - start_time).total_seconds() / 60)
            
            return True
        return False

    def getActiveSession(self):
        for session in self.sessions.values():
            if session.status == 'in_progress':
                return session
        return None

    def scheduleBreaksForSessions(self, session_id, mode, duration):
        # Mock implementation - just create some breaks
        pass

    def getNextPendingBreak(self, session_id):
        for break_obj in self.breaks.values():
            if break_obj.session_id == session_id and break_obj.status == 'pending':
                return break_obj
        return None

    def createBreak(self, break_obj):
        break_id = self.break_counter
        self.break_counter += 1
        break_obj.id = break_id
        self.breaks[break_id] = break_obj
        return break_id

    def updateBreak(self, break_id, **kwargs):
        if break_id in self.breaks:
            break_obj = self.breaks[break_id]
            for key, value in kwargs.items():
                setattr(break_obj, key, value)
            return True
        return False

    def snoozeBreak(self, break_id, session_id, snooze_duration_minutes=None):
        if break_id in self.breaks:
            break_obj = self.breaks[break_id]
            break_obj.snooze_count += 1
            break_obj.snooze_duration_minutes = snooze_duration_minutes or 5
            return True
        return False

    def resetSnoozePasses(self, session_id):
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.snooze_passes_remaining = 3  # Reset to default
            return True
        return False

    def getSnoozePassesRemaining(self, session_id: int) -> int:
        if session_id in self.sessions:
            return self.sessions[session_id].snooze_passes_remaining
        return 0

    def logSessionEvent(self, event_type: str, session_id: int, details: Optional[dict] = None, user_message: Optional[str] = None):
        self.events.append({
            'type': event_type,
            'session_id': session_id,
            'details': details or {},
            'user_message': user_message,
            'timestamp': datetime.now()
        })

    def getSessionBreaks(self, session_id: int) -> list[Break]:
        """Get breaks for a session"""
        return [break_obj for break_obj in self.breaks.values() if break_obj.session_id == session_id]

    def getBreak(self, break_id: int) -> Optional[Break]:
        """Get a break by ID"""
        return self.breaks.get(break_id)

    def logBreakEvent(self, event_type: str, session_id: int, break_id: int, details: Optional[dict] = None, user_message: Optional[str] = None):
        self.events.append({
            'type': event_type,
            'session_id': session_id,
            'break_id': break_id,
            'details': details or {},
            'user_message': user_message,
            'timestamp': datetime.now()
        })


class MockTask(Task):
    def __init__(self, id: int = 1, name: str = "Test Task", allocated_time_minutes: int = 60, mode: str = "normal"):
        super().__init__(
            id=str(id),  # Task.id is Optional[str] per dataclass
            name=name,
            allocated_time_minutes=allocated_time_minutes,
            start_time=None,
            end_time=None,
            mode=mode,
            auto_calculate_breaks=True,
            num_breaks=0,
            break_duration_minutes=5,
            created_at=datetime.now().isoformat()
        )
        self._int_id = id  # Store integer ID for dict key


class MockSettings(Settings):
    def __init__(self):
        self.id = 1
        self.media_volume = 50
        self.alarm_volume = 70
        self.music_volume = 50
        self.screen_brightness = 100
        self.alarm_duration_seconds = 5
        self.image_display_duration_seconds = 10
        self.normal_work_interval_minutes = 25
        self.normal_break_duration_minutes = 5
        self.normal_snooze_duration_minutes = 5
        self.strict_work_interval_minutes = 52
        self.strict_break_duration_minutes = 17
        self.strict_cooldown_minutes = 10
        self.focused_mandatory_break_minutes = 30
        self.max_snooze_passes = 3
        self.snooze_redistributes_breaks = True
        self.enable_break_music = True
        self.shuffle_media = False
        self.allow_skip_in_normal_mode = True
        self.escape_hatch_enabled = True
        self.escape_hatch_key_combo = "Ctrl+Shift+Q"
        self.escape_hatch_hold_duration_seconds = 3
        self.escape_hatch_debounce_ms = 500
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()


class TestSessionManager(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.db = MockDBManager()
        self.settings = MockSettings()
        self.db.settings = self.settings

        # Create a test task
        self.task = MockTask()
        self.db.tasks[self.task._int_id] = self.task

        # Create session manager
        self.sm = SessionManager(self.db)

        # Track callback calls
        self.callback_calls = {
            'work_tick': [],
            'break_tick': [],
            'break_warning': [],
            'break_triggered': [],
            'break_complete': [],
            'session_complete': [],
            'cooldown_tick': [],
            'cooldown_complete': []
        }

        # Set up callbacks
        self.sm.on_work_tick = lambda secs: self.callback_calls['work_tick'].append(secs)
        self.sm.on_break_tick = lambda secs: self.callback_calls['break_tick'].append(secs)
        self.sm.on_break_warning = lambda secs: self.callback_calls['break_warning'].append(secs)
        self.sm.on_break_triggered = lambda idx: self.callback_calls['break_triggered'].append(idx)
        self.sm.on_break_complete = lambda: self.callback_calls['break_complete'].append(True)
        self.sm.on_session_complete = lambda: self.callback_calls['session_complete'].append(True)
        self.sm.on_cooldown_tick = lambda secs: self.callback_calls['cooldown_tick'].append(secs)
        self.sm.on_cooldown_complete = lambda: self.callback_calls['cooldown_complete'].append(True)

    def test_initialization(self):
        """Test SessionManager initialization"""
        sm = SessionManager(self.db)
        self.assertIsNone(sm.active_session_id)
        self.assertIsNone(sm.work_timer)
        self.assertIsNone(sm.break_timer)
        self.assertIsNone(sm.cooldown_timer)
        self.assertFalse(sm.is_in_break)
        self.assertFalse(sm.is_in_cooldown)

    def test_create_session(self):
        """Test session creation"""
        session_id = self.sm.create_session(self.task._int_id)

        # Check session was created
        self.assertIsNotNone(session_id)
        self.assertIsNone(self.sm.active_session_id)  # Not active until started

        # Check database state
        session = self.db.getSession(session_id)
        self.assertIsNotNone(session)
        if session:
            self.assertEqual(session.task_id, self.task._int_id)
            self.assertEqual(session.mode, self.task.mode)
            self.assertEqual(session.status, 'in_progress')
            self.assertEqual(session.snooze_passes_remaining, self.settings.max_snooze_passes)

    def test_create_session_invalid_task(self):
        """Test session creation with invalid task"""
        with self.assertRaises(ValueError):
            self.sm.create_session(999)  # Non-existent task

    def test_start_session(self):
        """Test starting a session"""
        session_id = self.sm.create_session(self.task._int_id)
        self.sm.start_session(session_id)

        # Check timer was created
        self.assertIsNotNone(self.sm.work_timer)
        if self.sm.work_timer:
            self.assertTrue(self.sm.work_timer.is_running())

        # Check session status
        session = self.db.getSession(session_id)
        self.assertIsNotNone(session)
        if session:
            self.assertEqual(session.status, 'in_progress')

    def test_start_session_invalid_session(self):
        """Test starting an invalid session"""
        with self.assertRaises(ValueError):
            self.sm.start_session(999)  # Non-existent session

    def test_take_break(self):
        """Test taking a break"""
        session_id = self.sm.create_session(self.task._int_id)
        self.sm.start_session(session_id)

        # Create a pending break and start it manually
        break_obj = Break(
            id=None,
            session_id=session_id,
            scheduled_time=datetime.now().isoformat(),
            actual_time=None,
            duration_minutes=5,
            status='pending',
            snooze_count=0,
            snooze_duration_minutes=0,
            created_at=datetime.now().isoformat()
        )
        break_id = self.db.createBreak(break_obj)

        # Start the break manually (simulating timer trigger)
        self.sm._start_break(break_id)

        # Check state
        self.assertTrue(self.sm.is_in_break)
        self.assertIsNotNone(self.sm.break_timer)
        self.assertEqual(self.sm.current_break_id, break_id)

        # Check break was updated
        updated_break = self.db.breaks[break_id]
        self.assertEqual(updated_break.status, 'in_progress')

        # Now take the break (user action)
        self.sm.take_break()  # This should just log, doesn't change state

    def test_snooze_break(self):
        """Test snoozing a break"""
        session_id = self.sm.create_session(self.task._int_id)
        self.sm.start_session(session_id)

        # Create a pending break and start it
        break_obj = Break(
            id=None,
            session_id=session_id,
            scheduled_time=datetime.now().isoformat(),
            actual_time=None,
            duration_minutes=5,
            status='pending',
            snooze_count=0,
            snooze_duration_minutes=0,
            created_at=datetime.now().isoformat()
        )
        break_id = self.db.createBreak(break_obj)
        self.sm._start_break(break_id)

        # Snooze the break
        self.sm.snooze_break()

        # Check state - should not be in break anymore
        self.assertFalse(self.sm.is_in_break)
        self.assertIsNone(self.sm.break_timer)
        self.assertIsNone(self.sm.current_break_id)

        # Check break was snoozed
        updated_break = self.db.breaks[break_id]
        self.assertEqual(updated_break.snooze_count, 1)

    def test_skip_break(self):
        """Test skipping a break"""
        session_id = self.sm.create_session(self.task._int_id)
        self.sm.start_session(session_id)

        # Create a pending break and start it
        break_obj = Break(
            id=None,
            session_id=session_id,
            scheduled_time=datetime.now().isoformat(),
            actual_time=None,
            duration_minutes=5,
            status='pending',
            snooze_count=0,
            snooze_duration_minutes=0,
            created_at=datetime.now().isoformat()
        )
        break_id = self.db.createBreak(break_obj)
        self.sm._start_break(break_id)

        # Skip the break
        self.sm.skip_break()

        # Check state - should not be in break anymore
        self.assertFalse(self.sm.is_in_break)
        self.assertIsNone(self.sm.break_timer)
        self.assertIsNone(self.sm.current_break_id)

        # Check break was skipped
        updated_break = self.db.breaks[break_id]
        self.assertEqual(updated_break.status, 'skipped')

    def test_extend_session(self):
        """Test extending a session"""
        session_id = self.sm.create_session(self.task._int_id)
        self.sm.start_session(session_id)

        # Check timer duration was extended
        if self.sm.work_timer:
            original_duration = self.sm.work_timer.duration_minutes
            self.sm.extend_session(30)  # Add 30 minutes
            self.assertEqual(self.sm.work_timer.duration_minutes, original_duration + 30)

        # Check session was updated
        session = self.db.getSession(session_id)
        self.assertIsNotNone(session)
        if session:
            self.assertEqual(session.extended_count, 1)

    def test_complete_session(self):
        """Test completing a session"""
        session_id = self.sm.create_session(self.task._int_id)
        self.sm.start_session(session_id)

        # Complete the session
        self.sm.complete_session()

        # Check state
        self.assertIsNone(self.sm.active_session_id)
        self.assertIsNone(self.sm.work_timer)

        # Check session was updated
        session = self.db.getSession(session_id)
        self.assertIsNotNone(session)
        if session:
            self.assertEqual(session.status, 'completed')
            self.assertIsNotNone(session.end_time)
            self.assertIsNotNone(session.actual_duration_minutes)

    def test_emergency_exit(self):
        """Test emergency exit functionality"""
        session_id = self.sm.create_session(self.task._int_id)
        self.sm.start_session(session_id)

        # Start a break
        break_obj = Break(
            id=None,
            session_id=session_id,
            scheduled_time=datetime.now().isoformat(),
            actual_time=None,
            duration_minutes=5,
            status='pending',
            snooze_count=0,
            snooze_duration_minutes=0,
            created_at=datetime.now().isoformat()
        )
        break_id = self.db.createBreak(break_obj)
        self.sm.take_break()

        # Trigger emergency exit
        self.sm.handle_emergency_exit("Test emergency")

        # Check state
        self.assertFalse(self.sm.is_in_break)
        self.assertIsNone(self.sm.break_timer)
        self.assertIsNotNone(self.sm.work_timer)
        if self.sm.work_timer:
            self.assertTrue(self.sm.work_timer.is_running())  # Work should resume

        # Check session was updated
        session = self.db.getSession(session_id)
        self.assertIsNotNone(session)
        if session:
            self.assertEqual(session.emergency_exits, 1)

    def test_session_status(self):
        """Test getting session status"""
        # No active session
        status = self.sm.get_session_status()
        self.assertFalse(status['active'])

        # With active session
        session_id = self.sm.create_session(self.task._int_id)
        self.sm.start_session(session_id)

        status = self.sm.get_session_status()
        self.assertTrue(status['active'])
        self.assertEqual(status['session_id'], session_id)
        self.assertEqual(status['mode'], self.task.mode)
        self.assertFalse(status['is_in_break'])
        self.assertFalse(status['is_in_cooldown'])

    def test_state_queries(self):
        """Test state query methods"""
        # Initially no session active
        self.assertFalse(self.sm.is_session_active())
        self.assertFalse(self.sm.is_break_active())
        self.assertFalse(self.sm.is_cooldown_active())

        # After creating session (but not started)
        session_id = self.sm.create_session(self.task._int_id)
        self.assertFalse(self.sm.is_session_active())  # Not active until started
        self.assertFalse(self.sm.is_break_active())
        self.assertFalse(self.sm.is_cooldown_active())

        # After starting session
        self.sm.start_session(session_id)
        self.assertTrue(self.sm.is_session_active())
        self.assertFalse(self.sm.is_break_active())
        self.assertFalse(self.sm.is_cooldown_active())

        # During break
        break_obj = Break(
            id=None,
            session_id=session_id,
            scheduled_time=datetime.now().isoformat(),
            actual_time=None,
            duration_minutes=5,
            status='pending',
            snooze_count=0,
            snooze_duration_minutes=0,
            created_at=datetime.now().isoformat()
        )
        break_id = self.db.createBreak(break_obj)
        self.sm._start_break(break_id)

        self.assertTrue(self.sm.is_session_active())
        self.assertTrue(self.sm.is_break_active())
        self.assertFalse(self.sm.is_cooldown_active())

    def test_get_active_session_id(self):
        """Test getting active session ID"""
        self.assertIsNone(self.sm.get_active_session_id())

        session_id = self.sm.create_session(self.task._int_id)
        self.assertIsNone(self.sm.get_active_session_id())  # Not active until started

        self.sm.start_session(session_id)
        self.assertEqual(self.sm.get_active_session_id(), session_id)

    def test_timer_callbacks(self):
        """Test that timer callbacks are properly connected"""
        session_id = self.sm.create_session(self.task._int_id)
        self.sm.start_session(session_id)

        # Check that timer callbacks are properly connected
        if self.sm.work_timer:
            self.assertIsNotNone(self.sm.work_timer.on_tick)
            self.assertIsNotNone(self.sm.work_timer.on_complete)

    def test_multiple_sessions(self):
        """Test handling multiple sessions (should only allow one active)"""
        session1_id = self.sm.create_session(self.task._int_id)
        self.assertIsNone(self.sm.active_session_id)  # Not active until started

        # Create another task and session
        task2 = MockTask(id=2, name="Task 2")
        self.db.tasks[task2._int_id] = task2
        session2_id = self.sm.create_session(task2._int_id)
        self.assertIsNone(self.sm.active_session_id)  # Still not active

        # Start the second session
        self.sm.start_session(session2_id)

        # Should have the second session as active
        self.assertEqual(self.sm.active_session_id, session2_id)
        self.assertNotEqual(session1_id, session2_id)


if __name__ == '__main__':
    unittest.main()