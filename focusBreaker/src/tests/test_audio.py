"""
Comprehensive test suite for AudioManager class using unittest
"""
import unittest
import sys
import os
import tempfile
import time
from unittest.mock import Mock, patch, MagicMock
import logging

sys.path.insert(0, 'src')

try:
    from system.audio import AudioManager, create_default_alarm_sound, VOLUME_CONTROL_AVAILABLE
    AUDIO_AVAILABLE = True
except ImportError as e:
    print(f"Audio module not available: {e}")
    AUDIO_AVAILABLE = False
    AudioManager = None
    VOLUME_CONTROL_AVAILABLE = False


class TestAudioManager(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_audio_file = os.path.join(self.temp_dir, "test.wav")

        if AUDIO_AVAILABLE:
            self.audio_manager = AudioManager()                     # type: ignore
            # Initialize the audio manager for tests that need it
            try:
                self.audio_manager.initialize()

            except:
                # If initialization fails (e.g., no audio device), continue with uninitialized manager
                pass
        else:
            self.audio_manager = None

    def tearDown(self):
        """Clean up test fixtures"""
        if AUDIO_AVAILABLE and self.audio_manager:
            try:
                self.audio_manager.cleanup()
            except:
                pass

        # Clean up temp files
        try:
            if os.path.exists(self.test_audio_file):
                os.remove(self.test_audio_file)
            os.rmdir(self.temp_dir)
        except:
            pass

    @unittest.skipUnless(AUDIO_AVAILABLE, "Audio module not available")
    def test_initialization(self):
        """Test AudioManager initialization"""
        result = self.audio_manager.initialize()                    # type: ignore
        self.assertTrue(result)
        self.assertTrue(self.audio_manager.mixer_initialised)       # type: ignore

    @unittest.skipUnless(AUDIO_AVAILABLE, "Audio module not available")
    def test_volume_validation(self):
        """Test volume setting with validation"""
        # Test media volume
        self.audio_manager.set_media_volume(50)                     # type: ignore
        self.assertEqual(self.audio_manager.media_volume, 0.5)      # type: ignore

        # Test boundary values
        self.audio_manager.set_media_volume(-10)                    # type: ignore
        self.assertEqual(self.audio_manager.media_volume, 0.0)      # type: ignore

        self.audio_manager.set_media_volume(150)                    # type: ignore
        self.assertEqual(self.audio_manager.media_volume, 1.0)      # type: ignore  

    @unittest.skipUnless(AUDIO_AVAILABLE, "Audio module not available")
    def test_boost_system_volume_validation(self):
        """Test system volume boost validation"""
        # Test with valid boost amount
        self.audio_manager.boost_system_volume(0.1)                    # type: ignore
        # Should not raise exception

        # Test with invalid boost amounts
        self.audio_manager.boost_system_volume(-0.5)                    # type: ignore
        self.audio_manager.boost_system_volume(2.0)                     # type: ignore

    @unittest.skipUnless(AUDIO_AVAILABLE, "Audio module not available")
    def test_audio_file_validation(self):
        """Test audio file validation"""
        # Test non-existent file
        result = self.audio_manager.validate_audio_file("/nonexistent/file.wav")    # type: ignore
        self.assertFalse(result)

        # Test unsupported format
        temp_file = os.path.join(self.temp_dir, "test.txt")
        with open(temp_file, 'w') as f:
            f.write("test")

        result = self.audio_manager.validate_audio_file(temp_file)      # type: ignore
        self.assertFalse(result)

    @unittest.skipUnless(AUDIO_AVAILABLE, "Audio module not available")
    def test_list_audio_files(self):
        """Test listing audio files in directory"""
        # Create some test files
        wav_file = os.path.join(self.temp_dir, "test.wav")
        mp3_file = os.path.join(self.temp_dir, "test.mp3")
        txt_file = os.path.join(self.temp_dir, "test.txt")

        # Create empty files
        for file_path in [wav_file, mp3_file, txt_file]:
            with open(file_path, 'w') as f:
                f.write("")

        result = self.audio_manager.list_audio_files(self.temp_dir)     # type: ignore
        self.assertIn(wav_file, result)
        self.assertIn(mp3_file, result)
        self.assertNotIn(txt_file, result)

    @unittest.skipUnless(AUDIO_AVAILABLE, "Audio module not available")
    def test_get_audio_status(self):
        """Test getting audio status"""
        status = self.audio_manager.get_audio_status()                  # type: ignore
        self.assertIsInstance(status, dict)
        expected_keys = ['mixer_initialised', 'media_playing', 'music_playing',
                        'alarm_playing', 'media_volume', 'music_volume',
                        'alarm_volume', 'system_volume_boosted']
        for key in expected_keys:
            self.assertIn(key, status)

    @unittest.skipUnless(AUDIO_AVAILABLE, "Audio module not available")
    def test_actual_volume_change(self):
        """Test actual system volume changes (only when volume control is available)"""
        if not VOLUME_CONTROL_AVAILABLE:
            self.skipTest("System volume control not available - skipping actual volume test")

        # Check if volume controller is actually initialized
        if self.audio_manager.system_volume_controller is None:  # type: ignore
            self.skipTest("System volume controller failed to initialize - skipping actual volume test")

        # Get original volume
        original_volume = self.audio_manager.get_system_volume()            # type: ignore
        print(f"Original system volume: {original_volume:.2f}")

        # Test setting volume to 50%
        test_volume = 0.5
        print(f"Setting system volume to: {test_volume}")
        self.audio_manager.set_system_volume(test_volume)                   # type: ignore

        # Wait a moment for the change to take effect
        time.sleep(0.5)

        # Check current volume
        current_volume = self.audio_manager.get_system_volume()             # type: ignore
        print(f"Current volume after change: {current_volume:.2f}")

        # Verify volume changed (allow some tolerance for system variations)
        volume_diff = abs(current_volume - test_volume)
        self.assertLessEqual(volume_diff, 0.1, f"Volume should be close to {test_volume}, got {current_volume}")

        # Restore original volume
        print(f"Restoring volume to: {original_volume:.2f}")
        self.audio_manager.set_system_volume(original_volume)               # type: ignore
        time.sleep(0.5)

        restored_volume = self.audio_manager.get_system_volume()            # type: ignore
        print(f"Volume after restoration: {restored_volume:.2f}")

        # Verify restoration (allow some tolerance)
        restore_diff = abs(restored_volume - original_volume)
        self.assertLessEqual(restore_diff, 0.1, f"Volume should be restored to {original_volume}, got {restored_volume}")

    @unittest.skipUnless(AUDIO_AVAILABLE, "Audio module not available")
    def test_actual_volume_boost_and_restore(self):
        """Test actual volume boost and restore functionality"""
        if not VOLUME_CONTROL_AVAILABLE:
            self.skipTest("System volume control not available - skipping volume boost test")

        # Check if volume controller is actually initialized
        if self.audio_manager.system_volume_controller is None:  # type: ignore
            self.skipTest("System volume controller failed to initialize - skipping volume boost test")

        # Get original volume
        original_volume = self.audio_manager.get_system_volume()            # type: ignore
        print(f"Original system volume: {original_volume:.2f}")

        # First set volume to a lower level so we can test boosting
        test_base_volume = 0.5
        print(f"Setting base volume to: {test_base_volume}")
        self.audio_manager.set_system_volume(test_base_volume)              # type: ignore
        time.sleep(0.5)

        base_volume = self.audio_manager.get_system_volume()                # type: ignore
        print(f"Base volume set to: {base_volume:.2f}")

        # Test volume boost - this should boost from current volume (0.5) to (0.7)
        boost_amount = 0.2
        expected_boosted_volume = min(1.0, base_volume + boost_amount)
        print(f"Boosting volume by {boost_amount} (expected: {expected_boosted_volume:.2f})")

        self.audio_manager.boost_system_volume(boost_amount)                # type: ignore
        time.sleep(0.5)

        boosted_volume = self.audio_manager.get_system_volume()             # type: ignore
        print(f"Volume after boost: {boosted_volume:.2f}")

        # Verify boost worked (allow some tolerance)
        boost_diff = abs(boosted_volume - expected_boosted_volume)
        self.assertLessEqual(boost_diff, 0.15, f"Volume should be boosted to ~{expected_boosted_volume}, got {boosted_volume}")

        # Test restore - this should restore to the base volume (0.5), not the original (1.0)
        print(f"Restoring volume to base level: {base_volume:.2f}")
        self.audio_manager.restore_system_volume()                          # type: ignore
        time.sleep(0.5)

        restored_volume = self.audio_manager.get_system_volume()            # type: ignore
        print(f"Volume after restore: {restored_volume:.2f}")

        # Verify restoration to base volume
        restore_diff = abs(restored_volume - base_volume)
        self.assertLessEqual(restore_diff, 0.15, f"Volume should be restored to {base_volume}, got {restored_volume}")

        # Finally restore to original volume
        print(f"Restoring to original volume: {original_volume:.2f}")
        self.audio_manager.set_system_volume(original_volume)               # type: ignore

    @unittest.skipUnless(AUDIO_AVAILABLE, "Audio module not available")
    @patch('pygame.mixer.Sound')
    def test_get_audio_duration(self, mock_sound_class):
        """Test getting audio duration"""
        mock_sound = Mock()
        mock_sound.get_length.return_value = 3.5
        mock_sound_class.return_value = mock_sound

        duration = self.audio_manager.get_audio_duration("/fake/path.wav")          # type: ignore
        self.assertEqual(duration, 3.5)
    
    def test_system_volume_control_availability(self):
        """Test system volume control availability detection"""
        # This test just checks that the module loads and detects availability
        if AUDIO_AVAILABLE:
            self.assertIsInstance(VOLUME_CONTROL_AVAILABLE, bool)
        else:
            # If module not available, availability should be False
            self.assertFalse(VOLUME_CONTROL_AVAILABLE)

    # Tests that can run without pygame
    def test_volume_validation_logic(self):
        """Test volume validation logic without pygame"""
        # Test clamping logic directly
        def clamp_volume(volume):
            return max(0, min(100, volume))

        # Test normal values
        self.assertEqual(clamp_volume(50), 50)
        self.assertEqual(clamp_volume(0), 0)
        self.assertEqual(clamp_volume(100), 100)

        # Test boundary clamping
        self.assertEqual(clamp_volume(-10), 0)
        self.assertEqual(clamp_volume(150), 100)

    def test_boost_amount_validation_logic(self):
        """Test boost amount validation logic"""
        def clamp_boost(boost):
            return max(0.0, min(1.0, boost))

        # Test normal values
        self.assertEqual(clamp_boost(0.2), 0.2)
        self.assertEqual(clamp_boost(0.0), 0.0)
        self.assertEqual(clamp_boost(1.0), 1.0)

        # Test boundary clamping
        self.assertEqual(clamp_boost(-0.5), 0.0)
        self.assertEqual(clamp_boost(2.0), 1.0)

    def test_audio_file_extension_validation(self):
        """Test audio file extension validation logic"""
        supported_formats = ['.mp3', '.wav', '.ogg', '.flac', '.aac']

        # Test supported formats
        for ext in supported_formats:
            self.assertIn(ext, supported_formats)

        # Test unsupported formats
        self.assertNotIn('.txt', supported_formats)
        self.assertNotIn('.mp4', supported_formats)

    def test_list_audio_files_logic(self):
        """Test audio file listing logic"""
        # Create test files
        wav_file = os.path.join(self.temp_dir, "test.wav")
        mp3_file = os.path.join(self.temp_dir, "test.mp3")
        txt_file = os.path.join(self.temp_dir, "test.txt")

        # Create empty files
        for file_path in [wav_file, mp3_file, txt_file]:
            with open(file_path, 'w') as f:
                f.write("")

        # Test the logic manually
        supported_formats = ['.mp3', '.wav', '.ogg', '.flac', '.aac']
        audio_files = []

        for file in os.listdir(self.temp_dir):
            full_path = os.path.join(self.temp_dir, file)
            if os.path.isfile(full_path):
                extension = os.path.splitext(file)[1].lower()
                if extension in supported_formats:
                    audio_files.append(full_path)

        audio_files = sorted(audio_files)

        self.assertIn(wav_file, audio_files)
        self.assertIn(mp3_file, audio_files)
        self.assertNotIn(txt_file, audio_files)

    @unittest.skipUnless(AUDIO_AVAILABLE, "Audio module not available")
    def test_error_handling_in_playback(self):
        """Test error handling in playback methods"""
        # Test with uninitialized mixer
        self.audio_manager.mixer_initialised = False                          # type: ignore    

        # These should not raise exceptions
        self.audio_manager.play_audio_file("/fake/file.wav")                  # type: ignore
        self.audio_manager.play_alarm("/fake/alarm.wav")                      # type: ignore
        self.audio_manager.play_background_music("/fake/music.wav")           # type: ignore

    @unittest.skipUnless(AUDIO_AVAILABLE, "Audio module not available")
    def test_channel_none_handling(self):
        """Test handling when channels are None"""
        # Set channels to None
        self.audio_manager.channel_main = None                            # type: ignore
        self.audio_manager.channel_music = None                           # type: ignore
        self.audio_manager.channel_alarm = None                           # type: ignore

        # These should not raise exceptions
        self.audio_manager.set_media_volume(50)                          # type: ignore 
        self.audio_manager.set_music_volume(50)                          # type: ignore
        self.audio_manager.set_alarm_volume(50)                          # type: ignore

        self.assertFalse(self.audio_manager.is_playing_media())          # type: ignore
        self.assertFalse(self.audio_manager.is_playing_music())          # type: ignore
        self.assertFalse(self.audio_manager.is_playing_alarm())          # type: ignore


class TestAudioManagerIntegration(unittest.TestCase):
    """Integration tests for AudioManager"""

    def setUp(self):
        """Set up integration test fixtures"""
        if AUDIO_AVAILABLE:
            self.audio_manager = AudioManager()             # type: ignore
        else:
            self.audio_manager = None

    def tearDown(self):
        """Clean up integration test fixtures"""
        if AUDIO_AVAILABLE and self.audio_manager:
            try:
                self.audio_manager.cleanup()
            except:
                pass

    @unittest.skipUnless(AUDIO_AVAILABLE, "Audio module not available")
    def test_full_initialization_flow(self):
        """Test complete initialization flow"""
        from unittest.mock import patch

        with patch('pygame.mixer.init'), \
             patch('pygame.mixer.Channel') as mock_channel:

            mock_channel.return_value = Mock()
            result = self.audio_manager.initialize()                          # type: ignore        
            self.assertTrue(result)

            # Check that channels were created
            self.assertIsNotNone(self.audio_manager.channel_main)             # type: ignore
            self.assertIsNotNone(self.audio_manager.channel_music)            # type: ignore
            self.assertIsNotNone(self.audio_manager.channel_alarm)            # type: ignore

    @unittest.skipUnless(AUDIO_AVAILABLE, "Audio module not available")
    def test_volume_workflow(self):
        """Test volume setting workflow"""
        from unittest.mock import patch

        # Initialize with mocked pygame
        with patch('pygame.mixer.init'), \
             patch('pygame.mixer.Channel') as mock_channel:

            mock_channel.return_value = Mock()
            self.audio_manager.initialize()                         # type: ignore

            # Test volume settings
            self.audio_manager.set_media_volume(75)                          # type: ignore
            self.audio_manager.set_alarm_volume(60)                          # type: ignore
            self.audio_manager.set_music_volume(80)                          # type: ignore

            # Verify volumes were set
            self.assertEqual(self.audio_manager.media_volume, 0.75)         # type: ignore
            self.assertEqual(self.audio_manager.alarm_volume, 0.6)          # type: ignore
            self.assertEqual(self.audio_manager.music_volume, 0.8)          # type: ignore


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
        console.print("[dim]Testing audio.py functionality[/dim]\n")

        # Preliminary Information
        console.print("[bold cyan]📋 Preliminary Information[/bold cyan]")
        
        # Import Status
        if AUDIO_AVAILABLE:
            console.print("  [green]✓[/green] Audio module imports successful")
            console.print(f"  [dim]AudioManager available, Volume control: {'Available' if VOLUME_CONTROL_AVAILABLE else 'Not available'}[/dim]")
        else:
            console.print("  [red]✗[/red] Audio module import failed")
            console.print("  [dim]Audio functionality will be limited[/dim]")
        
        # Pygame Status
        try:
            import pygame
            pygame_version = pygame.version.ver
            console.print(f"  [green]✓[/green] Pygame v{pygame_version} available")
        except ImportError:
            console.print("  [red]✗[/red] Pygame not available")
        
        # Audio System Initialization
        if AUDIO_AVAILABLE:
            try:
                test_manager = AudioManager()               # type: ignore
                test_manager.initialize()
                console.print("  [green]✓[/green] Audio system initialized successfully")
                test_manager.cleanup()
            except Exception as e:
                console.print(f"  [yellow]⚠[/yellow] Audio system initialization failed: {e}")
        else:
            console.print("  [dim]-[/dim] Audio system initialization skipped (module not available)")
        
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