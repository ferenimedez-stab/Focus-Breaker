"""
Comprehensive test suite for scheduler functions using unittest
"""
import unittest
import sys
sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from core.scheduler import (
    calculate_break_schedule,
    calculate_elapsed_minutes,
    get_work_interval_for_mode,
    get_break_duration_for_mode,
    get_next_break_time,
    validate_break_schedule,
    optimize_break_schedule_for_energy,
)
from data.models import Settings


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
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()


class TestScheduler(unittest.TestCase):

    def setUp(self):
        self.settings = MockSettings()

    def test_calculate_break_schedule(self):
        """Test break schedule calculation for different modes and durations"""
        # Normal mode
        normal_120 = calculate_break_schedule('normal', 120, self.settings)
        self.assertEqual(normal_120, [25, 50, 75, 100])
        
        normal_50 = calculate_break_schedule('normal', 50, self.settings)
        self.assertEqual(normal_50, [25])
        
        normal_25 = calculate_break_schedule('normal', 25, self.settings)
        self.assertEqual(normal_25, [])
        
        normal_0 = calculate_break_schedule('normal', 0, self.settings)
        self.assertEqual(normal_0, [])
        
        # Strict mode
        strict_120 = calculate_break_schedule('strict', 120, self.settings)
        self.assertEqual(strict_120, [52, 104])
        
        strict_60 = calculate_break_schedule('strict', 60, self.settings)
        self.assertEqual(strict_60, [52])
        
        # Focused mode
        focused_120 = calculate_break_schedule('focused', 120, self.settings)
        self.assertEqual(focused_120, [])
        
        # Invalid mode (should use default 25)
        invalid_120 = calculate_break_schedule('invalid', 120, self.settings)
        self.assertEqual(invalid_120, [25, 50, 75, 100])

    def test_validate_break_schedule(self):
        """Test break schedule validation"""
        # Valid schedules
        self.assertTrue(validate_break_schedule([], 120))
        self.assertTrue(validate_break_schedule([25, 50, 75], 120))
        self.assertTrue(validate_break_schedule([30], 60))
        
        # Invalid: starts with 0 or negative
        self.assertFalse(validate_break_schedule([0, 25], 120))
        self.assertFalse(validate_break_schedule([-5, 25], 120))
        
        # Invalid: exceeds work duration
        self.assertFalse(validate_break_schedule([25, 50, 150], 120))
        self.assertFalse(validate_break_schedule([120], 120))
        self.assertTrue(validate_break_schedule([119], 120))
        
        # Invalid: not sorted
        self.assertFalse(validate_break_schedule([50, 25, 75], 120))
        
        # Invalid: duplicates
        self.assertFalse(validate_break_schedule([25, 25, 75], 120))

    def test_get_work_interval_for_mode(self):
        """Test work interval retrieval for modes"""
        self.assertEqual(get_work_interval_for_mode('normal', self.settings), 25)
        self.assertEqual(get_work_interval_for_mode('strict', self.settings), 52)
        self.assertEqual(get_work_interval_for_mode('focused', self.settings), 0)
        self.assertEqual(get_work_interval_for_mode('invalid', self.settings), 25)

    def test_get_break_duration_for_mode(self):
        """Test break duration retrieval for modes"""
        self.assertEqual(get_break_duration_for_mode('normal', self.settings), 5)
        self.assertEqual(get_break_duration_for_mode('strict', self.settings), 17)
        self.assertEqual(get_break_duration_for_mode('focused', self.settings), 30)
        self.assertEqual(get_break_duration_for_mode('invalid', self.settings), 30)

    def test_get_next_break_time(self):
        """Test finding next upcoming break"""
        breaks = [25, 50, 75, 100]
        
        self.assertEqual(get_next_break_time(0, breaks), 25)
        self.assertEqual(get_next_break_time(20, breaks), 25)
        self.assertEqual(get_next_break_time(25, breaks), 50)
        self.assertEqual(get_next_break_time(50, breaks), 75)
        self.assertIsNone(get_next_break_time(100, breaks))
        self.assertIsNone(get_next_break_time(150, breaks))
        
        # Empty breaks
        self.assertIsNone(get_next_break_time(0, []))

    def test_calculate_elapsed_minutes(self):
        """Test elapsed time calculation"""
        # Mock current time
        start_time = (datetime.now() - timedelta(minutes=30)).isoformat()
        elapsed = calculate_elapsed_minutes(start_time)
        self.assertAlmostEqual(elapsed, 30, delta=1)
        
        # Zero elapsed
        start_time_now = datetime.now().isoformat()
        elapsed_zero = calculate_elapsed_minutes(start_time_now)
        self.assertEqual(elapsed_zero, 0)

    def test_optimize_break_schedule_for_energy(self):
        """Test energy-based break optimization"""
        # Morning person
        morning = optimize_break_schedule_for_energy(120, "morning_person")
        self.assertEqual(morning, [20, 40, 70, 100])
        
        # Afternoon slump
        afternoon = optimize_break_schedule_for_energy(120, "afternoon_slump")
        self.assertEqual(afternoon, [30, 60, 90])
        
        # Night owl
        night = optimize_break_schedule_for_energy(120, "night_owl")
        self.assertEqual(night, [35, 70, 105])
        
        # Default (normal)
        default = optimize_break_schedule_for_energy(120, "normal")
        self.assertEqual(default, [25, 50, 75, 100])
        
        # Shorter duration
        short = optimize_break_schedule_for_energy(50, "normal")
        self.assertEqual(short, [25])

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Very short durations
        self.assertEqual(calculate_break_schedule('normal', 1, self.settings), [])
        self.assertEqual(calculate_break_schedule('strict', 10, self.settings), [])
        
        # Large durations
        large = calculate_break_schedule('normal', 1000, self.settings)
        self.assertGreater(len(large), 10)
        
        # Validation with edge values
        self.assertTrue(validate_break_schedule([1], 120))
        self.assertFalse(validate_break_schedule([120], 120))
        self.assertTrue(validate_break_schedule([119], 120))


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
Passed: {result.passed}
Failed: {result.failed}
Errors: {result.error_count}
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
        console.print("[dim]Testing scheduler.py functionality[/dim]\n")

        # Preliminary Information
        console.print("[bold cyan]📋 Preliminary Information[/bold cyan]")
        
        # Import Status
        try:
            from core.scheduler import calculate_break_schedule, get_work_interval_for_mode
            console.print("  [green]✓[/green] Scheduler module imports successful")
        except ImportError as e:
            console.print(f"  [red]✗[/red] Scheduler module import failed: {e}")
        
        # DateTime Status
        try:
            from datetime import datetime, timedelta
            current_time = datetime.now()
            console.print(f"  [green]✓[/green] DateTime module available, Current time: {current_time.strftime('%H:%M:%S')}")
        except ImportError:
            console.print("  [red]✗[/red] DateTime module not available")
        
        # Settings Integration
        try:
            from data.models import Settings
            console.print("  [green]✓[/green] Settings model available")
        except ImportError:
            console.print("  [yellow]⚠[/yellow] Settings model not available")
        
        # Scheduler Functions
        try:
            test_schedule = calculate_break_schedule('normal', 120, None)           # type: ignore
            console.print(f"  [green]✓[/green] Break schedule calculation working, Sample: {test_schedule}")
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Break schedule calculation failed: {e}")
        
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