"""
Display System Module - Screen and Brightness Management
Handles screen brightness control, multi-monitor support, and display manipulation
"""

import ctypes
import json
import logging
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from config import UIConfig

logger = logging.getLogger(__name__)

try:
    import platform
    PLATFORM_SYSTEM = platform.system()

    if PLATFORM_SYSTEM == "Windows":
        try:
            import screen_brightness_control as sbc
            BRIGHTNESS_CONTROL_AVAILABLE = True

        except ImportError:
            BRIGHTNESS_CONTROL_AVAILABLE = False
            logger.warning("screen_brightness_control module not found. Brightness control will be disabled.")

    elif PLATFORM_SYSTEM == "Darwin":
        import subprocess
        BRIGHTNESS_CONTROL_AVAILABLE = True

    elif PLATFORM_SYSTEM == "Linux":
        import subprocess
        BRIGHTNESS_CONTROL_AVAILABLE = True

    else:
        BRIGHTNESS_CONTROL_AVAILABLE = False
        logger.warning(f"Brightness control not implemented for platform: {PLATFORM_SYSTEM}")

except ImportError as e:
    BRIGHTNESS_CONTROL_AVAILABLE = False
    logger.error(f"Failed to import platform module: {e}. \nBrightness control will be disabled.")

@dataclass
class DisplayInfo:
    """Information about a display/monitor"""
    index: int
    name: str
    width: int
    height: int
    is_primary: bool
    brightness: Optional[int] = None
    dpi: Optional[int] = None

class DisplayManager:
    """Manages display brightness and screen information"""
    def __init__(self):
        self.platform = PLATFORM_SYSTEM
        self.brightness_control_available = BRIGHTNESS_CONTROL_AVAILABLE

        self.original_brightness: Optional[int] = None
        self.current_brightness: Optional[int] = None
        self.brightness_animation_active = False
        self._animation_thread: Optional[threading.Thread] = None

        self.displays: List[DisplayInfo] = []
        self.primary_display: Optional[DisplayInfo] = None

        if self.brightness_control_available:
            self._refresh_display_info()
            self.original_brightness = self.get_brightness()
            self.current_brightness = self.original_brightness
            logger.info(f"DisplayManager initialised {self.platform},\
                        Brightness Control: {self.brightness_control_available}")
        else:
            logger.warning("Brightness control not available on this platform.")
    
    # ====================================== DISPLAY DETECTION =====================================
    def _refresh_display_info(self):
        """Refresh information about connected displays"""
        self.displays = []

        if self.platform == "Windows":
            if self.brightness_control_available:
                try:
                    monitors = sbc.list_monitors()

                    for i, monitor in enumerate(monitors):
                        info = DisplayInfo(index=i,
                                           name=monitor,
                                           width=0,
                                           height=0,
                                           is_primary=(i == 0),
                                           brightness=None)

                        self.displays.append(info)

                except Exception as e:
                    logger.error(f"Failed to retrieve display information: {e}")
            else:
                # Fallback when brightness control not available
                info = DisplayInfo(index=0,
                                   name="Primary Display",
                                   width=0,
                                   height=0,
                                   is_primary=True,
                                   brightness=None)
                self.displays.append(info)
        
        elif self.platform == "Darwin":
            try:
                result = subprocess.run(['system_profiler', 'SPDisplaysDataType', '-json'], capture_output = True, text = True)
    
                data = json.loads(result.stdout)
                displays_data = data.get('SPDisplaysDataType', [])

                for i, display in enumerate(displays_data):
                    name = display.get('sppci_model', f'Display {i}')
                    info = DisplayInfo(index = i,
                                       name = name,
                                       width = 0,
                                       height = 0,
                                       is_primary = (i == 0),
                                       brightness = None)
                    self.displays.append(info)

            except Exception as e:
                logger.error(f"Failed to retrieve display information: {e}")
        
        elif self.platform == "Linux":
            try:
                result = subprocess.run(['xrandr', '--listmonitors'], capture_output = True, text = True)
                lines = result.stdout.splitlines()[1:]

                for i, line in enumerate(lines):
                    parts = line.split()
                    name = parts[-1]
                    info = DisplayInfo(index = i,
                                       name = name,
                                       width = 0,
                                       height = 0,
                                       is_primary = ('primary' in parts),
                                       brightness = None)
                    self.displays.append(info)
            
            except Exception as e:
                logger.error(f"Failed to retrieve display information: {e}")

        else:
            logger.warning(f"Display detection not implemented for platform: {self.platform}")
        
        if self.displays:
            self.primary_display = self.displays[0]

    def get_displays(self) -> List[DisplayInfo]:
        """Get list of all connected displays"""
        if not self.displays:
            self._refresh_display_info()

        return self.displays

    def get_primary_display(self) -> Optional[DisplayInfo]:
        """Get the primary display information"""
        if self.primary_display is None:
            self._refresh_display_info()

        return self.primary_display
    
    def get_screen_resolution(self, display_index: int = 0) -> Tuple[int, int]:
        """Get screen resolution for specified display"""
    
        if self.platform == "Windows":
            try:
                user32 = ctypes.windll.user32
                width = user32.GetSystemMetrics(0)
                height = user32.GetSystemMetrics(1)
                return (width, height)
            
            except Exception as e:
                logger.error(f"Failed to get screen resolution: {e}")
                return (1920, 1080)  # Default fallback
            
        elif self.platform == "Darwin":
            try:
                result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], capture_output = True, text = True)
                
                data = json.loads(result.stdout)
                displays_data = data.get('SPDisplaysDataType', [])
                
                if display_index < len(displays_data):
                    display = displays_data[display_index]
                    resolution_str = display.get('spdisplays_resolution', '1920 x 1080')
                    width, height = map(int, resolution_str.split(' x '))
                    return (width, height)
                
                return (1920, 1080)  # Default fallback
            
            except Exception as e:
                logger.error(f"Failed to get screen resolution: {e}")
                return (1920, 1080) 
        
        elif self.platform == "Linux":
            try:
                result = subprocess.run(['xrandr'], capture_output = True, text = True)
                lines = result.stdout.splitlines()
                
                for line in lines:
                    if '*' in line:
                        parts = line.split()
                        resolution_str = parts[0]
                        width, height = map(int, resolution_str.split('x'))
                        return (width, height)
                
                return (1920, 1080)  
            
            except Exception as e:
                logger.error(f"Failed to get screen resolution: {e}")
                return (1920, 1080)  
        
        else:
            logger.warning(f"Screen resolution detection not implemented for platform: {self.platform}")
            return (1920, 1080)  

    # ====================================== BRIGHTNESS CONTROL =====================================
    def get_brightness(self, display: Optional[int] = None) -> int:
        """Get current screen brightness"""
        if not self.brightness_control_available:
            logger.warning("Brightness control not available.")
            return 100

        try:
            if self.platform == "Windows":
                if display is None:
                    brightness_value = sbc.get_brightness(display = 0)[0]
                
                else:
                    brightness_value = sbc.get_brightness(display = display)[0]
                
                return brightness_value
            
            elif self.platform == "Darwin":
                # Use osascript to get brightness
                result = subprocess.run([
                    'osascript', '-e',
                    'tell application "System Events" to tell appearance preferences to get brightness'
                ], capture_output=True, text=True)

                if result.returncode == 0:
                    brightness_float = float(result.stdout.strip())
                    brightness_value = int(brightness_float * 100)
                    return brightness_value

                return 100
            
            elif self.platform == "Linux":
                # Try multiple methods for Linux brightness control
                try:
                    # Method 1: xbacklight (if available)
                    result = subprocess.run(['xbacklight', '-get'], capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        brightness_value = int(float(result.stdout.strip()))
                        return brightness_value
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                    pass

                try:
                    # Method 2: sysfs backlight (common on laptops)
                    backlight_dirs = list(Path('/sys/class/backlight').glob('*'))
                    if backlight_dirs:
                        brightness_file = backlight_dirs[0] / 'brightness'
                        max_brightness_file = backlight_dirs[0] / 'max_brightness'

                        if brightness_file.exists() and max_brightness_file.exists():
                            current = int(brightness_file.read_text().strip())
                            max_val = int(max_brightness_file.read_text().strip())
                            brightness_value = int((current / max_val) * 100)
                            return brightness_value
                except (OSError, ValueError):
                    pass

                # Fallback
                return 100

            else:
                logger.warning(f"Brightness retrieval not implemented for platform: {self.platform}")
                return 100
        
        except Exception as e:
            logger.error(f"Failed to get brightness: {e}")
            return 100

    def set_brightness(self, brightness: int, display: Optional[int] = None, smooth: bool = False):
        """Set screen brightness"""
        brightness = max(0, min(100, brightness))

        if not self.brightness_control_available:
            logger.warning("Brightness control not available.")
            return
        
        if smooth:
            self.animate_brightness_change(target_brightness = brightness, 
                                           display = display, 
                                           duration_ms = 500)
            return
    
        try:
            if self.platform == "Windows":
                if display is None:
                    sbc.set_brightness(brightness)

                else:
                    sbc.set_brightness(brightness, display = display)

            elif self.platform == "Darwin":
                brightness_float = brightness / 100.0
                subprocess.run([
                    'osascript', '-e',
                    f'tell application "System Events" to tell appearance preferences to set brightness to {brightness_float}'
                ])

            elif self.platform == "Linux":
                brightness_float = brightness / 100.0

                # Try multiple methods for Linux brightness setting
                success = False

                try:
                    # Method 1: xrandr (software brightness control)
                    # First get the connected display name
                    result = subprocess.run(['xrandr'], capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        lines = result.stdout.splitlines()
                        for line in lines:
                            if ' connected ' in line and 'primary' in line:
                                display_name = line.split()[0]
                                subprocess.run(['xrandr', '--output', display_name, '--brightness', str(brightness_float)], timeout=2)
                                success = True
                                break
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                    pass

                if not success:
                    try:
                        # Method 2: sysfs backlight
                        backlight_dirs = list(Path('/sys/class/backlight').glob('*'))
                        if backlight_dirs:
                            brightness_file = backlight_dirs[0] / 'brightness'
                            max_brightness_file = backlight_dirs[0] / 'max_brightness'

                            if brightness_file.exists() and max_brightness_file.exists():
                                max_val = int(max_brightness_file.read_text().strip())
                                target_val = int((brightness / 100.0) * max_val)
                                brightness_file.write_text(str(target_val))
                                success = True
                    except (OSError, ValueError, PermissionError):
                        pass

                if not success:
                    logger.warning("Could not set brightness using available Linux methods")   

            else:
                logger.warning(f"Brightness setting not implemented for platform: {self.platform}")
                return
            
            self.current_brightness = brightness
            logger.info(f"Brightness set to {brightness}%") 

        except Exception as e:
            logger.error(f"Failed to set brightness: {e}")

    def boost_brightness(self, target_brightness: int = 100, smooth: bool = True):
        """Temporarily boost screen brightness"""            
        try:
            if not self.brightness_control_available:
                logger.warning("Brightness control not available.")
                return
            
            if self.original_brightness is None:
                self.original_brightness = self.get_brightness()
            
            self.set_brightness(target_brightness, smooth = smooth)

            logger.info(f"Brightness boosted from {self.original_brightness}% to {target_brightness}%")
        
        except Exception as e:
            logger.error(f"Failed to boost brightness: {e}")

    def restore_brightness(self, smooth: bool = True):
        """Restore brightness to original level"""
        try:
            if not self.brightness_control_available:
                logger.warning("Brightness control not available.")
                return
            
            if self.original_brightness is not None:
                self.set_brightness(self.original_brightness, smooth = smooth)
                logger.info(f"Brightness restored to {self.original_brightness}%")
                self.original_brightness = None

            else:
                logger.info("No original brightness to restore.")
        
        except Exception as e:
            logger.error(f"Failed to restore brightness: {e}")
        
    def animate_brightness_change(self, target_brightness: int, display: Optional[int] = None, duration_ms: int = UIConfig.ANIMATION_NORMAL):
        """Animate smooth brightness change to target level"""
        try:
            if not self.brightness_control_available:
                logger.warning("Brightness control not available.")
                return
            
            self.brightness_animation_active = False
            if self._animation_thread is not None:
                self._animation_thread.join(timeout = 1.0)
            
            def _animate():
                try:
                    self.brightness_animation_active = True

                    current_brightness = self.get_brightness(display = display)
                    target_brightness_clamped = max(0, min(100, target_brightness))

                    steps = 20
                    step_delay = duration_ms / steps / 1000.0
                    brightness_difference = target_brightness_clamped - current_brightness
                    step_size = brightness_difference / steps

                    for i in range(steps):
                        if not self.brightness_animation_active:
                            break
                        
                        intermediate_brightness = int(current_brightness + step_size * (i + 1))
                        self.set_brightness(intermediate_brightness, display = display, smooth = False)
                        time.sleep(step_delay)
                    
                    if self.brightness_animation_active:
                        self.set_brightness(target_brightness_clamped, display = display, smooth = False)
                    
                    self.brightness_animation_active = False
                    logger.info(f"Brightness animation completed to {target_brightness}%")
                except Exception as e:
                    logger.error(f"Error in brightness animation: {e}")
                    self.brightness_animation_active = False
            
            self._animation_thread = threading.Thread(target = _animate, daemon = True)
            self._animation_thread.start()
            logger.info(f"Started brightness animation to {target_brightness}% over {duration_ms}ms")
        
        except Exception as e:
            logger.error(f"Failed to start brightness animation: {e}")

    def cancel_brightness_animation(self):
        """Cancel any ongoing brightness animation"""
        try:
            self.brightness_animation_active = False
            
            if self._animation_thread is not None:
                self._animation_thread.join(timeout = 0.5)
                self._animation_thread = None
        
        except Exception as e:
            logger.error(f"Failed to cancel brightness animation: {e}")
    
    # ====================================== SCREEN EFFECTS =====================================
    def flash_screen(self, duration_ms: int = UIConfig.ANIMATION_FAST, brightness: int = 100):
        """Flash screen to maximum brightness for brief duration"""
        try:
            if not self.brightness_control_available:
                logger.warning("Brightness control not available.")
                return
            
            original_brightness = self.get_brightness()

            # Flash
            self.set_brightness(brightness, smooth = True)
            
            def restore_after_delay():
                try:
                    time.sleep(duration_ms / 1000.0)
                    self.set_brightness(original_brightness, smooth = True)
                
                except Exception as e:
                    logger.error(f"Error in flash restore delay: {e}")
            
            thread = threading.Thread(target = restore_after_delay, daemon = True)
            thread.start()

            logger.info(f"Screen flashed to {brightness}% brightness for {duration_ms}ms")
        
        except Exception as e:
            logger.error(f"Failed to flash screen: {e}")
    
    def pulse_brightness(self, min_brightness: int = 50, max_brightness: int = 100, pulse_duration_ms: int = UIConfig.ANIMATION_NORMAL, pulse_count: int = 2):
        """Pulse brightness up and down"""
        try:
            if not self.brightness_control_available:
                logger.warning("Brightness control not available.")
                return
            
            original_brightness = self.get_brightness()
            half_pulse_duration = pulse_duration_ms // 2

            def pulse():
                try:
                    for i in range(pulse_count):
                        # Pulse up
                        self.animate_brightness_change(max_brightness, duration_ms = half_pulse_duration)
                        time.sleep(half_pulse_duration / 1000.0)
                        
                        # Pulse down
                        self.animate_brightness_change(min_brightness, duration_ms = half_pulse_duration)
                        time.sleep(half_pulse_duration / 1000.0)
                    
                    self.animate_brightness_change(original_brightness, duration_ms = half_pulse_duration)
                except Exception as e:
                    logger.error(f"Error in brightness pulsing: {e}")
            
            thread = threading.Thread(target = pulse, daemon = True)
            thread.start()
        
            logger.info(f"Started brightness pulsing between {min_brightness}% and {max_brightness}% for {pulse_count} cycles")
        
        except Exception as e:
            logger.error(f"Failed to start brightness pulsing: {e}")
    
    # ====================================== STATE QUERIES =====================================
    def is_brightness_boosted(self) -> bool:
        """Check if brightness is currently boosted"""
        try:
            return self.original_brightness is not None
        
        except Exception as e:
            logger.error(f"Failed to check brightness boost status: {e}")
            return False
    
    def is_animating(self) -> bool:
        """Check is brightness animation is active"""
        try:
            return self.brightness_animation_active
        
        except Exception as e:
            logger.error(f"Failed to check animation status: {e}")
            return False

    def get_display_status(self) -> Dict[str, Any]:
        """Get current display status information"""
        try:
            status = {
                'platform': self.platform,
                'brightness_control_available': self.brightness_control_available,
                'original_brightness': self.original_brightness,
                'current_brightness': self.current_brightness,
                'is_brightness_boosted': self.is_brightness_boosted(),
                'is_animating': self.is_animating(),
                'display_count': len(self.displays),
                'primary_display': self.primary_display
            }
            return status
        
        except Exception as e:
            logger.error(f"Failed to get display status: {e}")
            return {
                'platform': self.platform,
                'brightness_control_available': False,
                'error': str(e)
            }

    # ====================================== CLEANUP =====================================
    def cleanup(self):
        """Cleanup resources on shutdown"""
        self.cancel_brightness_animation()
        self.restore_brightness(smooth = False)

        logger.info("DisplayManager cleaned up and resources released.")

# ====================================== HELPER FUNCTIONS =====================================
def detect_display_features() -> Dict[str, bool]:
    """Detect what display features are available on current system"""
    features = {
        'brightness_control': BRIGHTNESS_CONTROL_AVAILABLE,
        'multi_monitor_support': False,
        'dpi_scaling': False,
        'color_management': False
    }

    try:
        if PLATFORM_SYSTEM == "Windows":
            features['multi_monitor_support'] = ctypes.windll.user32.GetSystemMetrics(80) > 1
            features['dpi_scaling'] = True
        
        elif PLATFORM_SYSTEM == "Darwin":
            features['multi_monitor_support'] = True
            features['dpi_scaling'] = True
        
        elif PLATFORM_SYSTEM == "Linux":
            result = subprocess.run(['xrandr'], capture_output = True, text = True)
            connected_count = result.stdout.count(' connected ')
            features['multi_monitor_support'] = connected_count > 1
        
        else:
            logger.warning(f"Display feature detection not implemented for platform: {PLATFORM_SYSTEM}")
        
    except Exception as e:
        logger.error(f"Error detecting display features: {e}")
    
    return features