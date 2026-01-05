"""
Comprehensive test suite for input_blocker.py
Tests cross-platform input blocking functionality
"""
import sys
import os
import unittest
import time
from unittest.mock import patch
from threading import Event

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from system.input_blocker import InputBlocker, BlockingMode


class TestInputBlocker(unittest.TestCase):
    """Comprehensive test cases for InputBlocker class"""

    def setUp(self):
        """Set up test fixtures"""
        self.blocker = InputBlocker()

    def tearDown(self):
        """Clean up after each test"""
        if self.blocker.is_blocking:
            self.blocker.stop_blocking()
        self.blocker.cleanup()

    # ====================================== INITIALIZATION TESTS =====================================

    def test_initialization_default_params(self):
        """Test InputBlocker initializes with default parameters"""
        blocker = InputBlocker()

        self.assertEqual(blocker.platform, 'Windows')
        self.assertEqual(blocker.escape_key_combo, {'ctrl', 'alt', 'shift', 'esc'})
        self.assertEqual(blocker.max_block_duration, 3600)
        self.assertFalse(blocker.is_blocking)
        self.assertEqual(blocker.blocking_mode, BlockingMode.NONE)
        self.assertIsInstance(blocker.escape_key_pressed, set)
        self.assertIsInstance(blocker.blocked_keys, set)

    def test_initialization_custom_params(self):
        """Test InputBlocker initializes with custom parameters"""
        custom_combo = {'ctrl', 'alt', 'f12'}
        blocker = InputBlocker(escape_key_combo=custom_combo, max_block_duration=1800)

        self.assertEqual(blocker.escape_key_combo, custom_combo)
        self.assertEqual(blocker.max_block_duration, 1800)

    def test_initialization_callbacks(self):
        """Test InputBlocker callback setup"""
        blocker = InputBlocker()

        self.assertIsNone(blocker.on_escape_detected)
        self.assertIsNone(blocker.on_block_timeout)

        # Set callbacks
        escape_callback = lambda: None
        timeout_callback = lambda: None

        blocker.on_escape_detected = escape_callback
        blocker.on_block_timeout = timeout_callback

        self.assertEqual(blocker.on_escape_detected, escape_callback)
        self.assertEqual(blocker.on_block_timeout, timeout_callback)

    # ====================================== PLATFORM DETECTION TESTS =====================================

    @patch('system.input_blocker.PLATFORM_SYSTEM', 'Windows')
    def test_platform_windows(self):
        """Test Windows platform detection"""
        blocker = InputBlocker()
        self.assertEqual(blocker.platform, 'Windows')

    @patch('system.input_blocker.PLATFORM_SYSTEM', 'Darwin')
    def test_platform_macos(self):
        """Test macOS platform detection"""
        blocker = InputBlocker()
        self.assertEqual(blocker.platform, 'Darwin')

    @patch('system.input_blocker.PLATFORM_SYSTEM', 'Linux')
    def test_platform_linux(self):
        """Test Linux platform detection"""
        blocker = InputBlocker()
        self.assertEqual(blocker.platform, 'Linux')

    # ====================================== BLOCKING CONTROL TESTS =====================================

    @patch('system.input_blocker.INPUT_BLOCKING_AVAILABLE', False)
    def test_start_blocking_unavailable(self):
        """Test starting blocking when not available"""
        blocker = InputBlocker()

        with patch('system.input_blocker.logger') as mock_logger:
            blocker.start_blocking()

            mock_logger.warning.assert_called_with("Input blocking not available on this platform.")
            self.assertFalse(blocker.is_blocking)

    @patch('system.input_blocker.INPUT_BLOCKING_AVAILABLE', True)
    def test_start_blocking_already_active(self):
        """Test starting blocking when already active"""
        blocker = InputBlocker()

        with patch.object(blocker, '_start_keyboard_blocking'):
            blocker.start_blocking()

            with patch('system.input_blocker.logger') as mock_logger:
                blocker.start_blocking()  # Try to start again

                mock_logger.warning.assert_called_with("Input blocking already active.")

    def test_stop_blocking_not_active(self):
        """Test stopping blocking when not active"""
        blocker = InputBlocker()

        with patch('system.input_blocker.logger') as mock_logger:
            blocker.stop_blocking()

            mock_logger.warning.assert_called_with("Input blocking is not active.")

    @patch('system.input_blocker.INPUT_BLOCKING_AVAILABLE', True)
    def test_start_stop_blocking_keyboard_only(self):
        """Test keyboard-only blocking mode"""
        blocker = InputBlocker()

        with patch.object(blocker, '_start_keyboard_blocking') as mock_kb, \
             patch.object(blocker, '_start_mouse_blocking') as mock_mouse, \
             patch.object(blocker, '_start_timeout_monitor') as mock_timeout:

            blocker.start_blocking(BlockingMode.KEYBOARD_ONLY)

            self.assertTrue(blocker.is_blocking)
            self.assertEqual(blocker.blocking_mode, BlockingMode.KEYBOARD_ONLY)
            mock_kb.assert_called_once()
            mock_mouse.assert_not_called()
            mock_timeout.assert_called_once()

            # Test stop
            with patch.object(blocker, '_stop_keyboard_blocking') as mock_kb_stop, \
                 patch.object(blocker, '_stop_mouse_blocking') as mock_mouse_stop, \
                 patch.object(blocker, '_stop_timeout_monitor') as mock_timeout_stop:

                blocker.stop_blocking()

                self.assertFalse(blocker.is_blocking)
                self.assertEqual(blocker.blocking_mode, BlockingMode.NONE)
                mock_kb_stop.assert_called_once()
                mock_mouse_stop.assert_called_once()
                mock_timeout_stop.assert_called_once()

    @patch('system.input_blocker.INPUT_BLOCKING_AVAILABLE', True)
    def test_start_stop_blocking_full(self):
        """Test full blocking mode"""
        blocker = InputBlocker()

        with patch.object(blocker, '_start_keyboard_blocking') as mock_kb, \
             patch.object(blocker, '_start_mouse_blocking') as mock_mouse, \
             patch.object(blocker, '_start_timeout_monitor') as mock_timeout:

            blocker.start_blocking(BlockingMode.FULL)

            self.assertTrue(blocker.is_blocking)
            self.assertEqual(blocker.blocking_mode, BlockingMode.FULL)
            mock_kb.assert_called_once()
            mock_mouse.assert_called_once()
            mock_timeout.assert_called_once()

    # ====================================== KEYCODE MAPPING TESTS =====================================

    def test_keycode_to_name_known_keys(self):
        """Test keycode to name conversion for known keys"""
        blocker = InputBlocker()

        # Test various known keycodes
        test_cases = [
            (0, 'a'), (1, 's'), (28, 'return'), (29, 'escape'),
            (30, 'backspace'), (31, 'tab'), (32, 'space'), (65, 'end'),
            (67, 'right_arrow'), (68, 'left_arrow'), (69, 'down_arrow'), (70, 'up_arrow')
        ]

        for keycode, expected_name in test_cases:
            with self.subTest(keycode=keycode):
                self.assertEqual(blocker._keycode_to_name(keycode), expected_name)

    def test_keycode_to_name_unknown_keys(self):
        """Test keycode to name conversion for unknown keys"""
        blocker = InputBlocker()

        self.assertEqual(blocker._keycode_to_name(999), 'key_999')
        self.assertEqual(blocker._keycode_to_name(-1), 'key_-1')

    # ====================================== ESCAPE DETECTION TESTS =====================================

    def test_escape_key_detection(self):
        """Test escape key combination detection"""
        blocker = InputBlocker()

        # Initially no keys pressed
        self.assertFalse(blocker.check_escape_keys_pressed())

        # Add some keys
        blocker.escape_key_pressed.add('ctrl')
        self.assertFalse(blocker.check_escape_keys_pressed())

        blocker.escape_key_pressed.add('alt')
        self.assertFalse(blocker.check_escape_keys_pressed())

        blocker.escape_key_pressed.add('shift')
        self.assertFalse(blocker.check_escape_keys_pressed())

        # Add the final key
        blocker.escape_key_pressed.add('esc')
        self.assertTrue(blocker.check_escape_keys_pressed())

    def test_escape_key_detection_custom_combo(self):
        """Test escape key detection with custom combination"""
        custom_combo = {'ctrl', 'f12'}
        blocker = InputBlocker(escape_key_combo=custom_combo)

        blocker.escape_key_pressed.add('ctrl')
        self.assertFalse(blocker.check_escape_keys_pressed())

        blocker.escape_key_pressed.add('f12')
        self.assertTrue(blocker.check_escape_keys_pressed())

    # ====================================== STATUS QUERY TESTS =====================================

    def test_get_blocking_duration_not_blocking(self):
        """Test getting blocking duration when not blocking"""
        blocker = InputBlocker()

        self.assertEqual(blocker.get_blocking_duration(), 0.0)

    @patch('system.input_blocker.INPUT_BLOCKING_AVAILABLE', True)
    def test_get_blocking_duration_blocking(self):
        """Test getting blocking duration when blocking"""
        blocker = InputBlocker()

        with patch.object(blocker, '_start_keyboard_blocking'):
            blocker.start_blocking()

            # Simulate some time passing
            original_time = blocker.block_start_time
            blocker.block_start_time = time.time() - 5.5  # 5.5 seconds ago

            duration = blocker.get_blocking_duration()
            self.assertAlmostEqual(duration, 5.5, places=1)

    def test_get_blocker_status_not_blocking(self):
        """Test getting blocker status when not blocking"""
        blocker = InputBlocker()

        status = blocker.get_blocker_status()

        expected_keys = ['platform', 'available', 'is_blocking', 'blocking_mode',
                        'duration_seconds', 'escape_combo', 'timeout_remaining']

        for key in expected_keys:
            self.assertIn(key, status)

        self.assertEqual(status['platform'], 'Windows')
        self.assertFalse(status['is_blocking'])
        self.assertEqual(status['blocking_mode'], 'none')
        self.assertEqual(status['duration_seconds'], 0.0)
        # Check that all expected keys are in the escape combo (order doesn't matter for sets)
        self.assertEqual(set(status['escape_combo']), {'ctrl', 'alt', 'shift', 'esc'})

    @patch('system.input_blocker.INPUT_BLOCKING_AVAILABLE', True)
    def test_get_blocker_status_blocking(self):
        """Test getting blocker status when blocking"""
        blocker = InputBlocker()

        with patch.object(blocker, '_start_keyboard_blocking'):
            blocker.start_blocking(BlockingMode.KEYBOARD_ONLY)

            status = blocker.get_blocker_status()

            self.assertTrue(status['is_blocking'])
            self.assertEqual(status['blocking_mode'], 'keyboard')
            self.assertGreater(status['duration_seconds'], 0)
            self.assertLess(status['timeout_remaining'], 3600)

    @patch('system.input_blocker.INPUT_BLOCKING_AVAILABLE', True)
    def test_is_input_blocked(self):
        """Test input blocked status query"""
        blocker = InputBlocker()

        self.assertFalse(blocker.is_input_blocked())

        with patch.object(blocker, '_start_keyboard_blocking'):
            blocker.start_blocking()

            self.assertTrue(blocker.is_input_blocked())

    @patch('system.input_blocker.INPUT_BLOCKING_AVAILABLE', True)
    def test_get_blocking_mode(self):
        """Test blocking mode query"""
        blocker = InputBlocker()

        self.assertEqual(blocker.get_blocking_mode(), BlockingMode.NONE)

        with patch.object(blocker, '_start_keyboard_blocking'):
            blocker.start_blocking(BlockingMode.MOUSE_ONLY)

            self.assertEqual(blocker.get_blocking_mode(), BlockingMode.MOUSE_ONLY)

    # ====================================== TIMEOUT TESTS =====================================

    @patch('system.input_blocker.INPUT_BLOCKING_AVAILABLE', True)
    def test_timeout_monitor_starts_and_stops(self):
        """Test timeout monitor lifecycle"""
        blocker = InputBlocker(max_block_duration=1)  # Short timeout for testing

        with patch.object(blocker, '_start_keyboard_blocking'):
            blocker.start_blocking()

            # Check timeout monitor started
            self.assertIsNotNone(blocker.timeout_thread)
            self.assertTrue(blocker.timout_active)

            # Wait for timeout
            time.sleep(1.5)

            # Should have auto-stopped
            self.assertFalse(blocker.is_blocking)

    @patch('system.input_blocker.INPUT_BLOCKING_AVAILABLE', True)
    def test_timeout_callback_called(self):
        """Test timeout callback is called"""
        blocker = InputBlocker(max_block_duration=1)

        timeout_called = Event()
        blocker.on_block_timeout = lambda: timeout_called.set()

        with patch.object(blocker, '_start_keyboard_blocking'):
            blocker.start_blocking()

            # Wait for timeout
            timeout_called.wait(timeout=2)

            self.assertTrue(timeout_called.is_set())

    # ====================================== CLEANUP TESTS =====================================

    def test_cleanup_when_not_blocking(self):
        """Test cleanup when not blocking"""
        blocker = InputBlocker()

        with patch('system.input_blocker.logger') as mock_logger:
            blocker.cleanup()

            mock_logger.info.assert_called_with("InputBlocker cleaned up")

    @patch('system.input_blocker.INPUT_BLOCKING_AVAILABLE', True)
    def test_cleanup_when_blocking(self):
        """Test cleanup when blocking is active"""
        blocker = InputBlocker()

        with patch.object(blocker, '_start_keyboard_blocking'):
            blocker.start_blocking()

            with patch.object(blocker, '_stop_keyboard_blocking') as mock_kb_stop, \
                 patch.object(blocker, '_stop_mouse_blocking') as mock_mouse_stop, \
                 patch.object(blocker, '_stop_timeout_monitor') as mock_timeout_stop:

                blocker.cleanup()

                # Called once by stop_blocking() and once by cleanup() directly
                self.assertEqual(mock_kb_stop.call_count, 2)
                self.assertEqual(mock_mouse_stop.call_count, 2)
                self.assertEqual(mock_timeout_stop.call_count, 2)

    # ====================================== ERROR HANDLING TESTS =====================================

    @patch('system.input_blocker.INPUT_BLOCKING_AVAILABLE', True)
    def test_start_blocking_handles_exceptions(self):
        """Test start_blocking handles exceptions gracefully"""
        blocker = InputBlocker()

        with patch.object(blocker, '_start_keyboard_blocking', side_effect=Exception("Test error")), \
             patch('system.input_blocker.logger') as mock_logger:

            blocker.start_blocking()

            mock_logger.error.assert_called_with("Failed to start input blocking: Test error")
            # Should have called stop_blocking to clean up
            self.assertFalse(blocker.is_blocking)

    def test_get_blocker_status_handles_exceptions(self):
        """Test get_blocker_status handles exceptions"""
        blocker = InputBlocker()

        # Force an exception in status calculation
        blocker.block_start_time = "invalid"  # This will cause an exception        # type: ignore

        status = blocker.get_blocker_status()

        self.assertIn('error', status)
        self.assertEqual(status['platform'], 'Windows')

    # ====================================== INTEGRATION TESTS =====================================

    @patch('system.input_blocker.INPUT_BLOCKING_AVAILABLE', True)
    def test_full_blocking_lifecycle(self):
        """Test complete blocking lifecycle"""
        blocker = InputBlocker()

        # Start blocking
        with patch.object(blocker, '_start_keyboard_blocking'), \
             patch.object(blocker, '_start_mouse_blocking'), \
             patch.object(blocker, '_start_timeout_monitor'):

            blocker.start_blocking(BlockingMode.FULL)

            self.assertTrue(blocker.is_blocking)
            self.assertEqual(blocker.blocking_mode, BlockingMode.FULL)

        # Check status
        status = blocker.get_blocker_status()
        self.assertTrue(status['is_blocking'])
        self.assertEqual(status['blocking_mode'], 'full')

        # Stop blocking
        with patch.object(blocker, '_stop_keyboard_blocking'), \
             patch.object(blocker, '_stop_mouse_blocking'), \
             patch.object(blocker, '_stop_timeout_monitor'):

            blocker.stop_blocking()

            self.assertFalse(blocker.is_blocking)
            self.assertEqual(blocker.blocking_mode, BlockingMode.NONE)

    def test_escape_detection_integration(self):
        """Test escape key detection in blocking context"""
        blocker = InputBlocker()

        escape_detected = Event()
        blocker.on_escape_detected = lambda: escape_detected.set()

        # Simulate escape key combination being pressed
        blocker.escape_key_pressed = {'ctrl', 'alt', 'shift', 'esc'}

        self.assertTrue(blocker.check_escape_keys_pressed())

        # Simulate callback being triggered (this would happen in real keyboard callback)
        if blocker.on_escape_detected:
            blocker.on_escape_detected()

        self.assertTrue(escape_detected.is_set())


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce log noise during testing

    # Try to use rich for beautiful CLI output, fall back to basic if not available
    try:
        from rich.console import Console
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
        from rich.panel import Panel
        from rich.text import Text
        from rich.table import Table
        import time

        console = Console()

        class RichTestResult(unittest.TextTestResult):
            """Custom test result class with rich formatting"""

            def __init__(self, stream, descriptions, verbosity):
                super().__init__(stream, descriptions, verbosity)
                self.console = Console()
                self.start_time = time.time()
                self.test_times = {}

            def startTest(self, test):
                super().startTest(test)
                self.test_times[test] = time.time()

            def addSuccess(self, test):
                super().addSuccess(test)
                duration = time.time() - self.test_times[test]
                self.console.print(f"✅ [green]{test._testMethodName}[/green] ({duration:.3f}s)")

            def addError(self, test, err):
                super().addError(test, err)
                duration = time.time() - self.test_times[test]
                self.console.print(f"❌ [red]{test._testMethodName}[/red] ({duration:.3f}s) - ERROR")

            def addFailure(self, test, err):
                super().addFailure(test, err)
                duration = time.time() - self.test_times[test]
                self.console.print(f"❌ [red]{test._testMethodName}[/red] ({duration:.3f}s) - FAILED")

            def addSkip(self, test, reason):
                super().addSkip(test, reason)
                duration = time.time() - self.test_times[test]
                self.console.print(f"⏭️  [yellow]{test._testMethodName}[/yellow] ({duration:.3f}s) - SKIPPED: {reason}")

        class RichTestRunner(unittest.TextTestRunner):
            """Custom test runner with rich progress display"""

            def __init__(self, **kwargs):
                kwargs['resultclass'] = RichTestResult
                super().__init__(**kwargs)
                self.console = Console()

            def run(self, test):
                # Preliminary Information
                self.console.print("[bold cyan]📋 Preliminary Information[/bold cyan]")
                
                # Import Status
                try:
                    from system.input_blocker import InputBlocker, INPUT_BLOCKING_AVAILABLE
                    self.console.print("  [green]✓[/green] Input blocker module imports successful")
                    self.console.print(f"  [dim]Input blocking: {'Available' if INPUT_BLOCKING_AVAILABLE else 'Not available'}[/dim]")
                except ImportError as e:
                    self.console.print(f"  [red]✗[/red] Input blocker module import failed: {e}")
                
                # Platform Detection
                try:
                    import platform
                    current_platform = platform.system()
                    self.console.print(f"  [green]✓[/green] Platform detected: {current_platform}")
                except Exception as e:
                    self.console.print(f"  [yellow]⚠[/yellow] Platform detection failed: {e}")
                
                # Input Blocker Initialization
                try:
                    test_blocker = InputBlocker()
                    self.console.print("  [green]✓[/green] Input blocker initialized successfully")
                    self.console.print(f"  [dim]Platform: {test_blocker.platform}, Max duration: {test_blocker.max_block_duration}s[/dim]")
                    test_blocker.cleanup()
                except Exception as e:
                    self.console.print(f"  [yellow]⚠[/yellow] Input blocker initialization failed: {e}")
                
                self.console.print()

                # Header
                self.console.print()
                self.console.print(Panel.fit(
                    "[bold blue]🧪 InputBlocker Test Suite[/bold blue]\n"
                    "[dim]Testing cross-platform input blocking functionality[/dim]",
                    border_style="blue"
                ))
                self.console.print()

                # Progress bar
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeElapsedColumn(),
                    console=self.console
                ) as progress:

                    task = progress.add_task("Running tests...", total=test.countTestCases())

                    # Custom result class to update progress
                    class ProgressTestResult(RichTestResult):
                        def __init__(self, stream, descriptions, verbosity):
                            super().__init__(stream, descriptions, verbosity)

                        def addSuccess(self, test):
                            super().addSuccess(test)
                            progress.update(task, advance=1)

                        def addError(self, test, err):
                            super().addError(test, err)
                            progress.update(task, advance=1)

                        def addFailure(self, test, err):
                            super().addFailure(test, err)
                            progress.update(task, advance=1)

                        def addSkip(self, test, reason):
                            super().addSkip(test, reason)
                            progress.update(task, advance=1)

                    self.resultclass = ProgressTestResult
                    result: RichTestResult = super().run(test)  # type: ignore

                # Results summary
                self.console.print()
                total_time = time.time() - result.start_time

                table = Table(title="📊 Test Results Summary")
                table.add_column("Metric", style="cyan")
                table.add_column("Count", style="magenta")
                table.add_column("Status", style="green")

                table.add_row("Total Tests", str(result.testsRun), "📋")
                table.add_row("Passed", str(result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)), "✅")
                table.add_row("Failed", str(len(result.failures)), "❌" if result.failures else "✅")
                table.add_row("Errors", str(len(result.errors)), "❌" if result.errors else "✅")
                table.add_row("Skipped", str(len(result.skipped)), "⏭️" if result.skipped else "✅")
                table.add_row("Total Time", f"{total_time:.2f}s", "⏱️")

                self.console.print(table)

                # Final status
                if result.wasSuccessful():
                    self.console.print()
                    self.console.print(Panel(
                        "[bold green]🎉 All tests passed![/bold green]\n"
                        f"Successfully ran {result.testsRun} tests in {total_time:.2f} seconds",
                        border_style="green"
                    ))
                else:
                    self.console.print()
                    self.console.print(Panel(
                        f"[bold red]⚠️  {len(result.failures) + len(result.errors)} test(s) failed[/bold red]\n"
                        f"Check the output above for details",
                        border_style="red"
                    ))

                    # Show failures
                    if result.failures:
                        self.console.print("\n[bold red]Failures:[/bold red]")
                        for test, traceback in result.failures:
                            self.console.print(f"  • {test}")

                    if result.errors:
                        self.console.print("\n[bold red]Errors:[/bold red]")
                        for test, traceback in result.errors:
                            self.console.print(f"  • {test}")

                return result

        # Run tests with rich output
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(__import__('__main__'))
        runner = RichTestRunner(verbosity=0)  # We handle our own output
        runner.run(suite)

    except ImportError:
        # Fallback to basic unittest with better formatting
        print("📦 Rich library not available, using basic test runner...")
        print("=" * 60)
        print("🧪 InputBlocker Test Suite")
        print("Testing cross-platform input blocking functionality")
        print("=" * 60)

        # Custom test runner with progress
        class ProgressTestResult(unittest.TextTestResult):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.test_count = 0

            def startTest(self, test):
                super().startTest(test)
                self.test_count += 1
                print(f"\n🧪 Running test {self.test_count}: {test._testMethodName}", end="")

            def addSuccess(self, test):
                super().addSuccess(test)
                print(" ✅ PASSED")

            def addError(self, test, err):
                super().addError(test, err)
                print(" ❌ ERROR")

            def addFailure(self, test, err):
                super().addFailure(test, err)
                print(" ❌ FAILED")

            def addSkip(self, test, reason):
                super().addSkip(test, reason)
                print(f" ⏭️  SKIPPED: {reason}")

        class ProgressTestRunner(unittest.TextTestRunner):
            def __init__(self, **kwargs):
                kwargs['resultclass'] = ProgressTestResult
                super().__init__(**kwargs)

            def run(self, test):
                print(f"\n📊 Starting test suite with {test.countTestCases()} tests...\n")
                result = super().run(test)

                print("\n" + "=" * 60)
                print("📊 TEST RESULTS SUMMARY")
                print("=" * 60)
                print(f"Total tests: {result.testsRun}")
                print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)}")
                print(f"Failed: {len(result.failures)}")
                print(f"Errors: {len(result.errors)}")
                print(f"Skipped: {len(result.skipped)}")

                if result.wasSuccessful():
                    print("\n🎉 ALL TESTS PASSED!")
                else:
                    print("\n⚠️  SOME TESTS FAILED!")
                    if result.failures:
                        print("\nFailures:")
                        for test, _ in result.failures:
                            print(f"  • {test}")
                    if result.errors:
                        print("\nErrors:")
                        for test, _ in result.errors:
                            print(f"  • {test}")

                return result

        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(__import__('__main__'))
        runner = ProgressTestRunner(verbosity=0)
        runner.run(suite)