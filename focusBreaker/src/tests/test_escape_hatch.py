"""
Comprehensive test suite for escape_hatch module using unittest
"""
import sys
import time
import threading
import unittest
import unittest.mock as mock
sys.path.insert(0, 'src')

from core.escape_hatch import EscapeHatchDetector


class TestEscapeHatch(unittest.TestCase):

    def test_initialization(self):
        """Test detector initialization with various parameters"""
        # Valid initialization
        detector = EscapeHatchDetector()
        self.assertEqual(detector.key_combo, "ctrl+alt+shift+e")
        self.assertEqual(detector.hold_duration_seconds, 3.0)
        self.assertIsNone(detector.on_escape)
        self.assertIsNone(detector.on_progress)
        self.assertFalse(detector.is_active)
        self.assertFalse(detector.is_holding)
        self.assertEqual(detector.consecutive_errors, 0)

        # Custom parameters
        def dummy_escape():
            pass

        def dummy_progress(p):
            pass

        detector2 = EscapeHatchDetector(
            key_combo="ctrl+alt+f12",
            hold_duration_seconds=2.5,
            on_escape=dummy_escape,
            on_progress=dummy_progress,
            debounce_ms=200
        )
        self.assertEqual(detector2.key_combo, "ctrl+alt+f12")
        self.assertEqual(detector2.hold_duration_seconds, 2.5)
        self.assertEqual(detector2.on_escape, dummy_escape)
        self.assertEqual(detector2.on_progress, dummy_progress)
        self.assertEqual(detector2.debounce_ms, 0.2)

    def test_initialization_validation(self):
        """Test input validation during initialization"""
        with self.assertRaises(ValueError) as cm:
            EscapeHatchDetector(key_combo="")
        self.assertIn("key_combo must be a non-empty string", str(cm.exception))

        # None values should use defaults (not raise errors)
        detector_none = EscapeHatchDetector(key_combo=None, hold_duration_seconds=None, debounce_ms=None)
        self.assertEqual(detector_none.key_combo, "ctrl+alt+shift+e")
        self.assertEqual(detector_none.hold_duration_seconds, 3.0)

        # Invalid hold_duration_seconds
        with self.assertRaises(ValueError) as cm:
            EscapeHatchDetector(hold_duration_seconds=0)
        self.assertIn("hold_duration_seconds must be a positive number", str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            EscapeHatchDetector(hold_duration_seconds=-1)
        self.assertIn("hold_duration_seconds must be a positive number", str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            EscapeHatchDetector(debounce_ms=-1)
        self.assertIn("debounce_ms must be non-negative", str(cm.exception))

    def test_settings_integration(self):
        """Test initialization with Settings object"""
        # Mock settings object
        class MockSettings:
            def __init__(self, enabled=True, key_combo="ctrl+alt+esc", hold_duration=5, debounce=200):
                self.escape_hatch_enabled = enabled
                self.escape_hatch_key_combo = key_combo
                self.escape_hatch_hold_duration_seconds = hold_duration
                self.escape_hatch_debounce_ms = debounce

        # Test with enabled settings
        settings = MockSettings()
        detector = EscapeHatchDetector(settings=settings)           # type: ignore
        self.assertEqual(detector.key_combo, "ctrl+alt+esc")
        self.assertEqual(detector.hold_duration_seconds, 5.0)
        self.assertEqual(detector.debounce_ms, 0.2)                          # Converted to seconds

        # Test with disabled settings (should use defaults)
        settings_disabled = MockSettings(enabled=False)
        detector2 = EscapeHatchDetector(settings=settings_disabled)         # type: ignore
        self.assertEqual(detector2.key_combo, "ctrl+alt+shift+e")                    # Default
        self.assertEqual(detector2.hold_duration_seconds, 3.0)

        # Test settings override individual parameters
        detector3 = EscapeHatchDetector(
            settings=settings,                          # type: ignore
            key_combo="ignored",                        # Should be ignored
            hold_duration_seconds=10                    # Should be ignored
        )
        self.assertEqual(detector3.key_combo, "ctrl+alt+esc")        # From settings
        self.assertEqual(detector3.hold_duration_seconds, 5.0)        # From settings

    def test_start_stop(self):
        """Test start and stop functionality"""
        detector = EscapeHatchDetector()

        # Initial state
        self.assertFalse(detector.is_active)

        # Start
        detector.start()
        self.assertTrue(detector.is_active)

        # Start again (should warn but not fail)
        detector.start()
        self.assertTrue(detector.is_active)

        # Stop
        detector.stop()
        self.assertFalse(detector.is_active)

        # Stop again (should not fail)
        detector.stop()
        self.assertFalse(detector.is_active)

    def test_reset_state(self):
        """Test state reset functionality"""
        detector = EscapeHatchDetector()

        # Set some state
        detector.is_holding = True
        detector.hold_start_time = time.time()
        detector.last_progress_time = 123.45

        # Reset
        detector.reset_state()
        self.assertFalse(detector.is_holding)
        self.assertIsNone(detector.hold_start_time)
        self.assertEqual(detector.last_progress_time, 0)

    def test_check_keys_held(self):
        """Test key checking with mocking"""
        detector = EscapeHatchDetector(key_combo="ctrl+alt+e")

        # Mock keyboard.is_pressed
        with mock.patch('core.escape_hatch.keyboard.is_pressed') as mock_pressed:
            # All keys pressed
            mock_pressed.return_value = True
            self.assertTrue(detector.check_keys_held())
            self.assertEqual(detector.consecutive_errors, 0)

            # One key not pressed
            def side_effect(key):
                return key != 'alt'
            mock_pressed.side_effect = side_effect
            self.assertFalse(detector.check_keys_held())
            self.assertEqual(detector.consecutive_errors, 0)

            # Exception handling
            mock_pressed.side_effect = Exception("Keyboard error")
            self.assertFalse(detector.check_keys_held())
            self.assertEqual(detector.consecutive_errors, 1)

            # Multiple errors
            for i in range(5):
                detector.check_keys_held()
            self.assertEqual(detector.consecutive_errors, 6)

    def test_update_logic(self):
        """Test the main update logic"""
        escape_called = False
        progress_values = []

        def on_escape():
            nonlocal escape_called
            escape_called = True

        def on_progress(p):
            progress_values.append(round(p, 2))

        detector = EscapeHatchDetector(
            hold_duration_seconds=0.5,  # Short for testing
            on_escape=on_escape,
            on_progress=on_progress
        )

        detector.start()

        # Test inactive state
        detector.stop()
        detector.update()  # Should do nothing
        self.assertFalse(escape_called)

        detector.start()

        # Test no keys held
        with mock.patch.object(detector, 'check_keys_held', return_value=False):
            detector.update()
            self.assertFalse(detector.is_holding)

        # Test keys held - start holding
        mock_check = mock.patch.object(detector, 'check_keys_held', return_value=True)
        with mock_check:
            detector.update()
            self.assertTrue(detector.is_holding)
            self.assertIsNotNone(detector.hold_start_time)

            # Continue holding - should progress
            time.sleep(0.3)  # Simulate time passing
            detector.update()
            self.assertGreater(len(progress_values), 0)

            # Complete hold
            time.sleep(0.3)  # Enough to complete
            detector.update()
            self.assertTrue(escape_called)
            self.assertFalse(detector.is_holding)

    def test_callbacks_error_handling(self):
        """Test callback error handling"""
        def failing_escape():
            raise Exception("Escape callback failed")

        def failing_progress(p):
            raise Exception("Progress callback failed")

        detector = EscapeHatchDetector(
            hold_duration_seconds=0.1,
            on_escape=failing_escape,
            on_progress=failing_progress
        )

        detector.start()

        # Mock keys held and fast-forward time
        with mock.patch.object(detector, 'check_keys_held', return_value=True):
            detector.update()  # Start holding

            # Simulate completion with failing callbacks
            detector.hold_start_time = time.time() - 0.2  # Already completed
            detector.update()  # Should trigger callbacks but handle errors

        # Should still reset state despite callback errors
        self.assertFalse(detector.is_holding)

    def test_status_and_health(self):
        """Test status reporting and health checks"""
        detector = EscapeHatchDetector()

        # Initial status
        status = detector.get_status()
        self.assertFalse(status['active'])
        self.assertFalse(status['holding'])
        self.assertEqual(status['progress'], 0.0)
        self.assertTrue(status['healthy'])
        self.assertEqual(status['consecutive_errors'], 0)
        self.assertEqual(status['key_combo'], "ctrl+alt+shift+e")

        # After some errors
        detector.consecutive_errors = 3
        self.assertTrue(detector.is_healthy())

        detector.consecutive_errors = 6
        self.assertFalse(detector.is_healthy())

        status = detector.get_status()
        self.assertFalse(status['healthy'])

    def test_force_escape(self):
        """Test force escape functionality"""
        escape_called = False

        def on_escape():
            nonlocal escape_called
            escape_called = True

        detector = EscapeHatchDetector(on_escape=on_escape)

        # Not active - should not call
        detector.force_escape()
        self.assertFalse(escape_called)

        # Active - should call
        detector.start()
        detector.force_escape()
        self.assertTrue(escape_called)

    def test_thread_safety(self):
        """Test basic thread safety"""
        detector = EscapeHatchDetector()
        results = []

        def worker():
            detector.start()
            results.append(detector.is_active)
            detector.stop()
            results.append(detector.is_active)

        # Run multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All operations should complete without issues
        self.assertEqual(len(results), 10)  # 5 start + 5 stop results
        self.assertTrue(all(isinstance(r, bool) for r in results))

    def test_debouncing(self):
        """Test debouncing mechanism"""
        detector = EscapeHatchDetector(debounce_ms=200)  # 200ms debounce

        detector.start()

        # Mock keys held
        with mock.patch.object(detector, 'check_keys_held', return_value=True):
            # First attempt
            detector.update()
            self.assertTrue(detector.is_holding)
            first_start = detector.hold_start_time

            # Release and try again immediately - should debounce
            detector.is_holding = False
            detector.last_release_time = time.time()
            detector.update()
            # Should not start holding due to debounce
            self.assertFalse(detector.is_holding)

            # Wait for debounce period
            time.sleep(0.25)
            detector.update()
            self.assertTrue(detector.is_holding)


if __name__ == '__main__':
    unittest.main()