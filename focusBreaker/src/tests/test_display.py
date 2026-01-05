"""
Comprehensive test suite for DisplayManager class using unittest
"""
import unittest
import sys
import time
sys.path.insert(0, 'src')

try:
    from system.display import DisplayManager, detect_display_features, BRIGHTNESS_CONTROL_AVAILABLE
    DISPLAY_AVAILABLE = True
except ImportError as e:
    print(f"Display module not available: {e}")
    DISPLAY_AVAILABLE = False
    DisplayManager = None


class TestDisplayManager(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        if DISPLAY_AVAILABLE:
            self.display_manager = DisplayManager()                          # type: ignore
        else:
            self.display_manager = None

    def tearDown(self):
        """Clean up test fixtures"""
        if DISPLAY_AVAILABLE and self.display_manager:
            try:
                self.display_manager.cleanup()
            except:
                pass

    @unittest.skipUnless(DISPLAY_AVAILABLE, "Display module not available")
    def test_initialization(self):
        """Test DisplayManager initialization"""
        self.assertIsNotNone(self.display_manager)
        self.assertIsInstance(self.display_manager.platform, str)                            # type: ignore
        self.assertIsInstance(self.display_manager.brightness_control_available, bool)       # type: ignore

    @unittest.skipUnless(DISPLAY_AVAILABLE, "Display module not available")
    def test_display_detection(self):
        """Test display detection functionality"""
        displays = self.display_manager.get_displays()                                      # type: ignore
        self.assertIsInstance(displays, list)

        primary = self.display_manager.get_primary_display()                                # type: ignore
        if displays:
            self.assertIsNotNone(primary)

    @unittest.skipUnless(DISPLAY_AVAILABLE, "Display module not available")
    def test_screen_resolution(self):
        """Test screen resolution detection"""
        resolution = self.display_manager.get_screen_resolution()                           # type: ignore
        self.assertIsInstance(resolution, tuple)
        self.assertEqual(len(resolution), 2)
        self.assertIsInstance(resolution[0], int)
        self.assertIsInstance(resolution[1], int)
        # Basic sanity checks
        self.assertGreater(resolution[0], 0)
        self.assertGreater(resolution[1], 0)

    @unittest.skipUnless(DISPLAY_AVAILABLE, "Display module not available")
    def test_brightness_getter(self):
        """Test brightness getter functionality"""
        brightness = self.display_manager.get_brightness()                                  # type: ignore
        self.assertIsInstance(brightness, int)
        self.assertGreaterEqual(brightness, 0)
        self.assertLessEqual(brightness, 100)

    @unittest.skipUnless(DISPLAY_AVAILABLE, "Display module not available")
    def test_actual_brightness_change(self):
        """Test actual screen brightness changes (only when brightness control is available)"""
        if not self.display_manager.brightness_control_available:                                   # type: ignore
            self.skipTest("Brightness control not available - skipping actual brightness test")

        # Get original brightness
        original_brightness = self.display_manager.get_brightness()                                 # type: ignore
        print(f"Original brightness: {original_brightness}%")

        # Test changing to a different brightness
        test_brightness = 75 if original_brightness != 75 else 50
        print(f"Setting brightness to: {test_brightness}%")

        self.display_manager.set_brightness(test_brightness)                                        # type: ignore

        # Wait a moment for the change to take effect
        import time
        time.sleep(0.5)

        # Verify the brightness actually changed
        current_brightness = self.display_manager.get_brightness()                                  # type: ignore
        print(f"Current brightness after change: {current_brightness}%")

        # Allow some tolerance for brightness control precision
        self.assertAlmostEqual(current_brightness, test_brightness, delta=5,
                              msg=f"Brightness should be close to {test_brightness}%, got {current_brightness}%")

        # Restore original brightness
        print(f"Restoring brightness to: {original_brightness}%")
        self.display_manager.set_brightness(original_brightness)                                    # type: ignore

        # Wait and verify restoration
        time.sleep(0.5)
        restored_brightness = self.display_manager.get_brightness()                                 # type: ignore
        print(f"Brightness after restoration: {restored_brightness}%")

        self.assertAlmostEqual(restored_brightness, original_brightness, delta=5,
                              msg=f"Brightness should be restored to {original_brightness}%, got {restored_brightness}%")

    @unittest.skipUnless(DISPLAY_AVAILABLE, "Display module not available")
    def test_smooth_brightness_animation(self):
        """Test smooth brightness animation (only when brightness control is available)"""
        if not self.display_manager.brightness_control_available:                                   # type: ignore
            self.skipTest("Brightness control not available - skipping animation test")

        import time
        original_brightness = self.display_manager.get_brightness()                                 # type: ignore
        print(f"Testing smooth animation from {original_brightness}%")

        # Test smooth transition to 60%
        target_brightness = 60
        print(f"Animating to {target_brightness}% over 2 seconds")

        start_time = time.time()
        self.display_manager.set_brightness(target_brightness, smooth=True)              # type: ignore

        # Monitor brightness during animation to verify it's actually changing
        brightness_readings = []
        for i in range(10):  # Check 10 times during the 2-second animation
            time.sleep(0.2)
            current = self.display_manager.get_brightness()                             # type: ignore
            brightness_readings.append(current)
            print(f"  Step {i+1}: {current}%")

        # Wait for animation to complete
        time.sleep(0.5)

        end_time = time.time()
        final_brightness = self.display_manager.get_brightness()                        # type: ignore

        print(f"Animation completed in {end_time - start_time:.1f} seconds")
        print(f"Final brightness: {final_brightness}%")
        print(f"Brightness readings during animation: {brightness_readings}")

        # Verify animation was active and completed
        self.assertFalse(self.display_manager.is_animating())                           # type: ignore

        # Verify brightness actually changed during animation
        min_reading = min(brightness_readings)
        max_reading = max(brightness_readings)
        brightness_range = max_reading - min_reading
        self.assertGreater(brightness_range, 5, "Brightness should change by at least 5% during animation")

        # Verify final brightness is reasonably close to target (system may have multiple brightness controls)
        brightness_diff = abs(final_brightness - target_brightness)
        # Allow more tolerance since system may have multiple brightness controls interfering
        self.assertLessEqual(brightness_diff, 20, f"Final brightness {final_brightness}% should be within 20% of target {target_brightness}% (system interference may occur)")

        print(f"✅ Animation test passed - brightness changed from {min_reading}% to {max_reading}% and ended at {final_brightness}% (target: {target_brightness}%)")

        # Note: tearDown will handle brightness restoration

    @unittest.skipUnless(DISPLAY_AVAILABLE, "Display module not available")
    def test_brightness_boost(self):
        """Test brightness boost functionality"""
        original_brightness = self.display_manager.get_brightness()                                 # type: ignore

        # Test boost
        self.display_manager.boost_brightness(target_brightness=80)                      # type: ignore
        if self.display_manager.brightness_control_available:                            # type: ignore
            self.assertTrue(self.display_manager.is_brightness_boosted())                # type: ignore

        # Test restore
        self.display_manager.restore_brightness()                                        # type: ignore
        if self.display_manager.brightness_control_available:                            # type: ignore
            self.assertFalse(self.display_manager.is_brightness_boosted())               # type: ignore

    @unittest.skipUnless(DISPLAY_AVAILABLE, "Display module not available")
    def test_display_status(self):
        """Test display status reporting"""
        status = self.display_manager.get_display_status()                              # type: ignore
        self.assertIsInstance(status, dict)

        expected_keys = [
            'platform', 'brightness_control_available', 'original_brightness',
            'current_brightness', 'is_brightness_boosted', 'is_animating',
            'display_count', 'primary_display'
        ]

        for key in expected_keys:
            self.assertIn(key, status)

    # Tests that can run without brightness control
    def test_detect_display_features(self):
        """Test display feature detection"""
        features = detect_display_features()
        self.assertIsInstance(features, dict)

        expected_keys = ['brightness_control', 'multi_monitor_support', 'dpi_scaling', 'color_management']
        for key in expected_keys:
            self.assertIn(key, features)
            self.assertIsInstance(features[key], bool)

    def test_brightness_availability_flag(self):
        """Test that brightness availability flag is properly set"""
        self.assertIsInstance(BRIGHTNESS_CONTROL_AVAILABLE, bool)

    @unittest.skipUnless(DISPLAY_AVAILABLE, "Display module not available")
    def test_animation_control(self):
        """Test brightness animation control"""
        # Test animation state
        self.assertFalse(self.display_manager.is_animating())                                   # type: ignore

        # Test animation cancellation (should not crash even if no animation is running)
        self.display_manager.cancel_brightness_animation()                                      # type: ignore
        self.assertFalse(self.display_manager.is_animating())                                   # type: ignore

    @unittest.skipUnless(DISPLAY_AVAILABLE, "Display module not available")
    def test_screen_effects(self):
        """Test screen effect methods"""
        # These should not crash even without brightness control
        self.display_manager.flash_screen(duration_ms=100, brightness=90)                               # type: ignore
        self.display_manager.pulse_brightness(min_brightness=30, max_brightness=70, pulse_count=1)      # type: ignore

        # Give a moment for threads to complete
        time.sleep(0.1)


class TestDisplayManagerIntegration(unittest.TestCase):
    """Integration tests for DisplayManager"""

    def setUp(self):
        """Set up integration test fixtures"""
        if DISPLAY_AVAILABLE:
            self.display_manager = DisplayManager()             # type: ignore
        else:
            self.display_manager = None

    def tearDown(self):
        """Clean up integration test fixtures"""
        if DISPLAY_AVAILABLE and self.display_manager:
            try:
                self.display_manager.cleanup()
            except:
                pass

    @unittest.skipUnless(DISPLAY_AVAILABLE, "Display module not available")
    def test_full_lifecycle(self):
        """Test complete display manager lifecycle"""
        # Test initialization
        self.assertIsNotNone(self.display_manager)

        # Test display enumeration
        displays = self.display_manager.get_displays()                          # type: ignore
        self.assertIsInstance(displays, list)

        # Test brightness operations
        original = self.display_manager.get_brightness()                        # type: ignore
        self.display_manager.set_brightness(75)                                 # type: ignore
        self.display_manager.set_brightness(original)                           # type: ignore

        # Test status reporting
        status = self.display_manager.get_display_status()                      # type: ignore    
        self.assertIsInstance(status, dict)

    @unittest.skipUnless(DISPLAY_AVAILABLE, "Display module not available")
    def test_brightness_workflow(self):
        """Test brightness control workflow"""
        original_brightness = self.display_manager.get_brightness()                       # type: ignore

        # Test boost and restore cycle
        self.display_manager.boost_brightness(target_brightness=90)                       # type: ignore
        if self.display_manager.brightness_control_available:                             # type: ignore
            self.assertTrue(self.display_manager.is_brightness_boosted())                 # type: ignore

        self.display_manager.restore_brightness()                                         # type: ignore 
        if self.display_manager.brightness_control_available:                             # type: ignore
            self.assertFalse(self.display_manager.is_brightness_boosted())                # type: ignore


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
        import io
        import sys
        from contextlib import redirect_stdout, redirect_stderr
        from typing import cast

        console = Console()

        # Custom test runner with progress bar
        class RichTestResult(unittest.TextTestResult):
            def __init__(self, stream, descriptions, verbosity):
                super().__init__(stream, descriptions, verbosity)
                self.console = Console()
                self.progress = None
                self.task = None
                self.test_count: int = 0
                self.passed: int = 0
                self.failed: int = 0
                self.error_count: int = 0

            def startTest(self, test):
                super().startTest(test)
                self.test_count += 1
                if self.progress:
                    self.progress.update(self.task, description=f"Running: {test._testMethodName}")

            def addSuccess(self, test):
                super().addSuccess(test)
                self.passed += 1
                if self.progress:
                    self.progress.update(self.task, advance=1)

            def addError(self, test, err):
                super().addError(test, err)
                self.error_count += 1
                if self.progress:
                    self.progress.update(self.task, advance=1)

            def addFailure(self, test, err):
                super().addFailure(test, err)
                self.failed += 1
                if self.progress:
                    self.progress.update(self.task, advance=1)

        class RichTestRunner(unittest.TextTestRunner):
            def __init__(self, **kwargs):
                kwargs['resultclass'] = RichTestResult
                super().__init__(**kwargs)
                self.console = Console()

            def run(self, test):
                # Count total tests
                total_tests = test.countTestCases()

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[bold blue]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TextColumn("•"),
                    TimeElapsedColumn(),
                    console=self.console,
                    transient=False
                ) as progress:

                    # Create progress bar
                    task = progress.add_task("Running tests...", total=total_tests)

                    # Set up result object with progress reference
                    self.resultclass.progress = progress
                    self.resultclass.task = task

                    # Capture unittest output
                    output_buffer = io.StringIO()
                    with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
                        result = cast('RichTestResult', super().run(test))

                    # Display results
                    progress.update(task, description="Tests completed!", completed=total_tests)

                    # Create summary panel
                    if result.wasSuccessful():
                        status = "[green]✓ All tests passed![/green]"
                        border_color = "green"
                    else:
                        status = f"[red]✗ {len(result.failures)} failed, {len(result.errors)} errors[/red]"
                        border_color = "red"

                    summary = f"""
                            Total Tests: {total_tests}
                            Passed: {result.passed}  # type: ignore
                            Failed: {result.failed}  # type: ignore
                            Errors: {result.error_count}  # type: ignore
                            """

                    if result.failures or result.errors:
                        summary += "\n[bold red]Failures and Errors:[/bold red]\n"
                        for test, traceback in result.failures + result.errors:
                            summary += f"• {test}\n"

                    panel = Panel(
                        summary.strip(),
                        title=f"[bold]{status}[/bold]",
                        border_style=border_color,
                        padding=(1, 2)
                    )

                    self.console.print("\n", panel)

                    # Show captured output if there were issues
                    captured_output = output_buffer.getvalue()
                    if captured_output.strip():
                        self.console.print("\n[bold yellow]Test Output:[/bold yellow]")
                        self.console.print(captured_output)

                    return result

        # Run tests with rich output
        console.print("[bold blue]🧪 FocusBreaker Test Suite[/bold blue]")
        console.print("[dim]Testing display.py functionality[/dim]\n")

        # Preliminary Information
        console.print("[bold cyan]📋 Preliminary Information[/bold cyan]")
        
        # Import Status
        if DISPLAY_AVAILABLE:
            console.print("  [green]✓[/green] Display module imports successful")
            console.print(f"  [dim]DisplayManager available, Brightness control: {'Available' if BRIGHTNESS_CONTROL_AVAILABLE else 'Not available'}[/dim]")
        else:
            console.print("  [red]✗[/red] Display module import failed")
            console.print("  [dim]Display functionality will be limited[/dim]")
        
        # Display Detection
        try:
            features = detect_display_features()
            console.print("  [green]✓[/green] Display feature detection completed")
            console.print(f"  [dim]Multi-monitor: {features.get('multi_monitor_support', 'Unknown')}, DPI scaling: {features.get('dpi_scaling', 'Unknown')}[/dim]")
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Display feature detection failed: {e}")
        
        # Display Manager Initialization
        if DISPLAY_AVAILABLE:
            try:
                test_manager = DisplayManager()  # type: ignore
                resolution = test_manager.get_screen_resolution()
                console.print(f"  [green]✓[/green] Display manager initialized, Resolution: {resolution[0]}x{resolution[1]}")
                test_manager.cleanup()
            except Exception as e:
                console.print(f"  [yellow]⚠[/yellow] Display manager initialization failed: {e}")
        else:
            console.print("  [dim]-[/dim] Display manager initialization skipped (module not available)")
        
        console.print()

        # Load and run tests
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(__import__('__main__'))
        
        runner = RichTestRunner(verbosity=0, stream=sys.stdout)
        result = runner.run(suite)

        # Exit with appropriate code
        sys.exit(0 if result.wasSuccessful() else 1)

    except ImportError:
        # Fall back to basic unittest if rich is not available
        print("Rich library not available, using basic unittest output.\n")
        unittest.main(verbosity=2)