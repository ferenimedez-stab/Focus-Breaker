"""
Escape Hatch Module - Emergency Exit System
Provides emergency escape from Strict/Focused mode breaks
"""

import keyboard
import time
import logging
import threading
from typing import Callable, Optional, Dict, Any
from data.db import DBManager
from data.models import Settings

logger = logging.getLogger(__name__)

class EscapeHatchDetector:
    """
    Detects emergency escape key combination
    Monitors for key hold, triggers callback when confirmed
    """

    def __init__(self, 
                 settings: Optional[Settings] = None,
                 key_combo: Optional[str] = None,
                 hold_duration_seconds: Optional[float] = None,
                 on_escape: Optional[Callable] = None,
                 on_progress: Optional[Callable[[float], None]] = None,
                 debounce_ms: Optional[int] = None):
        
        """Initialize escape hatch detector with validation"""
        # Validate provided parameters first
        if key_combo is not None and (not isinstance(key_combo, str) or not key_combo.strip()):
            raise ValueError("key_combo must be a non-empty string")
        
        if hold_duration_seconds is not None and (not isinstance(hold_duration_seconds, (int, float)) or hold_duration_seconds <= 0):
            raise ValueError("hold_duration_seconds must be a positive number")
        
        if debounce_ms is not None and debounce_ms < 0:
            raise ValueError("debounce_ms must be non-negative")
        
        # Determine final values: settings take precedence if enabled, otherwise use parameters
        if settings and hasattr(settings, 'escape_hatch_enabled') and settings.escape_hatch_enabled:
            final_key_combo = settings.escape_hatch_key_combo
            final_hold_duration = float(settings.escape_hatch_hold_duration_seconds)
            final_debounce_ms = settings.escape_hatch_debounce_ms
        else:
            # Use provided parameters or defaults
            final_key_combo = key_combo if key_combo is not None else "ctrl+alt+shift+e"
            final_hold_duration = hold_duration_seconds if hold_duration_seconds is not None else 3.0
            final_debounce_ms = debounce_ms if debounce_ms is not None else 100
        
        # Validate final values
        if not isinstance(final_key_combo, str) or not final_key_combo.strip():
            raise ValueError("key_combo must be a non-empty string")
        
        if not isinstance(final_hold_duration, (int, float)) or final_hold_duration <= 0:
            raise ValueError("hold_duration_seconds must be a positive number")
        
        if final_debounce_ms < 0:
            raise ValueError("debounce_ms must be non-negative")
        
        self.keys = [key.strip().lower() for key in final_key_combo.split('+')]
        if not self.keys:
            raise ValueError("key_combo must contain at least one key")
        
        valid_modifiers = {'ctrl', 'alt', 'shift', 'win', 'cmd'}
        for key in self.keys[:-1]: 
            if key not in valid_modifiers and len(key) > 1:
                logger.warning(f"Potentially invalid modifier key: {key}")
        
        self.key_combo = final_key_combo.lower()
        self.hold_duration_seconds = float(final_hold_duration)
        self.on_escape = on_escape
        self.on_progress = on_progress
        self.debounce_ms = final_debounce_ms / 1000.0  # Convert to seconds
        
        # State management
        self.is_active = False
        self.hold_start_time = None
        self.is_holding = False
        self.last_release_time = 0
        self.last_progress_time = 0
        self.progress_interval = 0.1  
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Error tracking
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        
        logger.info(f"EscapeHatchDetector initialized with combo: {self.key_combo}, duration: {self.hold_duration_seconds}s")

    def start(self):
        """Start listening for escape key presses"""
        with self._lock:
            if self.is_active:
                logger.warning("EscapeHatchDetector is already active")
                return
            
            self.is_active = True
            self.reset_state()
            logger.info("EscapeHatchDetector started")
    
    def stop(self):
        """Stop listening for escape key presses"""
        with self._lock:
            if not self.is_active:
                return
            
            self.is_active = False
            self.reset_state()
            
            try:
                keyboard.unhook_all()
           
            except Exception as e:
                logger.error(f"Error during keyboard cleanup: {e}")
            
            logger.info("EscapeHatchDetector stopped")
    
    def check_keys_held(self) -> bool:
        """Check if key combination is currently being held with error handling"""
        try:
            for key in self.keys:
                if not keyboard.is_pressed(key):
                    return False
            return True
       
        except Exception as e:
            self.consecutive_errors += 1
           
            if self.consecutive_errors <= self.max_consecutive_errors:
                logger.warning(f"Error checking key press: {e}")
            
            elif self.consecutive_errors == self.max_consecutive_errors + 1:
                logger.error(f"Too many consecutive errors ({self.max_consecutive_errors}), suppressing further error logs")
            
            return False

    def reset_state(self):
        """Reset hold state"""
        self.hold_start_time = None
        self.is_holding = False
        self.last_progress_time = 0
    
    def update(self):
        """Update detector state with thread safety and error handling"""
        with self._lock:
            if not self.is_active:
                return
            
            current_time = time.time()
            
            # Check for debouncing after release
            if not self.is_holding and current_time - self.last_release_time < self.debounce_ms:
                return
            
            keys_held = self.check_keys_held()
            
            if keys_held:
                if not self.is_holding:
                    if current_time - self.last_release_time >= self.debounce_ms:
                        self.hold_start_time = current_time
                        self.is_holding = True
                        logger.debug("Key combination hold started")
                
                elif self.hold_start_time is not None:
                    elapsed_time = current_time - self.hold_start_time
                    progress = min(elapsed_time / self.hold_duration_seconds, 1.0)
       
                    if self.on_progress and current_time - self.last_progress_time >= self.progress_interval:
                        try:
                            self.on_progress(progress)
                            self.last_progress_time = current_time
                        
                        except Exception as e:
                            logger.error(f"Error in progress callback: {e}")
                    
                    if elapsed_time >= self.hold_duration_seconds:
                        logger.info("Escape sequence completed - triggering escape")
                        if self.on_escape:
                            try:
                                self.on_escape()
                           
                            except Exception as e:
                                logger.error(f"Error in escape callback: {e}")
                        
                        self.reset_state()
                        self.last_release_time = current_time
            
            else:
                if self.is_holding:
                    logger.debug("Key combination released before completion")
                    self.last_release_time = current_time
                    self.reset_state()
    
    def is_healthy(self) -> bool:
        """Check if the detector is functioning properly"""
        return self.consecutive_errors < self.max_consecutive_errors
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the detector"""
        with self._lock:
            return {
                'active': self.is_active,
                'holding': self.is_holding,
                'progress': self._get_current_progress(),
                'healthy': self.is_healthy(),
                'consecutive_errors': self.consecutive_errors,
                'key_combo': self.key_combo
            }
    
    def _get_current_progress(self) -> float:
        """Get current hold progress (0.0 to 1.0)"""
        if not self.is_holding or self.hold_start_time is None:
            return 0.0
        
        elapsed = time.time() - self.hold_start_time
        return min(elapsed / self.hold_duration_seconds, 1.0)
    
    def force_escape(self):
        """Force trigger escape (for testing or emergency)"""
        with self._lock:
            if self.is_active and self.on_escape:
                logger.info("Force escape triggered")
                try:
                    self.on_escape()
                
                except Exception as e:
                    logger.error(f"Error in force escape callback: {e}")
                self.reset_state()

# ============================ ESCAPE HATCH HANDLER ============================

def handle_emergency_exit(session_id: int, mode: str, reason: str, db: DBManager):
    """
    Handle emergency exit - log it and update session
    """
    try:
        session = db.getSession(session_id)
        if not session:
            logger.error(f"Session {session_id} not found for emergency exit")
            return

        new_exit_count = session.emergency_exits + 1

        db.updateSession(session_id, emergency_exits=new_exit_count)
        
        db.logEvent(
            event_type = 'emergency_exit_used',
            event_category = 'session',
            session_id = session_id,
            details = {
                'mode': mode,
                'reason': reason,
                'previous_count': session.emergency_exits,
                'new_count': new_exit_count
            },
            severity = 'warning',
            user_message = f'Emergency exit used in {mode} mode: {reason}'
        )

        logger.info(f"Emergency exit handled for session {session_id}, count now {new_exit_count}")

    except Exception as e:
        logger.error(f"Error handling emergency exit for session {session_id}: {e}")

        try:
            db.logSystemEvent(
                event_type = 'emergency_exit_error',
                details = {'session_id': session_id, 'mode': mode, 'error': str(e)},
                severity = 'error',
                user_message = 'Failed to properly handle emergency exit'
            )
     
        except:
            pass  


def is_escape_hatch_available(mode: str, is_break_time: bool) -> bool:
    """
    Check if escape hatch is currently available
    """
    try:
        if mode == 'normal':
            return False  

        if mode in ['strict', 'focused']:
            return is_break_time  

        logger.warning(f"Unknown mode '{mode}' for escape hatch availability check")
        return False
  
    except Exception as e:
        logger.error(f"Error checking escape hatch availability: {e}")
        return False


def get_escape_consequences(mode: str) -> dict:
    """
    Get what happens when escape hatch is used
    """
    try:
        if mode == 'normal':
            return {
                'available': False,
                'breaks_perfect_streak': False,
                'logs_in_history': False,
                'reduces_quality_score': False,
                'affects_analytics': False,
                'message': "Emergency exit not available in Normal mode"
            }
        else:
            return {
                'available': True,
                'breaks_perfect_streak': True,
                'logs_in_history': True,
                'reduces_quality_score': True,
                'affects_analytics': True,
                'message': "Emergency exit will break your perfect streak and affect analytics"
            }
   
    except Exception as e:
        logger.error(f"Error getting escape consequences: {e}")
        return {
            'available': False,
            'breaks_perfect_streak': False,
            'logs_in_history': False,
            'reduces_quality_score': False,
            'affects_analytics': False,
            'message': "Error determining escape consequences"
        }

# ============================ CONFIGURATION ============================

def get_default_key_combo() -> str:
    """
    Get default key combination for escape hatch
    """
    try:
        return "ctrl+alt+shift+e"
    
    except Exception as e:
        logger.error(f"Error getting default key combo: {e}")
        return "ctrl+alt+shift+e"  # Return safe default


def get_default_hold_duration() -> int:
    """
    Get default hold duration in seconds
    """
    try:
        return 3
    
    except Exception as e:
        logger.error(f"Error getting default hold duration: {e}")
        return 3  # Return safe default


def validate_key_combo(key_combo: str) -> bool:
    """
    Validate that key combination is valid
    """
    try:
        if not key_combo or not isinstance(key_combo, str):
            return False

        keys = [key.strip().lower() for key in key_combo.split('+')]

        if len(keys) < 2:
            return False
        
        valid_modifiers = {'ctrl', 'alt', 'shift', 'win', 'cmd'}

        has_modifier = False
        has_action_key = False

        for key in keys:
            if key in valid_modifiers:
                has_modifier = True
            else:
                if (len(key) == 1 and key.isalnum()) or key.startswith('f') and key[1:].isdigit():
                    has_action_key = True
                else:
                    return False

        return has_modifier and has_action_key
    
    except Exception as e:
        logger.error(f"Error validating key combo '{key_combo}': {e}")
        return False