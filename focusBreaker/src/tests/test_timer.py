"""
Comprehensive test suite for timer functions using unittest
"""
import unittest
import sys
import time
sys.path.insert(0, 'src')

from core.timer import Timer, WorkTimer, BreakTimer, TimerState


class TestTimer(unittest.TestCase):

    def test_basic_timer(self):
        """Test basic Timer functionality"""
        tick_count = 0
        completed = False
        
        def on_tick(elapsed):
            nonlocal tick_count
            tick_count += 1
        
        def on_complete():
            nonlocal completed
            completed = True
        
        # Test normal flow
        timer = Timer(0.1, on_tick=on_tick, on_complete=on_complete)  # 6 seconds
        self.assertEqual(timer.state, TimerState.STOPPED)
        self.assertEqual(timer.get_elapsed_seconds(), 0)
        self.assertEqual(timer.get_progress_percentage(), 0.0)
        
        timer.start()
        self.assertTrue(timer.is_running())
        time.sleep(2)
        
        timer.pause()
        self.assertTrue(timer.is_paused())
        elapsed_before = timer.get_elapsed_seconds()
        time.sleep(1)
        self.assertEqual(timer.get_elapsed_seconds(), elapsed_before)
        
        timer.resume()
        self.assertTrue(timer.is_running())
        time.sleep(5)  # Wait for completion
        self.assertTrue(completed)
        self.assertTrue(timer.is_completed())
        self.assertEqual(timer.get_progress_percentage(), 100.0)
        
        timer.reset()
        self.assertEqual(timer.state, TimerState.STOPPED)
        self.assertEqual(timer.get_elapsed_seconds(), 0)

    def test_timer_pause_resume(self):
        """Test pause and resume functionality"""
        timer = Timer(2.0)
        timer.start()
        time.sleep(0.1)
        timer.pause()
        self.assertTrue(timer.is_paused())
        timer.resume()
        self.assertTrue(timer.is_running())
        timer.stop()

    def test_timer_callbacks(self):
        """Test timer callbacks"""
        tick_count = 0
        completed = False
        
        def on_tick(elapsed):
            nonlocal tick_count
            tick_count += 1
        
        def on_complete():
            nonlocal completed
            completed = True
        
        timer = Timer(0.1, on_tick=on_tick, on_complete=on_complete)
        timer.start()
        time.sleep(7.0)
        
        self.assertGreater(tick_count, 0)
        self.assertTrue(completed)

    def test_work_timer(self):
        """Test WorkTimer with break scheduling"""
        break_triggered = False
        break_index = None
        
        def on_break_time(index):
            nonlocal break_triggered, break_index
            break_triggered = True
            break_index = index
        
        def on_tick(elapsed):
            pass
        
        # 6 second work session, break at 3 seconds
        timer = WorkTimer(0.1, [0.05], on_tick=on_tick, on_break_time=on_break_time)  # 6 seconds, break at 3 seconds
        timer.start()
        time.sleep(4.0)
        
        self.assertTrue(break_triggered)
        self.assertEqual(break_index, 0)
        
        timer.stop()
        self.assertEqual(timer.state, TimerState.STOPPED)

    def test_break_timer(self):
        """Test BreakTimer with warnings"""
        warning_triggered = False
        completed = False
        
        def on_warning(remaining):
            nonlocal warning_triggered
            warning_triggered = True
        
        def on_complete():
            nonlocal completed
            completed = True
        
        # 0.1 minute break, warning at 0.02 minutes remaining
        timer = BreakTimer(0.1, on_warning=on_warning, on_complete=on_complete)
        timer.start()
        time.sleep(7.0)
        
        self.assertTrue(warning_triggered)
        self.assertTrue(completed)

    def test_timer_edge_cases(self):
        """Test edge cases and error conditions"""
        # Zero duration
        completed = False
        def on_complete():
            nonlocal completed
            completed = True
        
        timer = Timer(0, on_complete=on_complete)
        timer.start()
        time.sleep(0.1)
        self.assertTrue(completed)
        self.assertTrue(timer.is_completed())
        self.assertEqual(timer.get_progress_percentage(), 100.0)
        
        # Very short duration
        timer = Timer(0.1)
        timer.start()
        time.sleep(7.0)
        self.assertTrue(timer.is_completed())
        
        # Multiple start/stop
        timer = Timer(1.0)
        timer.start()
        time.sleep(0.2)
        timer.stop()
        self.assertEqual(timer.state, TimerState.STOPPED)
        timer.start()
        self.assertTrue(timer.is_running())
        time.sleep(0.3)
        self.assertFalse(timer.is_completed())
        
        # Pause without starting
        timer = Timer(1.0)
        timer.pause()
        self.assertEqual(timer.state, TimerState.STOPPED)
        
        # Resume without pausing
        timer.start()
        timer.resume()
        self.assertTrue(timer.is_running())

    def test_timer_state_transitions(self):
        """Test all possible state transitions"""
        timer = Timer(0.1)
        
        # STOPPED -> RUNNING
        self.assertEqual(timer.state, TimerState.STOPPED)
        timer.start()
        self.assertEqual(timer.state, TimerState.RUNNING)
        
        # RUNNING -> PAUSED
        timer.pause()
        self.assertEqual(timer.state, TimerState.PAUSED)
        
        # PAUSED -> RUNNING
        timer.resume()
        self.assertEqual(timer.state, TimerState.RUNNING)
        
        # RUNNING -> COMPLETED
        time.sleep(7.0)
        self.assertEqual(timer.state, TimerState.COMPLETED)
        
        # COMPLETED -> STOPPED
        timer.reset()
        self.assertEqual(timer.state, TimerState.STOPPED)


if __name__ == '__main__':
    unittest.main()