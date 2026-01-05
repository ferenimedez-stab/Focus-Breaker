"""
Scheduler Module - Break Scheduling Algorithm
Calculates when breaks should occur based on work mode and duration
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from data.db import DBManager
from data.models import Settings
from config import ModeConfig, EnergyConfig

logger = logging.getLogger(__name__)    

def calculate_break_schedule(mode: str, work_duration_minutes: int, settings: Settings) -> List[int]:
    """Calculate when breaks should occur during a work session"""
    try:
        break_times = []
        
        if mode == 'focused':
            return []
        
        if work_duration_minutes < ModeConfig.MIN_WORK_DURATION_MINUTES:
            return []
        
        work_interval = get_work_interval_for_mode(mode, settings)
        if work_duration_minutes < work_interval:
            return []
            
        num_breaks = work_duration_minutes // work_interval

        for i in range(1, num_breaks + 1):
            break_time = i * work_interval
            if break_time < work_duration_minutes:
                break_times.append(break_time)
        
        return break_times
    
    except Exception as e:
        logger.error(f"Error calculating break schedule for mode '{mode}': {e}")
        return []

def calculate_elapsed_minutes(start_time: str) -> int:
    """
    Calculate elapsed minutes from a start time string
    """
    try:
        start = datetime.fromisoformat(start_time)
        now = datetime.now()
        elapsed_seconds = (now - start).total_seconds()
        return int(elapsed_seconds / 60)
    
    except Exception as e:
        logger.error(f"Error calculating elapsed minutes from '{start_time}': {e}")
        return 0

def redistribute_breaks_after_snooze(session_id: int, db: DBManager) -> List[int]:
    """
    Recalculate break schedule after user snoozes a break
    Makes remaining breaks more frequent
    """
    try:
        session = db.getSession(session_id)
        if not session:
            return []
        
        elapsed_minutes = calculate_elapsed_minutes(session.start_time)
        remaining_time = session.planned_duration_minutes - elapsed_minutes
        
        if remaining_time <= 0:
            return []
        
        pending_breaks = db.getPendingBreaks(session_id)
        if not pending_breaks:
            return []
        elif len(pending_breaks) == 1:
            return [elapsed_minutes + (remaining_time // 2)]

        interval = remaining_time / (len(pending_breaks) + 1)

        new_break_times = []
        for i in range(len(pending_breaks)):
            break_time = elapsed_minutes + ((i + 1) * interval)
            new_break_times.append(int(break_time))

        return new_break_times
    
    except Exception as e:
        logger.error(f"Error redistributing breaks after snooze for session {session_id}: {e}")
        return []

def reschedule_break(break_id: int, snooze_duration_minutes: int, session_id: int, db: DBManager) -> datetime:
    """Reschedule a single break after snooze"""
    try:
        break_obj = db.getBreak(break_id)
        if not break_obj:
            raise ValueError("Break not found")

        old_time = datetime.fromisoformat(break_obj.scheduled_time)
        new_time = old_time + timedelta(minutes = snooze_duration_minutes)

        db.updateBreak(break_id, scheduled_time = new_time.isoformat())
        
        redistribute_breaks_after_snooze(session_id, db)

        return new_time
    
    except Exception as e:
        logger.error(f"Error rescheduling break {break_id}: {e}")
        raise  

def get_work_interval_for_mode(mode: str, settings: Settings) -> int:
    """Get work interval (minutes before break) for a given mode"""
    try:
        work_interval = {
            'normal' : settings.normal_work_interval_minutes if settings.normal_work_interval_minutes else ModeConfig.NORMAL_WORK_INTERVAL_MINUTES,
            'strict' : settings.strict_work_interval_minutes if settings.strict_work_interval_minutes else ModeConfig.STRICT_WORK_INTERVAL_MINUTES,
            'focused' : 0
        }

        return work_interval.get(mode, ModeConfig.NORMAL_WORK_INTERVAL_MINUTES)
    
    except Exception as e:
        logger.error(f"Error getting work interval for mode '{mode}': {e}")
        return ModeConfig.NORMAL_WORK_INTERVAL_MINUTES

def get_break_duration_for_mode(mode: str, settings: Settings) -> int:
    """Get break duration (minutes before break) for a given mode"""
    try:
        break_duration = {
            'normal' : settings.normal_break_duration_minutes if settings.normal_break_duration_minutes else ModeConfig.NORMAL_BREAK_DURATION_MINUTES,
            'strict' : settings.strict_break_duration_minutes if settings.strict_break_duration_minutes else ModeConfig.STRICT_BREAK_DURATION_MINUTES,
            'focused' : settings.focused_mandatory_break_minutes if settings.focused_mandatory_break_minutes else ModeConfig.FOCUSED_MANDATORY_BREAK_MINUTES
        }

        return break_duration.get(mode, ModeConfig.FOCUSED_MANDATORY_BREAK_MINUTES)
    
    except Exception as e:
        logger.error(f"Error getting break duration for mode '{mode}': {e}")
        return ModeConfig.FOCUSED_MANDATORY_BREAK_MINUTES

def get_next_break_time(current_time_minutes: int, break_times: List[int]) -> Optional[int]:
    """Find next upcoming break from schedule"""
    try:
        for break_time in break_times:
            if break_time > current_time_minutes:
                return break_time
        
        return None
    
    except Exception as e:
        logger.error(f"Error getting next break time from schedule: {e}")
        return None

def validate_break_schedule(break_times: List[int], work_duration_minutes: int) -> bool:
    """Validate that a break schedule is sensible"""
    try:
        if not break_times:
            return True
        
        if break_times[0] <= 0 or break_times[-1] >= work_duration_minutes:
            return False
        
        if break_times != sorted(break_times):
            return False
        
        if len(break_times) != len(set(break_times)):
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"Error validating break schedule: {e}")
        return False

def optimize_break_schedule_for_energy(work_duration_minutes: int, user_energy_pattern: str = "normal") -> List[int]:
    """Optimise break schedule based on user's energy pattern"""
    try:
        if user_energy_pattern == 'morning_person':
            base_schedule = EnergyConfig.MORNING_PERSON_BREAKS

        elif user_energy_pattern == "afternoon_slump":
            base_schedule = EnergyConfig.AFTERNOON_SLUMP_BREAKS

        elif user_energy_pattern == "night_owl":
            base_schedule = EnergyConfig.NIGHT_OWL_BREAKS

        else:
            base_schedule = EnergyConfig.NORMAL_BREAKS
        
        # Filter breaks that occur before the end
        optimized = [b for b in base_schedule if b < work_duration_minutes]
        return optimized
    
    except Exception as e:
        logger.error(f"Error optimizing break schedule for energy pattern '{user_energy_pattern}': {e}")
        return []