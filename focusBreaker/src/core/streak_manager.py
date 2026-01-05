"""
Streak Manager Module - Streak Calculation and Management
Handles all streak logic: session streaks, perfect streaks, daily consistency
"""

from datetime import datetime
from typing import Dict, Any, Optional
from data.db import DBManager
from config import StreakConfig, TimerConfig

import logging
logger = logging.getLogger(__name__)

# ================================== MAIN STREAK UPDATES ==================================
def update_session_streak(session_valid: bool, db: DBManager):
    try:
        streak = db.getStreak('session_streak')

        if not streak:
            return
        
        if session_valid:
            new_count = streak.current_count + 1
            new_best = max(streak.best_count, new_count)
        
        else:
            new_count = 0
            new_best = streak.best_count  
        
        db.updateStreak('session_streak', new_count, new_best)
   
    except Exception as e:
        logger.error(f"Error updating session streak: {e}")

def update_perfect_session_streak(session_perfect: bool, db: DBManager):
    try:
        streak = db.getStreak('perfect_session')

        if not streak:
            return
        
        if session_perfect:
            new_count = streak.current_count + 1
            new_best = max(streak.best_count, new_count)
       
        else:
            new_count = 0
            new_best = streak.best_count
        
        db.updateStreak('perfect_session', new_count, new_best)
    
    except Exception as e:
        logger.error(f"Error updating perfect session streak: {e}")

def update_daily_consistency(session_date: str, db: DBManager):
    try:
        streak = db.getStreak('daily_consistency')
        if not streak:
            return
        
        last_date = datetime.fromisoformat(streak.last_updated).date() if streak.last_updated else None
        current_date = datetime.strptime(session_date, "%Y-%m-%d").date()
        
        if last_date is None:
            days_difference = 1
        else:
            days_difference = (current_date - last_date).days
        
        if days_difference == 0:
            return
        
        elif days_difference == 1:
            new_count = streak.current_count + 1
            new_best = max(streak.best_count, new_count)
        
        else:
            new_count = 1 
            new_best = streak.best_count
        
        db.updateStreak('daily_consistency', new_count, new_best)
    
    except Exception as e:
        logger.error(f"Error updating daily consistency streak: {e}")

def update_streaks_after_session(session_id: int, db: DBManager):
    try:
        session = db.getSession(session_id)
        if not session:
            return
        
        session_valid = (session.breaks_skipped == 0)
        session_perfect = (session.breaks_skipped == 0 and session.breaks_snoozed == 0 and session.emergency_exits == 0)

        update_session_streak(session_valid, db)
        update_perfect_session_streak(session_perfect, db)
        update_daily_consistency(session.created_at, db)
   
    except Exception as e:
        logger.error(f"Error updating streaks after session: {e}")

# ============================== STREAK QUALITY CALCULATIONS ============================== 
def get_streak_status(streak_type: str, db: DBManager) -> Dict[str, Any]:
    try:
        streak = db.getStreak(streak_type)
        if streak is None:
            return {}
        
        is_active = (streak.current_count > 0)

        if streak_type == 'session_streak':
            text = f"🔥 {streak.current_count} session streak"
        
        elif streak_type == 'perfect_session':
            text = f"⭐ {streak.current_count} perfect sessions"
        elif streak_type == 'daily_consistency':
            text = f"📅 {streak.current_count} days consistent"
        else:
            text = "Streak not found."
        
        return {
            'type': streak_type,
            'current': streak.current_count,
            'best': streak.best_count,
            'is_active': is_active,
            'last_updated': streak.last_updated,
            'display_text': text
        }
    
    except Exception as e:
        logger.error(f"Error getting streak status for type '{streak_type}': {e}")
        return {}

def get_all_streaks_summary(db: DBManager) -> Dict[str, Dict[str, Any]]:
    try:
        summary = {}

        streak_types = StreakConfig.STREAK_TYPES

        for streak_type in streak_types:
            summary[streak_type] = get_streak_status(streak_type, db)

        return summary
   
    except Exception as e:
        logger.error(f"Error getting all streaks summary: {e}")
        return {}

# =================================== STREAK PREDICTIONS ==================================
def predict_streak_risk(streak_type: str, db: DBManager) -> Dict[str, Any]:
    try:
        if streak_type != 'daily_consistency':
            return {'at_risk': False}
        
        streak = db.getStreak(streak_type)
        if streak is None or streak.current_count == 0:
            return {'at_risk': False}  
        
        last_updated = datetime.fromisoformat(streak.last_updated) if streak.last_updated else datetime.now()
        now = datetime.now()
        hours_since = (now - last_updated).total_seconds() / TimerConfig.SECONDS_PER_HOUR
        
        if hours_since > StreakConfig.DAILY_RISK_HIGH_HOURS:
            risk = 'high'
            hours_until = StreakConfig.HOURS_IN_DAY - hours_since
            message = f"Work in {int(hours_until)}h or lose {streak.current_count}-day streak!"
        elif hours_since > StreakConfig.DAILY_RISK_MEDIUM_HOURS:
            risk = 'medium'
            hours_until = StreakConfig.HOURS_IN_DAY - hours_since
            message = f"{int(hours_until)}h left to maintain streak"
        else:
            risk = 'low'
            hours_until = StreakConfig.HOURS_IN_DAY - hours_since
            message = "Streak is safe for today"
        
        return {
            'at_risk': risk != 'low',
            'risk_level': risk,
            'hours_until_lost': hours_until,
            'message': message
        }
   
    except Exception as e:
        logger.error(f"Error predicting streak risk for type '{streak_type}': {e}")
        return {'at_risk': False}

# =================================== MILESTONE CHECKING ==================================
def check_streak_milestone(streak_type: str, db: DBManager) -> Optional[Dict[str, Any]]:
    try:
        milestones = StreakConfig.STREAK_MILESTONES

        streak = db.getStreak(streak_type)
        if streak is None:
            return None
        
        current_count = streak.current_count if streak else 0
        
        if current_count not in milestones:
            return None
        
        # Determine celebration level based on milestone
        if current_count == 5:
            level = 'small'
            emoji = '🎉'
        elif current_count == 10:
            level = 'medium'
            emoji = '🔥'
        elif current_count == 25:
            level = 'large'
            emoji = '🏆'
        elif current_count == 50:
            level = 'huge'
            emoji = '🚀'
        elif current_count == 100:
            level = 'legendary'
            emoji = '👑'
        elif current_count == 250:
            level = 'epic'
            emoji = '🌟'
        elif current_count == 500:
            level = 'mythic'
            emoji = '💎'
        elif current_count == 1000:
            level = 'ultimate'
            emoji = '👑'
        else:
            level = 'custom'
            emoji = '🎊'
        
        message = f"{emoji} {current_count}-day streak! Amazing!"

        return {
            'milestone' : current_count,
            'message' : message,
            'emoji' : emoji,
            'celebration_level' : level
        }
   
    except Exception as e:
        logger.error(f"Error checking streak milestone for type '{streak_type}': {e}")
        return None

def can_recover_streak(streak_type: str, db: DBManager) -> bool:
    try:
        if streak_type != 'daily_consistency':
            return False
        
        streak = db.getStreak(streak_type)
        if streak is None:
            return False
        
        current_count = streak.current_count
        if current_count > 0:
            return False
        
        last_updated = datetime.fromisoformat(streak.last_updated) if streak.last_updated else datetime.now()
        now = datetime.now()
        hours_since = (now - last_updated).total_seconds() / TimerConfig.SECONDS_PER_HOUR

        return (hours_since < StreakConfig.HOURS_IN_DAY)
   
    except Exception as e:
        logger.error(f"Error checking if streak can be recovered for type '{streak_type}': {e}")
        return False

def get_streak_statistics(db: DBManager) -> Dict[str, Any]:
    try:
        streaks = db.getAllStreaks()
        
        active_count = sum(1 for streak in streaks if streak.current_count > 0)
        
        longest = max(streak.best_count for streak in streaks) if streaks else 0
        
        stats = db.getSessionStats(days = StreakConfig.STATISTICS_PERIOD_DAYS)
        
        total_sessions = stats.get('total_sessions', 0)
        completed_sessions = stats.get('completed_sessions', 0)
        
        if total_sessions > 0:
            session_completion_rate = completed_sessions / total_sessions
        else:
            session_completion_rate = 0.0
        
        total_breaks_taken = stats.get('total_breaks_taken', 0)
        total_breaks_snoozed = stats.get('total_breaks_snoozed', 0)
        total_breaks_skipped = stats.get('total_breaks_skipped', 0)
        total_emergency_exits = stats.get('total_emergency_exits', 0)
        
        # Calculate weighted quality score using config weights
        weights = StreakConfig.QUALITY_SCORE_WEIGHTS
        total_weighted_score = (
            total_breaks_taken * weights['breaks_taken'] +
            total_breaks_snoozed * weights['breaks_snoozed'] +
            total_breaks_skipped * weights['breaks_skipped'] +
            total_emergency_exits * weights['emergency_exits']
        )
        
        total_actions = total_breaks_taken + total_breaks_snoozed + total_breaks_skipped + total_emergency_exits
        
        if total_actions > 0:
            average_quality_score = max(0.0, min(1.0, total_weighted_score / total_actions))
        else:
            average_quality_score = 1.0  
        
        perfect_sessions_count = stats.get('perfect_sessions', 0)
        
        streak_details = {}
        for streak in streaks:
            streak_details[streak.streak_type] = {
                'current': streak.current_count,
                'best': streak.best_count,
                'last_updated': streak.last_updated
            }
        
        return {
            'total_sessions_completed': completed_sessions,
            'perfect_sessions_count': perfect_sessions_count,
            'session_completion_rate': round(session_completion_rate, 2),
            'average_quality_score': round(average_quality_score, 2),
            'longest_ever_streak': longest,
            'current_active_streaks': active_count,
            'streak_details': streak_details,
            'total_breaks_taken': total_breaks_taken,
            'total_breaks_snoozed': total_breaks_snoozed,
            'total_breaks_skipped': total_breaks_skipped,
            'total_emergency_exits': stats.get('total_emergency_exits', 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting streak statistics: {e}")
        
        return {
            'total_sessions_completed': 0,
            'perfect_sessions_count': 0,
            'session_completion_rate': 0.0,
            'average_quality_score': 0.0,
            'longest_ever_streak': 0,
            'current_active_streaks': 0,
            'streak_details': {},
            'total_breaks_taken': 0,
            'total_breaks_snoozed': 0,
            'total_breaks_skipped': 0,
            'total_emergency_exits': 0
        }