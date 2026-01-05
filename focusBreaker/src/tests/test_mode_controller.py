"""
Comprehensive test suite for mode controller functions using unittest
"""
import unittest
import sys
sys.path.insert(0, 'src')

from core.mode_controller import (
    can_snooze_break,
    can_skip_break,
    can_extend_session,
    requires_cooldown,
    get_cooldown_duration,
    has_breaks_during_work,
    get_available_modes,
    get_mode_display_name,
    get_mode_description,
    is_emergency_exit_available,
    is_valid_mode,
    get_mode_rules,
)

from data.models import Settings


class MockSettings(Settings):
    def __init__(self):
        self.allow_skip_in_normal_mode = True
        self.strict_cooldown_minutes = 20
        self.focused_mandatory_break_minutes = 30


class TestModeController(unittest.TestCase):

    def setUp(self):
        self.settings = MockSettings()

    def test_normal_mode(self):
        """Test Normal mode permissions and behavior"""
        # Permissions
        self.assertFalse(can_snooze_break('normal', None, None))
        self.assertTrue(can_skip_break('normal', self.settings))
        self.assertTrue(can_extend_session('normal'))
        self.assertFalse(requires_cooldown('normal'))
        self.assertEqual(get_cooldown_duration('normal', self.settings), 0)
        self.assertFalse(is_emergency_exit_available('normal'))
        
        # Behavior
        self.assertTrue(has_breaks_during_work('normal'))
        
        # Display
        self.assertEqual(get_mode_display_name('normal'), 'Normal mode')
        self.assertIn('Flexible breaks', get_mode_description('normal'))

    def test_strict_mode(self):
        """Test Strict mode permissions and behavior"""
        # Permissions
        self.assertFalse(can_snooze_break('strict', None, None))
        self.assertFalse(can_skip_break('strict', self.settings))
        self.assertFalse(can_extend_session('strict'))
        self.assertTrue(requires_cooldown('strict'))
        self.assertEqual(get_cooldown_duration('strict', self.settings), 20)
        self.assertTrue(is_emergency_exit_available('strict'))
        
        # Behavior
        self.assertTrue(has_breaks_during_work('strict'))
        
        # Display
        self.assertEqual(get_mode_display_name('strict'), 'Strict mode')
        self.assertIn('Enforced', get_mode_description('strict'))

    def test_focused_mode(self):
        """Test Focused mode permissions and behavior"""
        # Permissions
        self.assertFalse(can_snooze_break('focused', None, None))
        self.assertFalse(can_skip_break('focused', self.settings))
        self.assertFalse(can_extend_session('focused'))
        self.assertTrue(requires_cooldown('focused'))
        self.assertEqual(get_cooldown_duration('focused', self.settings), 30)
        self.assertTrue(is_emergency_exit_available('focused'))
        
        # Behavior
        self.assertFalse(has_breaks_during_work('focused'))
        
        # Display
        self.assertEqual(get_mode_display_name('focused'), 'Focused mode')
        self.assertIn('No interruptions', get_mode_description('focused'))

    def test_mode_validation(self):
        """Test mode validation functions"""
        # Valid modes
        self.assertTrue(is_valid_mode('normal'))
        self.assertTrue(is_valid_mode('strict'))
        self.assertTrue(is_valid_mode('focused'))
        
        # Invalid modes
        self.assertFalse(is_valid_mode('invalid'))
        self.assertFalse(is_valid_mode(''))
        self.assertFalse(is_valid_mode(None))  # type: ignore
        
        # Available modes
        modes = get_available_modes()
        self.assertEqual(len(modes), 3)
        self.assertIn('normal', modes)
        self.assertIn('strict', modes)
        self.assertIn('focused', modes)

    def test_mode_rules(self):
        """Test comprehensive mode rules dictionary"""
        # Normal mode rules
        normal_rules = get_mode_rules('normal', self.settings)
        self.assertFalse(normal_rules['can_snooze'])
        self.assertTrue(normal_rules['can_skip'])
        self.assertTrue(normal_rules['can_extend_session'])
        self.assertFalse(normal_rules['requires_cooldown'])
        self.assertEqual(normal_rules['cooldown_duration_minutes'], 0)
        self.assertTrue(normal_rules['has_breaks_during_work'])
        self.assertEqual(normal_rules['display_name'], 'Normal mode')
        
        # Strict mode rules
        strict_rules = get_mode_rules('strict', self.settings)
        self.assertFalse(strict_rules['can_snooze'])
        self.assertFalse(strict_rules['can_skip'])
        self.assertFalse(strict_rules['can_extend_session'])
        self.assertTrue(strict_rules['requires_cooldown'])
        self.assertEqual(strict_rules['cooldown_duration_minutes'], 20)
        self.assertTrue(strict_rules['has_breaks_during_work'])
        
        # Focused mode rules
        focused_rules = get_mode_rules('focused', self.settings)
        self.assertFalse(focused_rules['can_snooze'])
        self.assertFalse(focused_rules['can_skip'])
        self.assertFalse(focused_rules['can_extend_session'])
        self.assertTrue(focused_rules['requires_cooldown'])
        self.assertEqual(focused_rules['cooldown_duration_minutes'], 30)
        self.assertFalse(focused_rules['has_breaks_during_work'])

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Invalid mode strings
        self.assertEqual(get_mode_display_name('invalid'), 'Unknown Mode')
        self.assertEqual(get_mode_description('invalid'), 'Unknown mode')
        self.assertFalse(has_breaks_during_work('invalid'))
        self.assertEqual(get_cooldown_duration('invalid', self.settings), 0)
        
        # None inputs (where applicable)
        self.assertFalse(can_snooze_break(None, None, None))        # type: ignore
        self.assertFalse(can_skip_break(None, self.settings))       # type: ignore
        self.assertFalse(can_extend_session(None))                  # type: ignore
        self.assertFalse(requires_cooldown(None))                   # type: ignore
        self.assertFalse(is_valid_mode(None))                       # type: ignore


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
        console.print("[dim]Testing mode_controller.py functionality[/dim]\n")

        # Preliminary Information
        console.print("[bold cyan]📋 Preliminary Information[/bold cyan]")
        
        # Import Status
        try:
            from core.mode_controller import get_available_modes, get_mode_display_name
            console.print("  [green]✓[/green] Mode controller module imports successful")
        except ImportError as e:
            console.print(f"  [red]✗[/red] Mode controller module import failed: {e}")
        
        # Available Modes
        try:
            modes = get_available_modes()
            console.print(f"  [green]✓[/green] Available modes: {', '.join(modes)}")
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Mode detection failed: {e}")
        
        # Mode Display Names
        try:
            for mode in ['normal', 'strict', 'focused']:
                name = get_mode_display_name(mode)
                console.print(f"  [dim]• {mode} → {name}[/dim]")
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Mode display name resolution failed: {e}")
        
        # Settings Integration
        try:
            from data.models import Settings
            console.print("  [green]✓[/green] Settings model available for mode rules")
        except ImportError:
            console.print("  [yellow]⚠[/yellow] Settings model not available")
        
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