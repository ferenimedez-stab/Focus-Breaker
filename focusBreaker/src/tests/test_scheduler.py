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
    unittest.main()