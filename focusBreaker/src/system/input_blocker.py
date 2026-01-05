"""
Input Blocker Module - Keyboard and Mouse Input Control
Blocks keyboard and mouse input during Strict/Focused mode breaks
"""

import logging
import threading
import time
from typing import Optional, Callable, Set
from enum import Enum
from config import EscapeHatchConfig

logger = logging.getLogger(__name__)

"""Try to import platform-specific input blocking libraries"""
try:
    import platform
    PLATFORM_SYSTEM = platform.system()
    
    if PLATFORM_SYSTEM == 'Windows':
        try:
            import keyboard
            import mouse
            INPUT_BLOCKING_AVAILABLE = True
            logger.info(f"Windows input blocking available (keyboard/mouse libraries)")

        except ImportError as e:
            INPUT_BLOCKING_AVAILABLE = False
            logger.warning(f"Keyboard/mouse libraries not available: {e}. Input blocking disabled.")

    elif PLATFORM_SYSTEM == 'Darwin':
        try:
            from Quartz import (                                    # type: ignore
                CGEventTapCreate, CGEventTapEnable, 
                kCGSessionEventTap, kCGHeadInsertEventTap,
                kCGEventTapOptionDefault, CGEventMaskBit,
                kCGEventKeyDown, kCGEventKeyUp,
                kCGEventLeftMouseDown, kCGEventLeftMouseUp,
                kCGEventRightMouseDown, kCGEventRightMouseUp
            )
            INPUT_BLOCKING_AVAILABLE = True
            logger.info(f"macOS input blocking available (Quartz library)")
        
        except ImportError as e:
            INPUT_BLOCKING_AVAILABLE = False
            logger.warning(f"Quartz library not available: {e}. Input blocking disabled.")
    
    elif PLATFORM_SYSTEM == 'Linux':
        try:
            import evdev                                            # type: ignore
            INPUT_BLOCKING_AVAILABLE = True
            logger.info(f"Linux input blocking available (evdev library)")
        
        except ImportError as e:
            INPUT_BLOCKING_AVAILABLE = False
            logger.warning(f"evdev library not available: {e}. Input blocking disabled.")
        
    else:
        INPUT_BLOCKING_AVAILABLE = False
        logger.warning(f"Unsupported platform '{PLATFORM_SYSTEM}'. Input blocking disabled.")
    
except Exception as e:
    INPUT_BLOCKING_AVAILABLE = False
    logger.error(f"Failed to initialize input blocker: {e}")

class BlockingMode(Enum):
    """Input blocking modes"""
    NONE = "none"
    KEYBOARD_ONLY = "keyboard"
    MOUSE_ONLY = "mouse"
    FULL = "full"

class InputBlocker:
    """Manages keyboard and mouse input blocking during breaks"""
    def __init__(self, escape_key_combo: Optional[Set[str]] = None, max_block_duration: int = 3600):
        self.platform = PLATFORM_SYSTEM
        self.blocking_available = INPUT_BLOCKING_AVAILABLE

        if escape_key_combo is None:
            # Parse the default key combo from config
            combo_str = EscapeHatchConfig.DEFAULT_KEY_COMBO
            self.escape_key_combo = set(combo_str.replace('+', ' ').split())
        
        else:
            self.escape_key_combo = escape_key_combo
        
        # Safety timeout to auto-unblock input
        self.max_block_duration = max_block_duration
        
        # Blocking state
        self.is_blocking = False
        self.blocking_mode = BlockingMode.NONE
        self.blocked_keys: Set[str] = set()
        self.escape_key_pressed: Set[str] = set()

        # Hooks (platform-specific)
        self.keyboard_hook = None
        self.mouse_hook = None
        self.event_tap = None               # for macOS
        
        # Linux-specific
        self.linux_keyboard_devices = []    # evdev devices
        self.linux_event_thread = None      # consumer thread

        # Timeout mechanism
        self.block_start_time: Optional[float] = None
        self.timeout_thread: Optional[threading.Thread] = None
        self.timout_active = False

        #Callbacks
        self.on_escape_detected: Optional[Callable] = None
        self.on_block_timeout: Optional[Callable] = None

        logger.info(f"InputBlocker initialized (Platform: {self.platform}, "
                    f"Available: {self.blocking_available})")
        
    # ====================================== BLOCKING CONTROL =====================================
    def start_blocking(self, mode: BlockingMode = BlockingMode.FULL):
        """Start blocking input based on specified mode"""
        if self.is_blocking:
            logger.warning("Input blocking already active.")
            return
        
        if not self.blocking_available:
            logger.warning("Input blocking not available on this platform.")
            return
        
        self.blocking_mode = mode
        self.is_blocking = True
        self.block_start_time = time.time()

        logger.info(f"Starting input blocking (Mode: {self.blocking_mode})")

        try:
            if mode in (BlockingMode.KEYBOARD_ONLY, BlockingMode.FULL):
                self._start_keyboard_blocking()
            
            if mode in (BlockingMode.MOUSE_ONLY, BlockingMode.FULL):
                self._start_mouse_blocking()
            
            self._start_timeout_monitor()
            logger.info(f"Input blocking started (mode: {self.blocking_mode})")
            
        except Exception as e:
            logger.error(f"Failed to start input blocking: {e}")
            self.stop_blocking()
    
    def stop_blocking(self):
        """Stop blocking input"""
        if not self.is_blocking:
            logger.warning("Input blocking is not active.")
            return
        
        try:
            # Stop hooks
            self._stop_keyboard_blocking()
            self._stop_mouse_blocking()

            # Stop timeout monitor
            self._stop_timeout_monitor()

            # Reset state
            self.is_blocking = False
            self.blocking_mode = BlockingMode.NONE
            self.blocked_keys.clear()
            self.escape_key_pressed.clear()
            self.block_start_time = None

            logger.info("Input blocking stopped.")

        except Exception as e:
            logger.error(f"Error stopping input blocking: {e}")
    
    # ====================================== KEYBOARD BLOCKING =====================================
    def _start_keyboard_blocking(self):
        """Start keyboard input blocking"""
        try:
            if self.platform == "Windows":
                # Hook all keyboard events
                self.keyboard_hook = keyboard.hook(self._keyboard_callback_windows)
                logger.info("Windows keyboard blocking started")
            
            elif self.platform == "Darwin":
                # Create event tap for keyboard
                event_mask = (
                    CGEventMaskBit(kCGEventKeyDown) | 
                    CGEventMaskBit(kCGEventKeyUp)
                )
                
                self.event_tap = CGEventTapCreate(
                    kCGSessionEventTap,
                    kCGHeadInsertEventTap,
                    kCGEventTapOptionDefault,
                    event_mask,
                    self._keyboard_callback_macos,
                    None
                )
                
                if self.event_tap:
                    CGEventTapEnable(self.event_tap, True)
                    logger.info("macOS keyboard blocking started")
                else:
                    logger.error("Failed to create macOS event tap")
            
            elif self.platform == "Linux":
                import evdev                                                    # type: ignore  
                from evdev import InputDevice, list_devices                     # type: ignore
                
                # Find keyboard devices
                self.linux_keyboard_devices = []
                devices = [InputDevice(path) for path in list_devices()]
                
                for device in devices:
                    if device.capabilities().get(1):  
                        key_events = device.capabilities().get(1, [])
                        if 30 in key_events or 31 in key_events:  # KEY_A or KEY_S
                            try:
                                device.grab()  
                                self.linux_keyboard_devices.append(device)
                                logger.info(f"Grabbed Linux keyboard device: {device.name}")
                            
                            except Exception as e:
                                logger.warning(f"Could not grab device {device.name}: {e}")
                
                if self.linux_keyboard_devices:
                    # Start background thread to consume events
                    self.linux_event_thread = threading.Thread(
                        target=self._linux_keyboard_consumer, 
                        daemon=True
                    )
                    self.linux_event_thread.start()
                    logger.info(f"Linux keyboard blocking started ({len(self.linux_keyboard_devices)} devices)")
                else:
                    logger.warning("No Linux keyboard devices could be grabbed")
                
        except Exception as e:
            logger.error(f"Error starting keyboard blocking: {e}")
    
    def _stop_keyboard_blocking(self):
        """Stop keyboard input blocking"""
        try:
            if self.platform == "Windows":
                if self.keyboard_hook:
                    keyboard.unhook_all()
                    self.keyboard_hook = None
                    logger.info("Windows keyboard blocking stopped")
            
            elif self.platform == "Darwin":
                if self.event_tap:
                    CGEventTapEnable(self.event_tap, False)
                    self.event_tap = None
                    logger.info("macOS keyboard blocking stopped")
            
            elif self.platform == "Linux":
                for device in getattr(self, 'linux_keyboard_devices', []):
                    try:
                        device.ungrab()
                        device.close()
                        logger.info(f"Released Linux keyboard device: {device.name}")
                    except Exception as e:
                        logger.error(f"Error releasing device {device.name}: {e}")
                
                self.linux_keyboard_devices.clear()
                
                if hasattr(self, 'linux_event_thread') and self.linux_event_thread:
                    self.linux_event_thread = None  
                
                logger.info("Linux keyboard blocking stopped")
                
        except Exception as e:
            logger.error(f"Error stopping keyboard blocking: {e}")
    
    def _keyboard_callback_windows(self, event):
        """Windows keyboard event callback"""
        try:
            key_name = event.name.lower()
            
            if event.event_type == 'down':
                self.escape_key_pressed.add(key_name)
            elif event.event_type == 'up':
                self.escape_key_pressed.discard(key_name)
            
            if self.escape_key_pressed >= self.escape_key_combo:
                if self.on_escape_detected:
                    self.on_escape_detected()
                return True  
            
            if key_name in self.escape_key_combo:
                return True 
            
            logger.debug(f"Blocked key: {key_name}")
            return False  
            
        except Exception as e:
            logger.error(f"Error in Windows keyboard callback: {e}")
            return True  
    
    def _keyboard_callback_macos(self, proxy, event_type, event, refcon):
        """macOS keyboard event callback"""
        try:
            from Quartz import CGEventGetIntegerValueField, kCGKeyboardEventKeycode                 # type: ignore
            
            key_code = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            
            key_name = self._keycode_to_name(key_code)
            
            if key_name in self.escape_key_combo:
                return event  
            
            logger.debug(f"Blocked macOS key: {key_name}")
            return None  
            
        except Exception as e:
            logger.error(f"Error in macOS keyboard callback: {e}")
            return event  
    
    def _keycode_to_name(self, keycode):
        """Convert macOS keycode to key name"""
        keycode_map = {
            0: 'a', 1: 's', 2: 'd', 3: 'f', 4: 'h', 5: 'g', 6: 'z', 7: 'x',
            8: 'c', 9: 'v', 11: 'b', 12: 'q', 13: 'w', 14: 'e', 15: 'r',
            16: 'y', 17: 't', 18: '1', 19: '2', 20: '3', 21: '4', 22: '5',
            23: '6', 24: '7', 25: '8', 26: '9', 27: '0', 28: 'return',
            29: 'escape', 30: 'backspace', 31: 'tab', 32: 'space',
            33: 'minus', 34: 'equal', 35: 'left_bracket', 36: 'right_bracket',
            37: 'backslash', 38: 'non_us_pound', 39: 'semicolon', 40: 'quote',
            41: 'grave_accent', 42: 'comma', 43: 'period', 44: 'slash',
            45: 'caps_lock', 46: 'f1', 47: 'f2', 48: 'f3', 49: 'f4', 50: 'f5',
            51: 'f6', 52: 'f7', 53: 'f8', 54: 'f9', 55: 'f10', 56: 'f11',
            57: 'f12', 58: 'print_screen', 59: 'scroll_lock', 60: 'pause',
            61: 'insert', 62: 'home', 63: 'page_up', 64: 'delete', 65: 'end',
            66: 'page_down', 67: 'right_arrow', 68: 'left_arrow', 69: 'down_arrow',
            70: 'up_arrow', 71: 'num_lock', 72: 'kp_divide', 73: 'kp_multiply',
            74: 'kp_minus', 75: 'kp_plus', 76: 'kp_enter', 77: 'kp_1', 78: 'kp_2',
            79: 'kp_3', 80: 'kp_4', 81: 'kp_5', 82: 'kp_6', 83: 'kp_7', 84: 'kp_8',
            85: 'kp_9', 86: 'kp_0', 87: 'kp_period', 88: 'non_us_backslash',
            89: 'application', 90: 'power', 91: 'kp_equal', 92: 'f13', 93: 'f14',
            94: 'f15', 95: 'f16', 96: 'f17', 97: 'f18', 98: 'f19', 99: 'f20',
            100: 'f21', 101: 'f22', 102: 'f23', 103: 'f24', 104: 'execute',
            105: 'help', 106: 'menu', 107: 'select', 108: 'stop', 109: 'again',
            110: 'undo', 111: 'cut', 112: 'copy', 113: 'paste', 114: 'find',
            115: 'mute', 116: 'volume_up', 117: 'volume_down', 118: 'locking_caps_lock',
            119: 'locking_num_lock', 120: 'locking_scroll_lock', 121: 'kp_comma',
            122: 'kp_equal_sign', 123: 'international1', 124: 'international2',
            125: 'international3', 126: 'international4', 127: 'international5',
            128: 'international6', 129: 'international7', 130: 'international8',
            131: 'international9', 132: 'lang1', 133: 'lang2', 134: 'lang3',
            135: 'lang4', 136: 'lang5', 137: 'lang6', 138: 'lang7', 139: 'lang8',
            140: 'lang9', 141: 'alt_erase', 142: 'sys_req', 143: 'cancel',
            144: 'clear', 145: 'prior', 146: 'return2', 147: 'separator',
            148: 'out', 149: 'oper', 150: 'clear_again', 151: 'cr_sel',
            152: 'ex_sel', 153: 'kp_00', 154: 'kp_000', 155: 'thousands_separator',
            156: 'decimal_separator', 157: 'currency_unit', 158: 'currency_sub_unit',
            159: 'kp_left_paren', 160: 'kp_right_paren', 161: 'kp_left_brace',
            162: 'kp_right_brace', 163: 'kp_tab', 164: 'kp_backspace', 165: 'kp_a',
            166: 'kp_b', 167: 'kp_c', 168: 'kp_d', 169: 'kp_e', 170: 'kp_f',
            171: 'kp_xor', 172: 'kp_power', 173: 'kp_percent', 174: 'kp_less',
            175: 'kp_greater', 176: 'kp_ampersand', 177: 'kp_double_ampersand',
            178: 'kp_vertical_bar', 179: 'kp_double_vertical_bar', 180: 'kp_colon',
            181: 'kp_hash', 182: 'kp_space', 183: 'kp_at', 184: 'kp_exclamation',
            185: 'kp_mem_store', 186: 'kp_mem_recall', 187: 'kp_mem_clear',
            188: 'kp_mem_add', 189: 'kp_mem_subtract', 190: 'kp_mem_multiply',
            191: 'kp_mem_divide', 192: 'kp_plus_minus', 193: 'kp_clear',
            194: 'kp_clear_entry', 195: 'kp_binary', 196: 'kp_octal', 197: 'kp_decimal',
            198: 'kp_hexadecimal', 199: 'left_control', 200: 'left_shift', 201: 'left_alt',
            202: 'left_gui', 203: 'right_control', 204: 'right_shift', 205: 'right_alt',
            206: 'right_gui'
        }
        
        return keycode_map.get(keycode, f'key_{keycode}')
    
    def _linux_keyboard_consumer(self):
        """Background thread to consume Linux keyboard events"""
        try:
            import select
            
            device_fds = [device.fd for device in self.linux_keyboard_devices]
            
            while self.linux_event_thread is not None and device_fds:
                try:
                    ready, _, _ = select.select(device_fds, [], [], 0.1)
                    
                    for fd in ready:
                        device = next((d for d in self.linux_keyboard_devices if d.fd == fd), None)
                        if device:
                            try:
                                for event in device.read():
                                    if event.type == evdev.ecodes.EV_KEY:
                                        key_name = evdev.ecodes.KEY[event.code]
                                        
                                        # Key down
                                        if event.value == 1: 
                                            self.escape_key_pressed.add(key_name.lower())
                                        
                                        # Key up
                                        elif event.value == 0:  
                                            self.escape_key_pressed.discard(key_name.lower())
                                        
                                        if self.escape_key_pressed >= self.escape_key_combo:
                                            if self.on_escape_detected:
                                                self.on_escape_detected()
                                        
                                        logger.debug(f"Consumed Linux key event: {key_name}")
                            
                            except Exception as e:
                                logger.error(f"Error reading from device {device.name}: {e}")
                                try:
                                    device.ungrab()
                                    device.close()
                                
                                except:
                                    pass
                               
                                device_fds.remove(fd)
                                self.linux_keyboard_devices.remove(device)
                                break
                
                except Exception as e:
                    logger.error(f"Error in Linux keyboard consumer: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Fatal error in Linux keyboard consumer thread: {e}")
    
    # ====================================== MOUSE BLOCKING =====================================
    def _start_mouse_blocking(self):
        """Start mouse input blocking"""
        try:
            if self.platform == "Windows":
                self.mouse_hook = mouse.hook(self._mouse_callback_windows)
                logger.info("Windows mouse blocking started")
            
            elif self.platform == "Darwin":
                from Quartz import CGEventMaskBit, CGEventTapCreate, CGEventTapEnable                   # type: ignore
                event_mask = (
                    CGEventMaskBit(kCGEventLeftMouseDown) |
                    CGEventMaskBit(kCGEventLeftMouseUp) |
                    CGEventMaskBit(kCGEventRightMouseDown) |
                    CGEventMaskBit(kCGEventRightMouseUp)
                )
                
                self.mouse_event_tap = CGEventTapCreate(
                    kCGSessionEventTap,
                    kCGHeadInsertEventTap,
                    kCGEventTapOptionDefault,
                    event_mask,
                    self._mouse_callback_macos,
                    None
                )
                
                if self.mouse_event_tap:
                    CGEventTapEnable(self.mouse_event_tap, True)
                    logger.info("macOS mouse blocking started")
                else:
                    logger.error("Failed to create macOS mouse event tap")
            
            elif self.platform == "Linux":
                logger.warning("Mouse blocking on Linux can be dangerous - not implemented for safety")
                
        except Exception as e:
            logger.error(f"Error starting mouse blocking: {e}")
    
    def _stop_mouse_blocking(self):
        """Stop mouse input blocking"""
        try:
            if self.platform == "Windows":
                if self.mouse_hook:
                    mouse.unhook_all()
                    self.mouse_hook = None
                    logger.info("Windows mouse blocking stopped")
            
            elif self.platform == "Darwin":
                if hasattr(self, 'mouse_event_tap') and self.mouse_event_tap:
                    CGEventTapEnable(self.mouse_event_tap, False)
                    self.mouse_event_tap = None
                    logger.info("macOS mouse blocking stopped")
            
            elif self.platform == "Linux":
                logger.info("Linux mouse blocking stopped (was not implemented)")
                
        except Exception as e:
            logger.error(f"Error stopping mouse blocking: {e}")
    
    def _mouse_callback_windows(self, event):
        """Windows mouse event callback"""
        try:
            if hasattr(event, 'event_type') and event.event_type in ('down', 'up'):
                logger.debug(f"Blocked mouse click: {getattr(event, 'button', 'unknown')}")
                return False  
            else:
                return True  
                
        except Exception as e:
            logger.error(f"Error in Windows mouse callback: {e}")
            return True  
    
    def _mouse_callback_macos(self, proxy, event_type, event, refcon):
        """macOS mouse event callback"""
        try:
            if event_type in (kCGEventLeftMouseDown, kCGEventLeftMouseUp, 
                            kCGEventRightMouseDown, kCGEventRightMouseUp):
                logger.debug("Blocked macOS mouse click")
                return None  
            else:
                return event  
                
        except Exception as e:
            logger.error(f"Error in macOS mouse callback: {e}")
            return event  
    
    # ====================================== TIMEOUT MECHANISM =====================================
    def _start_timeout_monitor(self):
        """Start safety timeout monitor"""
        try:
            self.timout_active = True
            
            def timeout_worker():
                start_time = time.time()
                
                while self.timout_active:
                    elapsed = time.time() - start_time
                    
                    if elapsed >= self.max_block_duration:
                        if self.is_blocking:
                            logger.warning("Input blocking timeout reached, forcing unblock")
                            
                            if self.on_block_timeout:
                                self.on_block_timeout()
                            
                            self.stop_blocking()
                        
                        break
                    
                    time.sleep(1)
            
            self.timeout_thread = threading.Thread(target=timeout_worker, daemon=True)
            self.timeout_thread.start()
            logger.info("Timeout monitor started")
            
        except Exception as e:
            logger.error(f"Error starting timeout monitor: {e}")
    
    def _stop_timeout_monitor(self):
        """Stop timeout monitor"""
        try:
            self.timout_active = False
            if self.timeout_thread:
                self.timeout_thread.join(timeout=1.0)
                self.timeout_thread = None
            logger.info("Timeout monitor stopped")
            
        except Exception as e:
            logger.error(f"Error stopping timeout monitor: {e}")
    
    # ====================================== ESCAPE DETECTION =====================================
    def check_escape_keys_pressed(self) -> bool:
        """Check if escape key combination is currently pressed"""
        try:
            return self.escape_key_pressed >= self.escape_key_combo
        
        except Exception as e:
            logger.error(f"Error checking escape keys: {e}")
            return False
    
    # ====================================== STATE QUERIES =====================================
    def is_input_blocked(self) -> bool:
        """Check if input is currently blocked"""
        try:
            return self.is_blocking
        
        except Exception as e:
            logger.error(f"Failed to check input blocking status: {e}")
            return False
    
    def get_blocking_mode(self) -> BlockingMode:
        """Get current blocking mode"""
        try:
            return self.blocking_mode
        
        except Exception as e:
            logger.error(f"Failed to get blocking mode: {e}")
            return BlockingMode.NONE
    
    def get_blocking_duration(self) -> float:
        """Get how long input has been blocked"""
        try:
            if self.block_start_time is None:
                return 0.0
            
            return time.time() - self.block_start_time
        
        except Exception as e:
            logger.error(f"Failed to get blocking duration: {e}")
            return 0.0
    
    def get_blocker_status(self) -> dict:
        """Get status of input blocker"""
        try:
            timeout_remaining = 0.0
            if self.is_blocking and self.block_start_time:
                elapsed = time.time() - self.block_start_time
                timeout_remaining = max(0, self.max_block_duration - elapsed)
            
            return {
                'platform': self.platform,
                'available': self.blocking_available,
                'is_blocking': self.is_blocking,
                'blocking_mode': self.blocking_mode.value,
                'duration_seconds': self.get_blocking_duration(),
                'escape_combo': list(self.escape_key_combo),
                'timeout_remaining': timeout_remaining
            }
            
        except Exception as e:
            logger.error(f"Error getting blocker status: {e}")
            return {
                'platform': self.platform,
                'available': self.blocking_available,
                'error': str(e)
            }
    
    # ====================================== CLEANUP =====================================
    def cleanup(self):
        """Clean up input blocker resources"""
        try:
            logger.info("Cleaning up InputBlocker...")
            
            # Stop blocking if active
            if self.is_blocking:
                self.stop_blocking()
            
            # Ensure everything is stopped
            self._stop_keyboard_blocking()
            self._stop_mouse_blocking()
            self._stop_timeout_monitor()
            
            logger.info("InputBlocker cleaned up")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")