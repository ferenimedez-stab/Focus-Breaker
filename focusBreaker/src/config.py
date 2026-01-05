"""
Configuration Module - Application Configuration Management
Handles all app configuration, constants, paths, and settings validation
"""

import os
from pathlib import Path
from typing import Set

# ========================= APPLICATION INFO =========================
APP_NAME = "FocusBreaker"
APP_VERSION = "0.3.0"
APP_AUTHOR = "Fernanne Hannah Enimedez"
APP_DESCRIPTION = "Productivity app with enforced break discipline"

# Schema version for database migrations
SCHEMA_VERSION = 1

# ========================= PATH CONFIGURATION =========================
class AppPaths:
    """
    Application directory and file paths
    
    STRUCTURE:
    focusBreaker/
    ├── src/
    │   ├── assets/
    │   │   ├── audio/
    │   │   ├── media/
    │   │   │   ├── normal/
    │   │   │   ├── strict/
    │   │   │   └── focused/
    │   │   └── icons/
    │   ├── data/
    │   └── logs/
    └── focusbreaker.db
    """
    
    # Base directories
    BASE_DIR = Path(__file__).parent.parent  # Project root
    SRC_DIR = BASE_DIR / "src"
    
    # Assets
    ASSETS_DIR = SRC_DIR / "assets"
    AUDIO_DIR = ASSETS_DIR / "audio"
    MEDIA_DIR = ASSETS_DIR / "media"
    ICONS_DIR = ASSETS_DIR / "icons"
    
    # Media subdirectories (per mode)
    MEDIA_NORMAL_DIR = MEDIA_DIR / "normal"
    MEDIA_NORMAL_DEFAULTS = MEDIA_NORMAL_DIR / "defaults"
    MEDIA_NORMAL_USER = MEDIA_NORMAL_DIR / "user"
    
    MEDIA_STRICT_DIR = MEDIA_DIR / "strict"
    MEDIA_STRICT_DEFAULTS = MEDIA_STRICT_DIR / "defaults"
    MEDIA_STRICT_USER = MEDIA_STRICT_DIR / "user"
    
    MEDIA_FOCUSED_DIR = MEDIA_DIR / "focused"
    MEDIA_FOCUSED_DEFAULTS = MEDIA_FOCUSED_DIR / "defaults"
    MEDIA_FOCUSED_USER = MEDIA_FOCUSED_DIR / "user"
    
    # Data and logs
    DATA_DIR = SRC_DIR / "data"
    LOGS_DIR = SRC_DIR / "logs"
    
    # Database
    DATABASE_FILE = BASE_DIR / "focusbreaker.db"
    
    @classmethod
    def get_database_path(cls) -> Path:
        """
        Get database file path
        """
        return cls.DATABASE_FILE
    
    @classmethod
    def get_media_dir(cls, mode: str, user_content: bool = False) -> Path:
        """
        Get media directory for a specific mode
        """
        if mode == 'normal':
            return cls.MEDIA_NORMAL_USER if user_content else cls.MEDIA_NORMAL_DEFAULTS
        elif mode == 'strict':
            return cls.MEDIA_STRICT_USER if user_content else cls.MEDIA_STRICT_DEFAULTS
        elif mode == 'focused':
            return cls.MEDIA_FOCUSED_USER if user_content else cls.MEDIA_FOCUSED_DEFAULTS
        else:
            raise ValueError(f"Invalid mode: {mode}")
    
    @classmethod
    def ensure_directories_exist(cls):
        """
        Create all necessary directories if they don't exist
        """
        directories = [
            cls.ASSETS_DIR,
            cls.AUDIO_DIR,
            cls.MEDIA_DIR,
            cls.ICONS_DIR,
            cls.MEDIA_NORMAL_DEFAULTS,
            cls.MEDIA_NORMAL_USER,
            cls.MEDIA_STRICT_DEFAULTS,
            cls.MEDIA_STRICT_USER,
            cls.MEDIA_FOCUSED_DEFAULTS,
            cls.MEDIA_FOCUSED_USER,
            cls.DATA_DIR,
            cls.LOGS_DIR
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

# ========================= AUDIO CONFIGURATION =========================
class AudioConfig:
    """Audio system configuration"""
    # Supported audio formats
    SUPPORTED_AUDIO_FORMATS: Set[str] = {'.mp3', '.wav', '.ogg', '.flac'}
    
    # Default volumes (0-100)
    DEFAULT_MEDIA_VOLUME = 80
    DEFAULT_ALARM_VOLUME = 70
    DEFAULT_MUSIC_VOLUME = 50
    
    # Volume limits
    MIN_VOLUME = 0
    MAX_VOLUME = 100
    
    # System volume boost
    DEFAULT_VOLUME_BOOST = 0.2      # 20% boost
    MAX_VOLUME_BOOST = 0.5          # 50% max boost
    
    # Audio timing
    DEFAULT_ALARM_DURATION_SECONDS = 5
    DEFAULT_IMAGE_DISPLAY_DURATION_SECONDS = 5
    
    # Audio file names (fallbacks)
    DEFAULT_ALARM_SOUND = "alarm.wav"
    DEFAULT_BREAK_MUSIC = "ambient.mp3"

# ========================= MEDIA CONFIGURATION =========================
class MediaConfig:
    """Media system configuration"""
    # Supported media formats
    SUPPORTED_VIDEO_FORMATS: Set[str] = {'.mp4', '.avi', '.mov', '.webm'}
    SUPPORTED_IMAGE_FORMATS: Set[str] = {'.jpg', '.jpeg', '.png', '.gif'}
    
    # File size limits
    MAX_VIDEO_SIZE_MB = 100
    MAX_IMAGE_SIZE_MB = 10
    
    # Media playback
    VIDEO_PLAYBACK_VOLUME = 0.8
    IMAGE_DISPLAY_DURATION_SECONDS = 5
    
    # Jump scare settings
    JUMPSCARE_BRIGHTNESS_BOOST = 100        # Max brightness
    JUMPSCARE_VOLUME_BOOST = 0.3            # 30% volume increase

# ========================= MODE CONFIGURATION =========================
class ModeConfig:
    """
    Configuration for each work mode
    """
    # Normal Mode defaults
    NORMAL_WORK_INTERVAL_MINUTES = 25
    NORMAL_BREAK_DURATION_MINUTES = 5
    NORMAL_SNOOZE_DURATION_MINUTES = 5
    NORMAL_MAX_SNOOZE_PASSES = 3
    
    # Strict Mode defaults
    STRICT_WORK_INTERVAL_MINUTES = 52
    STRICT_BREAK_DURATION_MINUTES = 17
    STRICT_COOLDOWN_MINUTES = 20
    
    # Focused Mode defaults
    FOCUSED_MANDATORY_BREAK_MINUTES = 30
    FOCUSED_BREAK_SCALING_ENABLED: bool = True
    
    # Break scaling for Focused mode
    FOCUSED_BREAK_SCALING_RULES = {
        (0, 120):    30,                    # 0-2 hours → 30 min break
        (120, 240):  45,                    # 2-4 hours → 45 min break
        (240, float('inf')):  60,           # 4+ hours → 60 min break
    }
    
    # Mode validation
    MIN_WORK_DURATION_MINUTES = 5
    MAX_WORK_DURATION_MINUTES = 480  # 8 hours
    
    MIN_BREAK_DURATION_MINUTES = 1
    MAX_BREAK_DURATION_MINUTES = 60
    
    @staticmethod
    def get_focused_break_duration(work_duration_minutes: int) -> int:
        """
        Calculate break duration for Focused mode based on work duration
        """
        if not ModeConfig.FOCUSED_BREAK_SCALING_ENABLED:
            return ModeConfig.FOCUSED_MANDATORY_BREAK_MINUTES
        
        for (min_dur, max_dur), break_dur in ModeConfig.FOCUSED_BREAK_SCALING_RULES.items():
            if min_dur <= work_duration_minutes < max_dur:
                return break_dur
        
        return ModeConfig.FOCUSED_MANDATORY_BREAK_MINUTES

# ========================= ENERGY PATTERN CONFIGURATION =========================
class EnergyConfig:
    """Energy pattern based break scheduling configuration"""
    # Energy pattern break schedules (minutes)
    MORNING_PERSON_BREAKS = [20, 40, 70, 100]
    AFTERNOON_SLUMP_BREAKS = [30, 60, 90]
    NIGHT_OWL_BREAKS = [35, 70, 105]
    NORMAL_BREAKS = [25, 50, 75, 100]

# ========================= ESCAPE HATCH CONFIGURATION =========================
class EscapeHatchConfig:
    """Emergency escape hatch configuration"""
    # Default key combination
    DEFAULT_KEY_COMBO = "ctrl+alt+shift+e"
    
    # Hold duration
    DEFAULT_HOLD_DURATION_SECONDS = 3
    MIN_HOLD_DURATION_SECONDS = 1
    MAX_HOLD_DURATION_SECONDS = 5
    
    # Debounce
    DEFAULT_DEBOUNCE_MS = 100
    
    # Quality score penalty
    EMERGENCY_EXIT_QUALITY_PENALTY = 0.2  
    
    # Availability by mode
    AVAILABLE_IN_NORMAL = False
    AVAILABLE_IN_STRICT = True
    AVAILABLE_IN_FOCUSED = True

# ========================= STREAK CONFIGURATION =========================
class StreakConfig:
    """Streak tracking configuration"""
    # Streak types
    STREAK_TYPES = ['session_streak', 'perfect_session', 'daily_consistency']
    
    # Milestones (for celebrations)
    STREAK_MILESTONES = [5, 10, 25, 50, 100, 250, 500, 1000]
    
    # Quality score calculation
    QUALITY_SCORE_WEIGHTS = {
        'breaks_taken': 1.0,
        'breaks_snoozed': 0.5,
        'breaks_skipped': 0.0,
        'emergency_exits': -0.2  # Penalty
    }
    
    # Daily consistency risk levels (hours since last session)
    DAILY_RISK_LOW_HOURS = 12
    DAILY_RISK_MEDIUM_HOURS = 12
    DAILY_RISK_HIGH_HOURS = 18
    
    # Statistics calculation period (days)
    STATISTICS_PERIOD_DAYS = 365
    
    # Hours in a day (for streak calculations)
    HOURS_IN_DAY = 24

# ========================= UI CONFIGURATION =========================
class UIConfig:
    """User interface configuration"""
    # Window settings
    DEFAULT_WINDOW_WIDTH = 800
    DEFAULT_WINDOW_HEIGHT = 600
    MIN_WINDOW_WIDTH = 600
    MIN_WINDOW_HEIGHT = 400
    
    # Break window (Normal mode)
    BREAK_WINDOW_WIDTH = 400
    BREAK_WINDOW_HEIGHT = 300
    BREAK_WINDOW_ALWAYS_ON_TOP = True
    
    # Colors (hex)
    COLOR_PRIMARY = "#2196F3"
    COLOR_SUCCESS = "#4CAF50"
    COLOR_WARNING = "#FF9800"
    COLOR_DANGER = "#F44336"
    COLOR_BACKGROUND = "#FFFFFF"
    COLOR_TEXT = "#212121"
    
    # Fonts
    FONT_FAMILY = "Segoe UI, Arial, sans-serif"
    FONT_SIZE_SMALL = 12
    FONT_SIZE_NORMAL = 14
    FONT_SIZE_LARGE = 18
    FONT_SIZE_HEADING = 24
    
    # Animation durations (ms)
    ANIMATION_FAST = 150
    ANIMATION_NORMAL = 300
    ANIMATION_SLOW = 500
    
    # Progress bar update interval (ms)
    PROGRESS_UPDATE_INTERVAL = 100

# ========================= NOTIFICATION CONFIGURATION =========================
class NotificationConfig:
    """Notification settings"""
    # Timing
    BREAK_WARNING_MINUTES = 2      # Warn 2 minutes before break
    BREAK_END_WARNING_SECONDS = 60  # Warn 60 seconds before break ends
    
    # Notification types
    NOTIFY_BREAK_INCOMING = True
    NOTIFY_BREAK_STARTING = True
    NOTIFY_BREAK_ENDING = True
    NOTIFY_BREAK_COMPLETE = True
    NOTIFY_SESSION_COMPLETE = True
    NOTIFY_STREAK_MILESTONE = True
    
    # System tray
    TRAY_ICON_WORKING = "icon_working.png"
    TRAY_ICON_BREAK = "icon_break.png"
    TRAY_ICON_PAUSED = "icon_paused.png"

# ========================= TIMER CONFIGURATION =========================
class TimerConfig:
    """Timer system configuration"""
    # Timer update intervals (seconds)
    TIMER_UPDATE_INTERVAL_SECONDS = 1.0
    TIMER_PAUSE_CHECK_INTERVAL_SECONDS = 0.1
    
    # Break timer warning (uses NotificationConfig.BREAK_END_WARNING_SECONDS)
    
    # Thread settings
    TIMER_THREAD_TIMEOUT_SECONDS = 1.0
    
    # Time conversion constants
    SECONDS_PER_MINUTE = 60
    MINUTES_PER_HOUR = 60
    SECONDS_PER_HOUR = 3600

# ========================= LOGGING CONFIGURATION =========================
class LogConfig:
    """Logging configuration"""
    # Log file
    LOG_FILE = AppPaths.LOGS_DIR / "focusbreaker.log"
    
    # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    LOG_LEVEL = "INFO"
    LOG_LEVEL_FILE = "DEBUG"    # More verbose in file
    LOG_LEVEL_CONSOLE = "INFO"  # Less verbose in console
    
    # Log format
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # Rotation
    MAX_LOG_FILE_SIZE_MB = 10
    MAX_LOG_FILE_COUNT = 5
    
    # What to log
    LOG_DATABASE_QUERIES = False
    LOG_TIMER_TICKS = False  # Can be very verbose
    LOG_UI_EVENTS = True
    LOG_AUDIO_EVENTS = True

# ========================= FEATURE FLAGS =========================
class FeatureFlags:
    """
    Feature toggles for development and testing
    
    USAGE:
    IF FeatureFlags.ENABLE_ANALYTICS:
        track_event(...)
    """
    
    # Core features
    ENABLE_BREAK_MUSIC: bool = True
    ENABLE_INPUT_BLOCKING: bool = True
    ENABLE_BRIGHTNESS_CONTROL: bool = True
    ENABLE_SYSTEM_VOLUME_BOOST: bool = True
    
    # UI features
    ENABLE_ANIMATIONS: bool = True
    ENABLE_SOUND_EFFECTS: bool = True
    ENABLE_TRAY_NOTIFICATIONS: bool = True
    
    # Data features
    ENABLE_ANALYTICS: bool = True
    ENABLE_ACTIVITY_LOGGING: bool = True
    ENABLE_CRASH_REPORTING: bool = False
    
    # Advanced features
    ENABLE_CLOUD_SYNC: bool = False  # Future feature
    ENABLE_SOCIAL_FEATURES: bool = False  # Future feature
    ENABLE_AI_SUGGESTIONS: bool = False  # Future feature
    
    # Debug features
    DEBUG_MODE: bool = False
    DEBUG_SKIP_INTRO: bool = False
    DEBUG_FAST_TIMERS: bool = False  # Makes timers run faster for testing


# ========================= VALIDATION =========================

class ValidationRules:
    """
    Validation rules for user input
    
    USAGE:
    ValidationRules.validate_work_duration(minutes)
    → raises ValueError if invalid
    """
    @staticmethod
    def validate_work_duration(minutes: int) -> bool:
        """
        Validate work duration
        
        PARAMETERS:
        - minutes: Work duration to validate
        
        RETURNS:
        - True if valid
        
        RAISES:
        - ValueError if invalid
        
        PSEUDOCODE:
        IF minutes < ModeConfig.MIN_WORK_DURATION_MINUTES:
            RAISE ValueError(f"Work duration too short (min: {MIN})")
        
        IF minutes > ModeConfig.MAX_WORK_DURATION_MINUTES:
            RAISE ValueError(f"Work duration too long (max: {MAX})")
        
        RETURN True
        """
        if minutes < ModeConfig.MIN_WORK_DURATION_MINUTES:
            raise ValueError(f"Work duration must be at least {ModeConfig.MIN_WORK_DURATION_MINUTES} minutes")
        
        if minutes > ModeConfig.MAX_WORK_DURATION_MINUTES:
            raise ValueError(f"Work duration cannot exceed {ModeConfig.MAX_WORK_DURATION_MINUTES} minutes")
        
        return True
    
    @staticmethod
    def validate_break_duration(minutes: int) -> bool:
        """Validate break duration"""
        if minutes < ModeConfig.MIN_BREAK_DURATION_MINUTES:
            raise ValueError(f"Break duration must be at least {ModeConfig.MIN_BREAK_DURATION_MINUTES} minutes")
        
        if minutes > ModeConfig.MAX_BREAK_DURATION_MINUTES:
            raise ValueError(f"Break duration cannot exceed {ModeConfig.MAX_BREAK_DURATION_MINUTES} minutes")
        
        return True
    
    @staticmethod
    def validate_volume(volume: int) -> bool:
        """Validate volume level (0-100)"""
        if volume < AudioConfig.MIN_VOLUME or volume > AudioConfig.MAX_VOLUME:
            raise ValueError(f"Volume must be between {AudioConfig.MIN_VOLUME} and {AudioConfig.MAX_VOLUME}")
        
        return True
    
    @staticmethod
    def validate_mode(mode: str) -> bool:
        """Validate work mode"""
        valid_modes = ['normal', 'strict', 'focused']
        if mode.lower() not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of: {valid_modes}")
        
        return True
    
    @staticmethod
    def validate_file_size(file_path: Path, max_size_mb: int) -> bool:
        """
        Validate file size
        
        PARAMETERS:
        - file_path: Path to file
        - max_size_mb: Maximum size in megabytes
        
        PSEUDOCODE:
        IF NOT file_path.exists():
            RAISE FileNotFoundError(f"File not found: {file_path}")
        
        size_mb = file_path.stat().st_size / (1024 * 1024)
        
        IF size_mb > max_size_mb:
            RAISE ValueError(f"File too large: {size_mb:.1f}MB (max: {max_size_mb}MB)")
        
        RETURN True
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        size_mb = file_path.stat().st_size / (1024 * 1024)
        
        if size_mb > max_size_mb:
            raise ValueError(f"File too large: {size_mb:.1f}MB (max: {max_size_mb}MB)")
        
        return True


# ========================= ENVIRONMENT DETECTION =========================

class Environment:
    """
    Detect and expose environment information
    
    USAGE:
    IF Environment.is_development():
        enable_debug_features()
    """
    
    @staticmethod
    def is_development() -> bool:
        """Check if running in development mode"""
        return FeatureFlags.DEBUG_MODE or os.getenv('FOCUSBREAKER_ENV') == 'development'
    
    @staticmethod
    def is_production() -> bool:
        """Check if running in production mode"""
        return not Environment.is_development()
    
    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows"""
        import platform
        return platform.system() == "Windows"
    
    @staticmethod
    def is_macos() -> bool:
        """Check if running on macOS"""
        import platform
        return platform.system() == "Darwin"
    
    @staticmethod
    def is_linux() -> bool:
        """Check if running on Linux"""
        import platform
        return platform.system() == "Linux"
    
    @staticmethod
    def get_platform_name() -> str:
        """Get platform name"""
        import platform
        return platform.system()


# ========================= INITIALIZATION =========================
def initialize_app():
    """
    Initialize application on startup
    
    WHAT IT DOES:
    - Creates necessary directories
    - Sets up logging
    - Validates configuration
    - Prints startup info
    
    CALL THIS:
    At the very start of main.py
    
    PSEUDOCODE:
    print(f"Initializing {APP_NAME} v{APP_VERSION}...")
    
    # Create directories
    AppPaths.ensure_directories_exist()
    print("✓ Directories created")
    
    # Setup logging
    setup_logging()
    print("✓ Logging configured")
    
    # Log startup info
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"{APP_NAME} v{APP_VERSION} starting...")
    logger.info(f"Platform: {Environment.get_platform_name()}")
    logger.info(f"Environment: {'Development' IF Environment.is_development() ELSE 'Production'}")
    logger.info(f"Database: {AppPaths.get_database_path()}")
    
    print(f"✓ {APP_NAME} initialized successfully!")
    """
    print(f"Initializing {APP_NAME} v{APP_VERSION}...")
    
    # Create directories
    AppPaths.ensure_directories_exist()
    print("✓ Directories created")
    
    # Setup logging
    setup_logging()
    print("✓ Logging configured")
    
    # Log startup info
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"{APP_NAME} v{APP_VERSION} starting...")
    logger.info(f"Platform: {Environment.get_platform_name()}")
    logger.info(f"Environment: {'Development' if Environment.is_development() else 'Production'}")
    logger.info(f"Database: {AppPaths.get_database_path()}")
    
    print(f"✓ {APP_NAME} initialized successfully!")


def setup_logging():
    """
    Configure logging system
    
    WHAT IT DOES:
    Sets up file and console logging handlers
    Configures log levels and formats
    
    PSEUDOCODE:
    import logging
    from logging.handlers import RotatingFileHandler
    
    # Ensure log directory exists
    LogConfig.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Create formatters
    formatter = logging.Formatter(
        LogConfig.LOG_FORMAT,
        datefmt=LogConfig.LOG_DATE_FORMAT
    )
    
    # File handler (rotating)
    file_handler = RotatingFileHandler(
        LogConfig.LOG_FILE,
        maxBytes=LogConfig.MAX_LOG_FILE_SIZE_MB * 1024 * 1024,
        backupCount=LogConfig.MAX_LOG_FILE_COUNT
    )
    file_handler.setLevel(getattr(logging, LogConfig.LOG_LEVEL_FILE))
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LogConfig.LOG_LEVEL_CONSOLE))
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LogConfig.LOG_LEVEL))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    """
    import logging
    from logging.handlers import RotatingFileHandler
    
    # Ensure log directory exists
    LogConfig.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        LogConfig.LOG_FORMAT,
        datefmt=LogConfig.LOG_DATE_FORMAT
    )
    
    # File handler
    file_handler = RotatingFileHandler(
        LogConfig.LOG_FILE,
        maxBytes=LogConfig.MAX_LOG_FILE_SIZE_MB * 1024 * 1024,
        backupCount=LogConfig.MAX_LOG_FILE_COUNT
    )
    file_handler.setLevel(getattr(logging, LogConfig.LOG_LEVEL_FILE))
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LogConfig.LOG_LEVEL_CONSOLE))
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LogConfig.LOG_LEVEL))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)