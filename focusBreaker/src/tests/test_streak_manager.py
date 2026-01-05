import unittest
import sys
sys.path.insert(0, 'src')
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
from core.streak_manager import (
    update_session_streak,
    update_perfect_session_streak,
    update_daily_consistency,
    update_streaks_after_session,
    get_streak_status,
    get_all_streaks_summary,
    predict_streak_risk,
    check_streak_milestone,
    can_recover_streak,
    get_streak_statistics
)


class TestStreakManager(unittest.TestCase):

    def setUp(self):
        self.db = Mock()
        self.streak = Mock()
        self.streak.current_count = 5
        self.streak.best_count = 10
        self.streak.last_updated = '2024-01-01T10:00:00'
        self.streak.streak_type = 'session_streak'

    def test_update_session_streak_valid(self):
        self.db.getStreak.return_value = self.streak
        update_session_streak(True, self.db)
        self.db.updateStreak.assert_called_with('session_streak', 6, 10)

    def test_update_session_streak_invalid(self):
        self.db.getStreak.return_value = self.streak
        update_session_streak(False, self.db)
        self.db.updateStreak.assert_called_with('session_streak', 0, 10)

    def test_update_session_streak_no_streak(self):
        self.db.getStreak.return_value = None
        update_session_streak(True, self.db)
        self.db.updateStreak.assert_not_called()

    def test_update_perfect_session_streak_perfect(self):
        self.db.getStreak.return_value = self.streak
        update_perfect_session_streak(True, self.db)
        self.db.updateStreak.assert_called_with('perfect_session', 6, 10)

    def test_update_perfect_session_streak_not_perfect(self):
        self.db.getStreak.return_value = self.streak
        update_perfect_session_streak(False, self.db)
        self.db.updateStreak.assert_called_with('perfect_session', 0, 10)

    def test_update_daily_consistency_consecutive(self):
        self.streak.last_updated = '2024-01-01'
        self.db.getStreak.return_value = self.streak
        update_daily_consistency('2024-01-02', self.db)
        self.db.updateStreak.assert_called_with('daily_consistency', 6, 10)

    def test_update_daily_consistency_gap(self):
        self.streak.last_updated = '2024-01-01'
        self.db.getStreak.return_value = self.streak
        update_daily_consistency('2024-01-04', self.db)
        self.db.updateStreak.assert_called_with('daily_consistency', 1, 10)

    def test_update_daily_consistency_same_day(self):
        self.streak.last_updated = '2024-01-01'
        self.db.getStreak.return_value = self.streak
        update_daily_consistency('2024-01-01', self.db)
        self.db.updateStreak.assert_not_called()

    def test_update_streaks_after_session(self):
        session = Mock()
        session.status = 'completed'
        session.breaks_skipped = 0
        session.breaks_snoozed = 0
        session.emergency_exits = 0
        session.created_at = '2024-01-02'  # Different day
        self.db.getSession.return_value = session
        self.db.getStreak.return_value = self.streak
        update_streaks_after_session(1, self.db)
        self.assertEqual(self.db.updateStreak.call_count, 3)

    def test_get_streak_status_active(self):
        self.db.getStreak.return_value = self.streak
        result = get_streak_status('session_streak', self.db)
        self.assertEqual(result['current'], 5)
        self.assertTrue(result['is_active'])

    def test_get_streak_status_inactive(self):
        self.streak.current_count = 0
        self.db.getStreak.return_value = self.streak
        result = get_streak_status('session_streak', self.db)
        self.assertFalse(result['is_active'])

    def test_get_streak_status_none(self):
        self.db.getStreak.return_value = None
        result = get_streak_status('session_streak', self.db)
        self.assertEqual(result, {})

    def test_get_all_streaks_summary(self):
        self.db.getStreak.return_value = self.streak
        result = get_all_streaks_summary(self.db)
        self.assertIn('session_streak', result)
        self.assertIn('perfect_session', result)
        self.assertIn('daily_consistency', result)

    def test_predict_streak_risk_not_daily(self):
        result = predict_streak_risk('session_streak', self.db)
        self.assertEqual(result, {'at_risk': False})

    def test_predict_streak_risk_no_streak(self):
        self.db.getStreak.return_value = None
        result = predict_streak_risk('daily_consistency', self.db)
        self.assertEqual(result, {'at_risk': False})

    def test_predict_streak_risk_zero_count(self):
        self.streak.current_count = 0
        self.db.getStreak.return_value = self.streak
        result = predict_streak_risk('daily_consistency', self.db)
        self.assertEqual(result, {'at_risk': False})

    def test_predict_streak_risk_low_risk(self):
        self.streak.last_updated = datetime.now().isoformat()
        self.db.getStreak.return_value = self.streak
        result = predict_streak_risk('daily_consistency', self.db)
        self.assertEqual(result['risk_level'], 'low')

    def test_predict_streak_risk_high_risk(self):
        past_time = datetime.now() - timedelta(hours=20)
        self.streak.last_updated = past_time.isoformat()
        self.db.getStreak.return_value = self.streak
        result = predict_streak_risk('daily_consistency', self.db)
        self.assertEqual(result['risk_level'], 'high')

    def test_check_streak_milestone_none(self):
        self.streak.current_count = 3
        self.db.getStreak.return_value = self.streak
        result = check_streak_milestone('session_streak', self.db)
        self.assertIsNone(result)

    def test_check_streak_milestone_reached(self):
        self.streak.current_count = 5
        self.db.getStreak.return_value = self.streak
        result = check_streak_milestone('session_streak', self.db)
        self.assertIsNotNone(result)
        self.assertEqual(result['milestone'], 5)                    # type: ignore                        

    def test_can_recover_streak_not_daily(self):
        result = can_recover_streak('session_streak', self.db)
        self.assertFalse(result)

    def test_can_recover_streak_active(self):
        self.streak.current_count = 5
        self.db.getStreak.return_value = self.streak
        result = can_recover_streak('daily_consistency', self.db)
        self.assertFalse(result)

    def test_can_recover_streak_recent(self):
        self.streak.current_count = 0
        recent_time = datetime.now() - timedelta(hours=12)
        self.streak.last_updated = recent_time.isoformat()
        self.db.getStreak.return_value = self.streak
        result = can_recover_streak('daily_consistency', self.db)
        self.assertTrue(result)

    def test_can_recover_streak_old(self):
        self.streak.current_count = 0
        old_time = datetime.now() - timedelta(hours=30)
        self.streak.last_updated = old_time.isoformat()
        self.db.getStreak.return_value = self.streak
        result = can_recover_streak('daily_consistency', self.db)
        self.assertFalse(result)

    def test_get_streak_statistics(self):
        streaks = [self.streak]
        self.db.getAllStreaks.return_value = streaks
        stats = {
            'total_sessions': 10,
            'completed_sessions': 8,
            'total_breaks_taken': 20,
            'total_breaks_snoozed': 5,
            'total_breaks_skipped': 2,
            'perfect_sessions': 5,
            'total_emergency_exits': 1
        }
        self.db.getSessionStats.return_value = stats
        result = get_streak_statistics(self.db)
        self.assertEqual(result['total_sessions_completed'], 8)
        self.assertEqual(result['perfect_sessions_count'], 5)

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
        console.print("[dim]Testing streak_manager.py functionality[/dim]\n")

        # Preliminary Information
        console.print("[bold cyan]📋 Preliminary Information[/bold cyan]")
        
        # Import Status
        try:
            from core.streak_manager import update_session_streak, get_streak_status
            console.print("  [green]✓[/green] Streak manager module imports successful")
        except ImportError as e:
            console.print(f"  [red]✗[/red] Streak manager module import failed: {e}")
        
        # DateTime Status
        try:
            from datetime import datetime, timedelta
            console.print("  [green]✓[/green] DateTime module available for streak calculations")
        except ImportError:
            console.print("  [red]✗[/red] DateTime module not available")
        
        # Mock Database
        try:
            from unittest.mock import Mock
            mock_db = Mock()
            console.print("  [green]✓[/green] Mock database setup available")
        except ImportError:
            console.print("  [yellow]⚠[/yellow] Mock library not available")
        
        # Streak Functions
        try:
            mock_streak = Mock()
            mock_streak.current_count = 5
            mock_streak.best_count = 10
            mock_db.getStreak.return_value = mock_streak
            update_session_streak(True, mock_db)
            console.print("  [green]✓[/green] Streak update functions working")
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Streak function test failed: {e}")
        
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