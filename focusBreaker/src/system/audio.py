"""
Audio System Module - Audio Playback and Volume Management
Handles audio playback, timer warning SFX, volume control, and audio device management.

Supported audio formats: MP3, WAV, OGG, FLAC, AAC
"""

import logging
import os 
from pygame import mixer
from typing import Optional, List, Dict, Any
from pathlib import Path
import threading
import time
from config import AudioConfig

logger = logging.getLogger(__name__)

try: 
    import platform
    PLATFORM_SYSTEM = platform.system()
    
    if PLATFORM_SYSTEM == "Windows":
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            # Test if pycaw actually works by trying to get speakers
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)         # type: ignore   
            volume_controller = cast(interface, POINTER(IAudioEndpointVolume))
            
            # Test getting volume to ensure it works
            test_volume = volume_controller.GetMasterVolumeLevelScalar()                       # type: ignore
            
            VOLUME_CONTROL_AVAILABLE = True
            VOLUME_METHOD = 'pycaw'
            logger.info("Using pycaw for volume control")
            
        except (ImportError, AttributeError, Exception) as e:
            logger.warning(f"pycaw failed: {e}")
            try:
                import ctypes
                from ctypes import wintypes
                VOLUME_CONTROL_AVAILABLE = True
                VOLUME_METHOD = 'winapi'
                logger.info("Using Windows API fallback for volume control")

            except ImportError:
                VOLUME_CONTROL_AVAILABLE = False
                VOLUME_METHOD = None
                logger.warning("No volume control method available")
    
    elif PLATFORM_SYSTEM == "Darwin":
        import subprocess
        VOLUME_CONTROL_AVAILABLE = True
        VOLUME_METHOD = 'osascript'
    
    else:
        VOLUME_CONTROL_AVAILABLE = False
        VOLUME_METHOD = None

except ImportError:
    VOLUME_CONTROL_AVAILABLE = False
    VOLUME_METHOD = None
    logger.warning("System volume control not available")


class AudioManager:
    """Manager all audio playback"""
    def __init__(self, assets_path: str = "assets/audio"):
        """Initialise audio manager"""
        self.assets_path = assets_path
        
        # Audio channels
        self.channel_main = None
        self.channel_music = None
        self.channel_alarm = None

        # Volume levels (0.0 to 1.0)
        self.media_volume = AudioConfig.DEFAULT_MEDIA_VOLUME / 100.0
        self.alarm_volume = AudioConfig.DEFAULT_ALARM_VOLUME / 100.0
        self.music_volume = AudioConfig.DEFAULT_MUSIC_VOLUME / 100.0

        # System volume controller
        self.system_volume_controller = None
        self.original_system_volume = None

        # Currently loaded sounds
        self.current_media: Optional[mixer.Sound] = None
        self.current_music: Optional[mixer.Sound] = None
        self.current_alarm: Optional[mixer.Sound] = None
        
        # Timer for volume restore
        self.restore_timer: Optional[threading.Timer] = None

        self.mixer_initialised = False
        
        logger.info(f"AudioManager initialised with assets path: {self.assets_path}")

    def initialize(self) -> bool:
        """Initialize pygame mixer and audio system"""
        try:
            mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.mixer_initialised = True
            
            # Initialize channels
            self.channel_main = mixer.Channel(0)
            self.channel_music = mixer.Channel(1)
            self.channel_alarm = mixer.Channel(2)
            
            if VOLUME_CONTROL_AVAILABLE:
                self._init_system_volume_control()
            
            logger.info("Pygame mixer initialized successfully.")
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize pygame mixer: {e}")
            self.mixer_initialised = False
            return False

    # ====================================== SYSTEM VOLUME CONTROLS =====================================
    def _init_system_volume_control(self):
        """Initialise system volume controller"""
        try:
            if VOLUME_METHOD == 'pycaw':
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)          # type: ignore   
                self.system_volume_controller = cast(interface, POINTER(IAudioEndpointVolume))
                
            elif VOLUME_METHOD == 'winapi':
                # Windows API fallback using ctypes
                # We'll store the method type and implement volume control in the methods below
                self.system_volume_controller = 'winapi'
                
            elif VOLUME_METHOD == 'osascript':
                self.system_volume_controller = 'osascript'

            else:
                self.system_volume_controller = None

        except Exception as e:
            self.system_volume_controller = None
            logger.warning(f"Failed to initialise system volume controller: {e}")

    def get_system_volume(self):
        """Get current system volume"""
        try:
            volume_controller = self.system_volume_controller
            if volume_controller is None:
                return 1.0
            
            if VOLUME_METHOD == 'pycaw':
                try:
                    volume = volume_controller.GetMasterVolumeLevelScalar()     #type: ignore
                    return volume 
                
                except Exception as e:
                    logger.error("Failed to get system volume")
                    return 1.0
                    
            elif VOLUME_METHOD == 'winapi':
                try:
                    # Windows API fallback using user32.dll
                    user32 = ctypes.windll.user32
                    
                    # Get current volume (this is a simplified approach)
                    # Note: Windows API doesn't have a direct "get master volume" function
                    # We'll return the stored volume if available, otherwise assume 1.0
                    if hasattr(self, '_last_set_volume'):
                        return self._last_set_volume
                    else:
                        return 1.0
                
                except Exception as e:
                    logger.error(f"Failed to get system volume via Windows API: {e}")
                    return 1.0
                
            elif VOLUME_METHOD == 'osascript':
                try: 
                    result = subprocess.run(['osascript', '-e', 'output volume of (get volume settings)'], capture_output=True, text=True)
                    volume = int(result.stdout.strip()) / 100.0
                    
                    return volume
                
                except:
                    return 1.0

            else:
                return 1.0

        except Exception as e:
            logger.warning(f"Failed to fetch system volume: {e}")
            return 1.0
    
    def set_system_volume(self, volume: float):
        """Set system volume temporarily"""
        try:
            volume_controller = self.system_volume_controller
            if volume_controller is None:
                return
            
            if VOLUME_METHOD == 'pycaw':
                try:
                    volume_controller.SetMasterVolumeLevelScalar(volume, None)     #type: ignore
                
                except Exception as e:
                    logger.error("Failed to set system volume")
                    
            elif VOLUME_METHOD == 'winapi':
                try:
                    # Windows API fallback - use keyboard simulation to adjust volume
                    # This is a workaround since Windows API doesn't have direct volume control
                    # We'll simulate keyboard presses for volume up/down
                    import ctypes
                    from ctypes import wintypes
                    
                    # Map volume (0.0-1.0) to number of volume up/down presses needed
                    # This is approximate and may not be very accurate
                    user32 = ctypes.windll.user32
                    
                    # VK_VOLUME_UP = 0xAF, VK_VOLUME_DOWN = 0xAE
                    VK_VOLUME_UP = 0xAF
                    VK_VOLUME_DOWN = 0xAE
                    
                    # Calculate how many steps we need (assuming 50 steps for full range)
                    target_steps = int(volume * 50)
                    current_steps = int((self.get_system_volume() or 1.0) * 50)
                    
                    steps_needed = target_steps - current_steps
                    
                    if steps_needed > 0:
                        # Need to increase volume
                        for _ in range(min(steps_needed, 10)):  # Limit to 10 steps to avoid too many presses
                            user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                            user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)  # Key up
                            time.sleep(0.01)
                    elif steps_needed < 0:
                        # Need to decrease volume
                        for _ in range(min(-steps_needed, 10)):  # Limit to 10 steps
                            user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                            user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)  # Key up
                            time.sleep(0.01)
                    
                    # Store the volume we attempted to set
                    self._last_set_volume = volume
                    
                except Exception as e:
                    logger.error(f"Failed to set system volume via Windows API: {e}")
                
            elif VOLUME_METHOD == 'osascript':
                try: 
                    volume_int = int(volume * 100)
                    subprocess.run(['osascript', '-e', f'set volume output volume {volume_int}'])
                
                except:
                    logger.error("Failed to set system volume")

            else:
                logger.error("Failed to set system volume") 

        except Exception as e:
            logger.warning(f"Failed to set system volume: {e}")
            return 

    def boost_system_volume(self, boost_amount: float = AudioConfig.DEFAULT_VOLUME_BOOST):
        """Temporarily boost system volume for media playback"""
        try:
            if self.system_volume_controller is None:
                return
            
            # Validate boost_amount
            boost_amount = max(0.0, min(1.0, boost_amount))
            
            if self.original_system_volume is None:
                self.original_system_volume = self.get_system_volume()
            
            new_volume = min(1.0, self.original_system_volume + boost_amount)
            self.set_system_volume(new_volume)

            logger.info(f"System volume boosted from {self.original_system_volume:.2f} to {new_volume:.2f}")
        
        except Exception as e:
            logger.error(f"Failed to boost system volume: {e}")

    def restore_system_volume(self):
        """Restore system volume to original level"""
        try:
            original_volume = self.original_system_volume

            if original_volume is not None:
                self.set_system_volume(original_volume)
                logger.info(f"System volume restored to {original_volume}")

                self.original_system_volume = None

        except Exception as e:
            logger.error(f"Failed to restore system volume: {e}")
        
    # ====================================== VOLUME SETTINGS =====================================
    def set_media_volume(self, volume: int):
        """Set media volume level"""
        try:
            if self.channel_main is None:
                logger.error("Audio channels not initialized")
                return
                
            volume = max(0, min(100, volume))
            self.media_volume = volume / 100.0

            self.channel_main.set_volume(self.media_volume)
            logger.info(f"Media volume set to {volume}%")

        except Exception as e:
            logger.error(f"Failed to set media volume: {e}")

    def set_alarm_volume(self, volume: int):
        """Set alarm volume level"""
        try:
            if self.channel_alarm is None:
                logger.error("Audio channels not initialized")
                return
                
            volume = max(0, min(100, volume))
            self.alarm_volume = volume / 100.0

            self.channel_alarm.set_volume(self.alarm_volume)
            logger.info(f"Alarm volume set to {volume}%")

        except Exception as e:
            logger.error(f"Failed to set alarm volume: {e}")
    
    def set_music_volume(self, volume: int):
        """Set background music volume level"""
        try:
            if self.channel_music is None:
                logger.error("Audio channels not initialized")
                return
                
            volume = max(0, min(100, volume))
            self.music_volume = volume / 100.0

            self.channel_music.set_volume(self.music_volume)
            logger.info(f"Music volume set to {volume}%")

        except Exception as e:
            logger.error(f"Failed to set music volume: {e}")

    # ====================================== AUDIO PLAYBACK  =====================================
    def play_audio_file(self, file_path: str, boost_volume: bool = True):
        """Play an audio file on the main channel"""
        if not self.mixer_initialised:
            logger.error("Pygame mixer not initialised. Cannot play audio.")
            return

        if self.channel_main is None:
            logger.error("Audio channels not initialized")
            return

        try:
            sound = mixer.Sound(file_path)
            sound.set_volume(self.media_volume)

            if boost_volume:
                self.boost_system_volume(boost_amount=AudioConfig.DEFAULT_VOLUME_BOOST)
            
            self.current_media = sound
            self.channel_main.play(sound)

            duration = sound.get_length()

            if boost_volume and self.original_system_volume is not None:
                # Cancel any existing restore timer
                if self.restore_timer and self.restore_timer.is_alive():
                    self.restore_timer.cancel()
                
                # Start new restore timer
                self.restore_timer = threading.Timer(duration + 0.5, self.restore_system_volume)
                self.restore_timer.start()
            
            logger.info(f"Playing audio file: {file_path}")
        
        except Exception as e:
            logger.error(f"Failed to play audio file {file_path}: {e}")
        
    def play_alarm(self, file_path: str, duration_seconds: Optional[int] = None):
        """Play break end alarm sound"""
        if not self.mixer_initialised:
            logger.error("Pygame mixer not initialised. Cannot play alarm.")
            return

        if self.channel_alarm is None:
            logger.error("Audio channels not initialized")
            return

        try:
            sound = mixer.Sound(file_path)
            sound.set_volume(self.alarm_volume)
            
            self.current_alarm = sound
            self.channel_alarm.play(sound, loops = -1 if duration_seconds is None else 0)

            if duration_seconds is not None:
                timer = threading.Timer(duration_seconds, self.stop_alarm)
                timer.start()

            logger.info(f"Playing alarm sound: {file_path}")
        
        except Exception as e:
            logger.error(f"Failed to play alarm sound {file_path}: {e}")

    
    def play_background_music(self, file_path: str, loop: bool = True, fade_in_ms: int = 1000):
        """Play background music during break"""
        if not self.mixer_initialised:
            logger.error("Pygame mixer not initialised. Cannot play background music.")
            return

        if self.channel_music is None:
            logger.error("Audio channels not initialized")
            return

        try:
            sound = mixer.Sound(file_path)
            sound.set_volume(self.music_volume)
            
            self.current_music = sound
            loops = -1 if loop else 0

            if fade_in_ms > 0:
                self.channel_music.play(sound, loops = loops, fade_ms = fade_in_ms)
            
            else:
                self.channel_music.play(sound, loops = loops)

            logger.info(f"Playing background music: {file_path}")
        
        except Exception as e:
            logger.error(f"Failed to play background music {file_path}: {e}")

    def stop_alarm(self):
        """Stop alarm sound"""
        try:
            if self.channel_alarm is None:
                return
                
            if self.channel_alarm.get_busy():
                self.channel_alarm.stop()
                logger.info("Alarm sound stopped.")

        except Exception as e:
            logger.error(f"Failed to stop alarm: {e}")
    
    def stop_music(self, fade_out_ms: int = 1000):
        """Stop background music"""
        try:
            if self.channel_music is None:
                return
                
            if self.channel_music.get_busy():
                if fade_out_ms > 0:
                    self.channel_music.fadeout(fade_out_ms)
                
                else:
                    self.channel_music.stop()
                
                logger.info("Music stopped.")

        except Exception as e:
            logger.error(f"Failed to stop music: {e}")
    
    def pause_music(self):
        """Pause background music"""
        try:
            if self.channel_music is None:
                return
                
            if self.channel_music.get_busy():
                self.channel_music.pause()
                logger.info("Music paused.")

        except Exception as e:
            logger.error(f"Failed to pause music: {e}")
    
    def resume_music(self):
        """Resume background music"""
        try:
            if self.channel_music is None:
                return
                
            if self.channel_music.get_busy():
                self.channel_music.unpause()
                logger.info("Music resumed.")

        except Exception as e:
            logger.error(f"Failed to resume music: {e}")
    
    def stop_all(self):
        try:
            if self.channel_main is not None:
                self.channel_main.stop()
            if self.channel_music is not None:
                self.channel_music.stop()
            if self.channel_alarm is not None:
                self.channel_alarm.stop()

            self.restore_system_volume()

            logger.info("All audio playback stopped.")
        except Exception as e:
            logger.error(f"Failed to stop all audio: {e}")

    # ====================================== AUDIO PLAYBACK  =====================================
    def validate_audio_file(self, file_path: str) -> bool:
        """Validate that audio file exists and is loadable"""

        if not os.path.isfile(file_path):
            logger.error(f"Audio file does not exist: {file_path}")
            return False

        extension = os.path.splitext(file_path)[1].lower()
        supported_formats = ['.mp3', '.wav', '.ogg', '.flac', '.aac']

        if extension not in supported_formats:
            logger.error(f"Unsupported audio format: {extension}")
            return False

        try:
            test_sound = mixer.Sound(file_path)
            return True
        
        except Exception as e:
            logger.error(f"Failed to load audio file {file_path}: {e}")
            return False
    
    def get_audio_duration(self, file_path: str) -> float:
        """Get duration of audio file in seconds"""
        try:
            sound = mixer.Sound(file_path)
            duration = sound.get_length()

            return duration
        
        except Exception as e:
            logger.error(f"Failed to get duration of audio file {file_path}: {e}")
            return 0.0
    
    def list_audio_files(self, directory: str) -> List[str]:
        """List all audio files in a directory"""
        try:
            audio_files = []
            supported_formats = ['.mp3', '.wav', '.ogg', '.flac', '.aac']

            if not os.path.isdir(directory):
                logger.error(f"Directory does not exist: {directory}")
                return audio_files

            for file in os.listdir(directory):
                full_path = os.path.join(directory, file)
                if os.path.isfile(full_path):
                    extension = os.path.splitext(file)[1].lower()
                    if extension in supported_formats:
                        audio_files.append(full_path)
            
            return sorted(audio_files)
        
        except Exception as e:
            logger.error(f"Failed to list audio files in {directory}: {e}")
            return []

    # ====================================== STATE QUERIES  =====================================
    def is_playing_media(self) -> bool:
        """Check if media is currently playing"""
        try:
            if self.channel_main is None:
                return False
            
            return self.channel_main.get_busy()
        
        except Exception as e:
            logger.error(f"Failed to check media playing status: {e}")
            return False

    def is_playing_music(self) -> bool:
        """Check if background music is currently playing"""
        try:
            if self.channel_music is None:
                return False
            
            return self.channel_music.get_busy()
        
        except Exception as e:
            logger.error(f"Failed to check music playing status: {e}")
            return False
    
    def is_playing_alarm(self) -> bool:
        """Check if alarm sound is currently playing"""
        try:
            if self.channel_alarm is None:
                return False
            
            return self.channel_alarm.get_busy()
       
        except Exception as e:
            logger.error(f"Failed to check alarm playing status: {e}")
            return False
    
    def get_audio_status(self) -> Dict[str, Any]:
        """Get status of all audio channels"""
        try:
            return {
                'mixer_initialised': self.mixer_initialised,
                'media_playing': self.is_playing_media(),
                'music_playing': self.is_playing_music(),
                'alarm_playing': self.is_playing_alarm(),
                'media_volume': self.media_volume,
                'music_volume': self.music_volume,
                'alarm_volume': self.alarm_volume,
                'system_volume_boosted': self.original_system_volume is not None
            }
      
        except Exception as e:
            logger.error(f"Failed to get audio status: {e}")
            return {
                'mixer_initialised': False,
                'media_playing': False,
                'music_playing': False,
                'alarm_playing': False,
                'media_volume': 0.0,
                'music_volume': 0.0,
                'alarm_volume': 0.0,
                'system_volume_boosted': False
            }
    
    # ====================================== CLEANUP =====================================
    def cleanup(self):
        """Cleanup audio manager resources"""
        try:
            self.stop_all()
            self.restore_system_volume()

            # Cancel any pending restore timer
            if self.restore_timer and self.restore_timer.is_alive():
                self.restore_timer.cancel()
                self.restore_timer = None

            if self.mixer_initialised:
                mixer.quit()
                self.mixer_initialised = False
                logger.info("Pygame mixer quit and resources cleaned up.")
        
        except Exception as e:
            logger.error(f"Failed to cleanup audio resources: {e}")
    
# ====================================== HELPER FUNCTIONS =====================================
def create_default_alarm_sound(output_path: str, frequency: int = 440, duration_ms: int = 500):
    """Generate simple beep alarm sound as fallback"""
    try:
        import numpy as np

        sample_rate = 44100
        duration_seconds = duration_ms / 1000.0
        num_samples = int(sample_rate * duration_seconds)

        # Generate sine wave
        t = np.linspace(0, duration_seconds, num_samples)
        wave_data = np.sin(2 * np.pi * frequency * t)

        # Convert to 16-bit PCM
        wave_data_converted = (wave_data * 32767).astype(np.int16)

        # Create stereo sound
        stereo = np.column_stack((wave_data_converted, wave_data_converted))

        # Save as WAV file
        from scipy.io import wavfile
        wavfile.write(output_path, sample_rate, stereo)

        logger.info(f"Default beep alarm created at: {output_path}")

    except Exception as e:
        logger.error(f"Failed to create default alarm sound: {e}")