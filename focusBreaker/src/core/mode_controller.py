"""
Mode Controller Module - Mode-Specific Behavior Rules
Defines what each mode (Normal, Strict, Focused) allows or restricts
"""

import logging
from typing import Dict, Any, Optional
from data.db import DBManager
from data.models import Settings

logger = logging.getLogger(__name__)

# ========================= MODE PERMISSION CHECKS =========================
def can_snooze_break(mode: str, session_id: Optional[int], db: Optional[DBManager]) -> bool:
    """Check if user can snooze a break, given mode"""
    try:
        if not session_id or not db:
            return False
        
        session = db.getSession(session_id)

        if not session:
            return False
        
        if mode == 'normal':
            snooze_pass = db.getSnoozePassesRemaining(session_id)
            return snooze_pass < 0
        
        else:
            return False
    except Exception as e:
        logger.error(f"Error checking snooze permission for mode '{mode}': {e}")
        return False
    
def can_skip_break(mode: str, settings: Settings) -> bool:
    """Check is user can skip a break, given mode"""
    try:
        if mode == 'normal':
            return settings.allow_skip_in_normal_mode
        
        else:
            return False
    except Exception as e:
        logger.error(f"Error checking skip permission for mode '{mode}': {e}")
        return False

def can_extend_session(mode: str) -> bool:
    """Check if user can extend session, given mode"""
    try:
        if mode == 'normal':
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Error checking extend permission for mode '{mode}': {e}")
        return False
    
def get_break_windows_type(mode: str) -> str:
    """Get type of window to show during break, given mode"""
    try:
        if mode == 'normal':
            return 'small_movable'
        
        else:
            return 'full_screen'
    except Exception as e:
        logger.error(f"Error getting break window type for mode '{mode}': {e}")
        return 'small_movable'  # Safe default

def requires_cooldown(mode: str) -> bool:
    """Check if mode requires mandatory cooldown after session"""
    try:
        if mode == 'strict' or mode == 'focused':
            return True
        
        else: 
            return False
    except Exception as e:
        logger.error(f"Error checking cooldown requirement for mode '{mode}': {e}")
        return False
    

def get_cooldown_duration(mode: str, settings: Settings) -> int:
    """Get mandatory cooldown/rest duration, given mode"""
    try:
        if mode == 'normal':
            return 0
        
        elif mode == 'strict':
            return settings.strict_cooldown_minutes
        
        elif mode == 'focused':
            return settings.focused_mandatory_break_minutes 
        
        else:
            return 0
    except Exception as e:
        logger.error(f"Error getting cooldown duration for mode '{mode}': {e}")
        return 0

# ========================= MODE BEHAVIOR QUERIES =========================
def has_breaks_during_work(mode: str) -> bool:
    """Check if user has breaks during work session, given mode"""
    try:
        if mode == 'normal' or mode == 'strict':
            return True
        
        elif mode == 'focused':
            return False
        
        else:
            print("Mode not found.")
            return False
    except Exception as e:
        logger.error(f"Error checking breaks during work for mode '{mode}': {e}")
        return False
    
def get_mode_display_name(mode: str) -> str:
    """Get human-readable name for mode"""
    try:
        display_name = {
            'normal' : 'Normal mode',
            'strict' : 'Strict mode',
            'focused' : 'Focused mode'
        }
        
        return display_name.get(mode, 'Unknown Mode')
    except Exception as e:
        logger.error(f"Error getting display name for mode '{mode}': {e}")
        return 'Unknown Mode'
    
def get_mode_description(mode: str) -> str:
    """Get description of what mode does"""
    try:
        description = {
            'normal' : 'Flexible breaks - Can snooze/skip, Can extend session',
            'strict' : 'Enforced breaks - No snooze/skip, Mandatory cooldown after breaks',
            'focused' : 'No interruptions - Pure focus, Mandatory break at the end of session' 
        }

        return description.get(mode, 'Unknown mode')
    except Exception as e:
        logger.error(f"Error getting description for mode '{mode}': {e}")
        return 'Unknown mode'

# ============================ MODE VALIDATION ============================
def is_valid_mode(mode: str) -> bool:
    """Check if mode string is valid"""
    try:
        valid_modes = ['normal', 'strict', 'focused']

        return mode in valid_modes
    except Exception as e:
        logger.error(f"Error validating mode '{mode}': {e}")
        return False

def get_available_modes() -> list:
    """Get list of all available modes"""
    try:
        available_modes = ['normal', 'strict', 'focused']

        return available_modes
    except Exception as e:
        logger.error(f"Error getting available modes: {e}")
        return []

# =========================== MODE RULES SUMMARY ===========================
def get_mode_rules(mode: str, settings: Settings) -> Dict[str, Any]:
    """Get complete rule set for a mode as dictionary"""
    try:
        rules = {
            'can_snooze' : can_snooze_break(mode, session_id = None, db = None),
            'can_skip' : can_skip_break(mode, settings),
            'can_extend_session' : can_extend_session(mode),
            'break_window_type' : get_break_windows_type(mode),
            'requires_cooldown' : requires_cooldown(mode),
            'cooldown_duration_minutes' : get_cooldown_duration(mode, settings),
            'has_breaks_during_work' : has_breaks_during_work(mode),
            'display_name' : get_mode_display_name(mode),
            'description' : get_mode_description(mode)
        }

        return rules
    except Exception as e:
        logger.error(f"Error getting mode rules for mode '{mode}': {e}")
        return {}

# ============================= EMERGENCY EXIT ==============================
def is_emergency_exit_available(mode: str) -> bool:
    """Check is emergency escape hatch is available, given mode"""
    try:
        if mode == 'strict' or mode == 'focused':
            return True
        
        else:
            return False
    except Exception as e:
        logger.error(f"Error checking emergency exit availability for mode '{mode}': {e}")
        return False

def get_emergency_exit_consequence(mode: str) -> str:
    """Get description of what happens when emergency exit used"""
    try:
        exit_consequences = {
            'normal' : 'Emergency exit not available in Normal mode',
            'strict' : '''Using emergency exit will:
                                    - Break your perfect session streak
                                    - Log the exit in your history
                                    - Reduce session quality score''',
            'focused' : '''Using emergency exit will:
                                    - Break your perfect session streak
                                    - Log the exit in your history
                                    - Reduce session quality score'''
        }

        return exit_consequences.get(mode, 'Unknown Mode')
    except Exception as e:
        logger.error(f"Error getting emergency exit consequence for mode '{mode}': {e}")
        return 'Unknown Mode'