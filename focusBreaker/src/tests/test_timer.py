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
        console.print("[dim]Testing timer.py functionality[/dim]\n")

        # Preliminary Information
        console.print("[bold cyan]📋 Preliminary Information[/bold cyan]")
        
        # Import Status
        try:
            from core.timer import Timer, WorkTimer, BreakTimer, TimerState
            console.print("  [green]✓[/green] Timer module imports successful")
        except ImportError as e:
            console.print(f"  [red]✗[/red] Timer module import failed: {e}")
        
        # Threading Status
        try:
            import threading
            console.print("  [green]✓[/green] Threading module available")
        except ImportError:
            console.print("  [red]✗[/red] Threading module not available")
            console.print("  [dim]Timer functionality will be limited[/dim]")
        
        # Time Module Status
        try:
            import time
            console.print("  [green]✓[/green] Time module available")
        except ImportError:
            console.print("  [red]✗[/red] Time module not available")
        
        # Timer Initialization
        try:
            test_timer = Timer(1.0)
            console.print("  [green]✓[/green] Timer initialized successfully")
            console.print(f"  [dim]Timer state: {test_timer.state.name}[/dim]")
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Timer initialization failed: {e}")
        
        # Timer States
        try:
            console.print(f"  [dim]Available timer states: {', '.join([state.name for state in TimerState])}[/dim]")
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Timer state enumeration failed: {e}")
        
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