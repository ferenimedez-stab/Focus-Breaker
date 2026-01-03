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
    unittest.main()