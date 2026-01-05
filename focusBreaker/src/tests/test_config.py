"""
Comprehensive test suite for config.py using unittest
"""
import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, 'src')

from config import (
    AppPaths, AudioConfig, MediaConfig, ModeConfig, EscapeHatchConfig,
    StreakConfig, UIConfig, NotificationConfig, LogConfig, FeatureFlags,
    ValidationRules, Environment, initialize_app, setup_logging,
    APP_NAME, APP_VERSION, APP_AUTHOR
)


class TestAppPaths(unittest.TestCase):
    """Test AppPaths class functionality"""

    def setUp(self):
        """Set up test environment"""
        self.test_base = Path(tempfile.mkdtemp())
        # Mock the BASE_DIR to use our test directory
        with patch.object(AppPaths, 'BASE_DIR', self.test_base):
            with patch.object(AppPaths, 'SRC_DIR', self.test_base / "src"):
                self.app_paths = AppPaths()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_base, ignore_errors=True)

    def test_get_database_path(self):
        """Test database path retrieval"""
        with patch('config.AppPaths.DATABASE_FILE', self.test_base / "focusbreaker.db"):
            expected = self.test_base / "focusbreaker.db"
            actual = AppPaths.get_database_path()
            self.assertEqual(actual, expected)

    def test_get_media_dir_normal_defaults(self):
        """Test media directory for normal mode defaults"""
        with patch.object(AppPaths, 'MEDIA_NORMAL_DEFAULTS', self.test_base / "normal_defaults"):
            path = AppPaths.get_media_dir('normal', user_content=False)
            self.assertEqual(path, self.test_base / "normal_defaults")

    def test_get_media_dir_normal_user(self):
        """Test media directory for normal mode user content"""
        with patch.object(AppPaths, 'MEDIA_NORMAL_USER', self.test_base / "normal_user"):
            path = AppPaths.get_media_dir('normal', user_content=True)
            self.assertEqual(path, self.test_base / "normal_user")

    def test_get_media_dir_strict_defaults(self):
        """Test media directory for strict mode defaults"""
        with patch.object(AppPaths, 'MEDIA_STRICT_DEFAULTS', self.test_base / "strict_defaults"):
            path = AppPaths.get_media_dir('strict', user_content=False)
            self.assertEqual(path, self.test_base / "strict_defaults")

    def test_get_media_dir_focused_user(self):
        """Test media directory for focused mode user content"""
        with patch.object(AppPaths, 'MEDIA_FOCUSED_USER', self.test_base / "focused_user"):
            path = AppPaths.get_media_dir('focused', user_content=True)
            self.assertEqual(path, self.test_base / "focused_user")

    def test_get_media_dir_invalid_mode(self):
        """Test media directory with invalid mode"""
        with self.assertRaises(ValueError) as context:
            AppPaths.get_media_dir('invalid_mode')
        self.assertIn("Invalid mode: invalid_mode", str(context.exception))

    def test_ensure_directories_exist(self):
        """Test directory creation"""
        with patch.object(AppPaths, 'BASE_DIR', self.test_base):
            with patch.object(AppPaths, 'SRC_DIR', self.test_base / "src"):
                # Mock all the directory attributes
                dirs_to_create = [
                    self.test_base / "src" / "assets",
                    self.test_base / "src" / "assets" / "audio",
                    self.test_base / "src" / "assets" / "media",
                    self.test_base / "src" / "assets" / "icons",
                    self.test_base / "src" / "assets" / "media" / "normal" / "defaults",
                    self.test_base / "src" / "assets" / "media" / "normal" / "user",
                    self.test_base / "src" / "assets" / "media" / "strict" / "defaults",
                    self.test_base / "src" / "assets" / "media" / "strict" / "user",
                    self.test_base / "src" / "assets" / "media" / "focused" / "defaults",
                    self.test_base / "src" / "assets" / "media" / "focused" / "user",
                    self.test_base / "src" / "data",
                    self.test_base / "src" / "logs"
                ]

                # Ensure directories don't exist initially
                for d in dirs_to_create:
                    self.assertFalse(d.exists())

                # Call ensure_directories_exist with mocked paths
                with patch.multiple(AppPaths,
                    ASSETS_DIR=self.test_base / "src" / "assets",
                    AUDIO_DIR=self.test_base / "src" / "assets" / "audio",
                    MEDIA_DIR=self.test_base / "src" / "assets" / "media",
                    ICONS_DIR=self.test_base / "src" / "assets" / "icons",
                    MEDIA_NORMAL_DEFAULTS=self.test_base / "src" / "assets" / "media" / "normal" / "defaults",
                    MEDIA_NORMAL_USER=self.test_base / "src" / "assets" / "media" / "normal" / "user",
                    MEDIA_STRICT_DEFAULTS=self.test_base / "src" / "assets" / "media" / "strict" / "defaults",
                    MEDIA_STRICT_USER=self.test_base / "src" / "assets" / "media" / "strict" / "user",
                    MEDIA_FOCUSED_DEFAULTS=self.test_base / "src" / "assets" / "media" / "focused" / "defaults",
                    MEDIA_FOCUSED_USER=self.test_base / "src" / "assets" / "media" / "focused" / "user",
                    DATA_DIR=self.test_base / "src" / "data",
                    LOGS_DIR=self.test_base / "src" / "logs"):
                    AppPaths.ensure_directories_exist()

                    # Check that directories were created
                    for d in dirs_to_create:
                        self.assertTrue(d.exists(), f"Directory {d} was not created")


class TestModeConfig(unittest.TestCase):
    """Test ModeConfig class functionality"""

    def test_get_focused_break_duration_scaling_enabled(self):
        """Test break duration calculation with scaling enabled"""
        # Test 0-2 hours -> 30 min (0-119 minutes)
        self.assertEqual(ModeConfig.get_focused_break_duration(90), 30)
        self.assertEqual(ModeConfig.get_focused_break_duration(119), 30)

        # Test 2-4 hours -> 45 min (120-239 minutes)
        self.assertEqual(ModeConfig.get_focused_break_duration(120), 45)
        self.assertEqual(ModeConfig.get_focused_break_duration(150), 45)
        self.assertEqual(ModeConfig.get_focused_break_duration(239), 45)

        # Test 4+ hours -> 60 min (240+ minutes)
        self.assertEqual(ModeConfig.get_focused_break_duration(240), 60)
        self.assertEqual(ModeConfig.get_focused_break_duration(300), 60)
        self.assertEqual(ModeConfig.get_focused_break_duration(1000), 60)

    def test_get_focused_break_duration_scaling_disabled(self):
        """Test break duration calculation with scaling disabled"""
        original_enabled = ModeConfig.FOCUSED_BREAK_SCALING_ENABLED
        try:
            ModeConfig.FOCUSED_BREAK_SCALING_ENABLED = False
            self.assertEqual(ModeConfig.get_focused_break_duration(90), 30)
            self.assertEqual(ModeConfig.get_focused_break_duration(300), 30)
        finally:
            ModeConfig.FOCUSED_BREAK_SCALING_ENABLED = original_enabled


class TestValidationRules(unittest.TestCase):
    """Test ValidationRules class functionality"""

    def test_validate_work_duration_valid(self):
        """Test valid work duration"""
        self.assertTrue(ValidationRules.validate_work_duration(25))
        self.assertTrue(ValidationRules.validate_work_duration(60))
        self.assertTrue(ValidationRules.validate_work_duration(480))

    def test_validate_work_duration_too_short(self):
        """Test work duration too short"""
        with self.assertRaises(ValueError) as context:
            ValidationRules.validate_work_duration(4)
        self.assertIn("must be at least 5 minutes", str(context.exception))

    def test_validate_work_duration_too_long(self):
        """Test work duration too long"""
        with self.assertRaises(ValueError) as context:
            ValidationRules.validate_work_duration(481)
        self.assertIn("cannot exceed 480 minutes", str(context.exception))

    def test_validate_break_duration_valid(self):
        """Test valid break duration"""
        self.assertTrue(ValidationRules.validate_break_duration(5))
        self.assertTrue(ValidationRules.validate_break_duration(30))
        self.assertTrue(ValidationRules.validate_break_duration(60))

    def test_validate_break_duration_too_short(self):
        """Test break duration too short"""
        with self.assertRaises(ValueError) as context:
            ValidationRules.validate_break_duration(0)
        self.assertIn("must be at least 1 minutes", str(context.exception))

    def test_validate_break_duration_too_long(self):
        """Test break duration too long"""
        with self.assertRaises(ValueError) as context:
            ValidationRules.validate_break_duration(61)
        self.assertIn("cannot exceed 60 minutes", str(context.exception))

    def test_validate_volume_valid(self):
        """Test valid volume"""
        self.assertTrue(ValidationRules.validate_volume(0))
        self.assertTrue(ValidationRules.validate_volume(50))
        self.assertTrue(ValidationRules.validate_volume(100))

    def test_validate_volume_too_low(self):
        """Test volume too low"""
        with self.assertRaises(ValueError) as context:
            ValidationRules.validate_volume(-1)
        self.assertIn("must be between 0 and 100", str(context.exception))

    def test_validate_volume_too_high(self):
        """Test volume too high"""
        with self.assertRaises(ValueError) as context:
            ValidationRules.validate_volume(101)
        self.assertIn("must be between 0 and 100", str(context.exception))

    def test_validate_mode_valid(self):
        """Test valid modes"""
        self.assertTrue(ValidationRules.validate_mode('normal'))
        self.assertTrue(ValidationRules.validate_mode('strict'))
        self.assertTrue(ValidationRules.validate_mode('focused'))
        self.assertTrue(ValidationRules.validate_mode('NORMAL'))  # Case insensitive

    def test_validate_mode_invalid(self):
        """Test invalid mode"""
        with self.assertRaises(ValueError) as context:
            ValidationRules.validate_mode('invalid')
        self.assertIn("Invalid mode 'invalid'", str(context.exception))

    def test_validate_file_size_valid(self):
        """Test valid file size"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'x' * 1024)  # 1KB file
            temp_path = Path(f.name)

        try:
            self.assertTrue(ValidationRules.validate_file_size(temp_path, 1))
        finally:
            temp_path.unlink()

    def test_validate_file_size_too_large(self):
        """Test file size too large"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'x' * (2 * 1024 * 1024))  # 2MB file
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ValueError) as context:
                ValidationRules.validate_file_size(temp_path, 1)  # Max 1MB
            self.assertIn("File too large", str(context.exception))
        finally:
            temp_path.unlink()

    def test_validate_file_size_not_found(self):
        """Test file not found"""
        nonexistent = Path("nonexistent_file.txt")
        with self.assertRaises(FileNotFoundError) as context:
            ValidationRules.validate_file_size(nonexistent, 10)
        self.assertIn("File not found", str(context.exception))


class TestEnvironment(unittest.TestCase):
    """Test Environment class functionality"""

    def test_is_development_debug_mode(self):
        """Test development mode detection via debug flag"""
        original_debug = FeatureFlags.DEBUG_MODE
        try:
            FeatureFlags.DEBUG_MODE = True
            self.assertTrue(Environment.is_development())
            self.assertFalse(Environment.is_production())
        finally:
            FeatureFlags.DEBUG_MODE = original_debug

    @patch.dict(os.environ, {'FOCUSBREAKER_ENV': 'development'})
    def test_is_development_env_var(self):
        """Test development mode detection via environment variable"""
        original_debug = FeatureFlags.DEBUG_MODE
        try:
            FeatureFlags.DEBUG_MODE = False
            self.assertTrue(Environment.is_development())
            self.assertFalse(Environment.is_production())
        finally:
            FeatureFlags.DEBUG_MODE = original_debug

    @patch.dict(os.environ, {}, clear=True)
    def test_is_production(self):
        """Test production mode detection"""
        original_debug = FeatureFlags.DEBUG_MODE
        try:
            FeatureFlags.DEBUG_MODE = False
            self.assertFalse(Environment.is_development())
            self.assertTrue(Environment.is_production())
        finally:
            FeatureFlags.DEBUG_MODE = original_debug

    @patch('platform.system')
    def test_is_windows(self, mock_system):
        """Test Windows detection"""
        mock_system.return_value = "Windows"
        self.assertTrue(Environment.is_windows())
        self.assertFalse(Environment.is_macos())
        self.assertFalse(Environment.is_linux())

    @patch('platform.system')
    def test_is_macos(self, mock_system):
        """Test macOS detection"""
        mock_system.return_value = "Darwin"
        self.assertFalse(Environment.is_windows())
        self.assertTrue(Environment.is_macos())
        self.assertFalse(Environment.is_linux())

    @patch('platform.system')
    def test_is_linux(self, mock_system):
        """Test Linux detection"""
        mock_system.return_value = "Linux"
        self.assertFalse(Environment.is_windows())
        self.assertFalse(Environment.is_macos())
        self.assertTrue(Environment.is_linux())

    @patch('platform.system')
    def test_get_platform_name(self, mock_system):
        """Test platform name retrieval"""
        mock_system.return_value = "TestPlatform"
        self.assertEqual(Environment.get_platform_name(), "TestPlatform")


class TestConstants(unittest.TestCase):
    """Test configuration constants"""

    def test_app_info_constants(self):
        """Test application info constants"""
        self.assertEqual(APP_NAME, "FocusBreaker")
        self.assertEqual(APP_VERSION, "0.3.0")
        self.assertEqual(APP_AUTHOR, "Fernanne Hannah Enimedez")

    def test_audio_config_constants(self):
        """Test audio configuration constants"""
        self.assertEqual(AudioConfig.DEFAULT_MEDIA_VOLUME, 80)
        self.assertEqual(AudioConfig.MIN_VOLUME, 0)
        self.assertEqual(AudioConfig.MAX_VOLUME, 100)
        self.assertIn('.mp3', AudioConfig.SUPPORTED_AUDIO_FORMATS)

    def test_media_config_constants(self):
        """Test media configuration constants"""
        self.assertEqual(MediaConfig.MAX_VIDEO_SIZE_MB, 100)
        self.assertEqual(MediaConfig.MAX_IMAGE_SIZE_MB, 10)
        self.assertIn('.mp4', MediaConfig.SUPPORTED_VIDEO_FORMATS)

    def test_mode_config_constants(self):
        """Test mode configuration constants"""
        self.assertEqual(ModeConfig.NORMAL_WORK_INTERVAL_MINUTES, 25)
        self.assertEqual(ModeConfig.STRICT_WORK_INTERVAL_MINUTES, 52)
        self.assertEqual(ModeConfig.FOCUSED_MANDATORY_BREAK_MINUTES, 30)

    def test_ui_config_constants(self):
        """Test UI configuration constants"""
        self.assertEqual(UIConfig.DEFAULT_WINDOW_WIDTH, 800)
        self.assertEqual(UIConfig.COLOR_PRIMARY, "#2196F3")
        self.assertEqual(UIConfig.ANIMATION_FAST, 150)

    def test_feature_flags(self):
        """Test feature flag constants"""
        self.assertTrue(FeatureFlags.ENABLE_BREAK_MUSIC)
        self.assertFalse(FeatureFlags.ENABLE_CLOUD_SYNC)
        self.assertFalse(FeatureFlags.DEBUG_MODE)


class TestInitializationFunctions(unittest.TestCase):
    """Test initialization functions"""

    def setUp(self):
        """Set up test environment"""
        self.test_base = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_base, ignore_errors=True)

    @patch('config.AppPaths.ensure_directories_exist')
    @patch('config.setup_logging')
    @patch('builtins.print')
    def test_initialize_app(self, mock_print, mock_setup_logging, mock_ensure_dirs):
        """Test app initialization"""
        initialize_app()

        # Check that directories were ensured
        mock_ensure_dirs.assert_called_once()

        # Check that logging was set up
        mock_setup_logging.assert_called_once()

        # Check that prints were called
        self.assertEqual(mock_print.call_count, 4)  # 3 progress prints + 1 success

    @patch('config.LogConfig.LOG_FILE')
    @patch('logging.getLogger')
    def test_setup_logging(self, mock_get_logger, mock_log_file):
        """Test logging setup"""
        # Mock the log file path
        mock_log_file.__str__ = lambda: str(self.test_base / "test.log")
        mock_log_file.parent.mkdir = MagicMock()

        # Mock logger and handlers
        mock_root_logger = MagicMock()
        mock_file_handler = MagicMock()
        mock_console_handler = MagicMock()
        mock_get_logger.return_value = mock_root_logger

        with patch('logging.handlers.RotatingFileHandler', return_value=mock_file_handler):
            with patch('logging.StreamHandler', return_value=mock_console_handler):
                setup_logging()

                # Check that handlers were added to root logger
                mock_root_logger.addHandler.assert_any_call(mock_file_handler)
                mock_root_logger.addHandler.assert_any_call(mock_console_handler)


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

        console = Console()

        # Custom test runner with progress bar
        class RichTestResult(unittest.TextTestResult):
            def __init__(self, stream, descriptions, verbosity):
                super().__init__(stream, descriptions, verbosity)
                self.console = Console()
                self.progress = None
                self.task = None
                self.test_count = 0
                self.passed = 0
                self.failed_count = 0
                self.errors_count = 0

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
                self.errors_count += 1
                if self.progress:
                    self.progress.update(self.task, advance=1)

            def addFailure(self, test, err):
                super().addFailure(test, err)
                self.failed_count += 1
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
                        result = super().run(test)

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
Passed: {result.testsRun - len(result.failures) - len(result.errors)}
Failed: {len(result.failures)}
Errors: {len(result.errors)}
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
        console.print("[dim]Testing config.py functionality[/dim]\n")

        # Preliminary Information
        console.print("[bold cyan]📋 Preliminary Information[/bold cyan]")
        
        # Import Status
        try:
            from config import APP_NAME, APP_VERSION, APP_AUTHOR, Environment
            console.print("  [green]✓[/green] Config module imports successful")
            console.print(f"  [dim]App: {APP_NAME} v{APP_VERSION} by {APP_AUTHOR}[/dim]")
        except ImportError as e:
            console.print(f"  [red]✗[/red] Config module import failed: {e}")
        
        # Environment Status
        try:
            import os
            env = os.environ.get('FOCUSBREAKER_ENV', 'production')
            console.print(f"  [green]✓[/green] Environment: {env}")
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Environment check failed: {e}")
        
        # Path Initialization
        try:
            from config import AppPaths
            paths = AppPaths()
            console.print("  [green]✓[/green] Application paths initialized")
            console.print(f"  [dim]Base dir: {AppPaths.BASE_DIR}[/dim]")
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Path initialization failed: {e}")
        
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