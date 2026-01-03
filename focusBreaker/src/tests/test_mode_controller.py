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
    unittest.main()