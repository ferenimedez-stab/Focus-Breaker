# FocusBreaker - Complete Feature Coverage

## 📋 Core Features

### 1. Task Management
- Create task with name
- Set allocated work time (in minutes or time range like 8:00 AM - 10:00 AM)
- Choose work mode (Normal/Strict/Focused)
- Auto-calculate breaks OR manually set number/duration
- Task history tracking

### 2. Three Work Modes

#### Normal Mode (Flexible)
- Work interval: 25 minutes
- Break duration: 5 minutes (customizable)
- Break behavior:
  - Pop-up window (small, movable, always-on-top)
  - Media plays (surprise effects + user uploads, randomized)
  - Countdown timer visible
  - Three buttons available: [Take Break] [Snooze] [Skip]
  - Buttons stay active entire break (temptation design)
  - Can't close window until break ends naturally
  - Snooze: Default 5 minutes (adjustable)
  - Skip: Allowed (breaks streak)
- Session end: Option to extend or rest
- No escape hatch: Not needed (already flexible)

#### Strict Mode (Enforced)
- Work interval: 52 minutes
- Break duration: 17 minutes (customizable)
- Break behavior:
  - Full-screen overlay (cannot minimize, cannot escape normally)
  - Media plays (intense effects + user uploads, randomized)
  - Countdown timer visible
  - NO snooze/skip buttons
  - Must wait entire duration
- Session end:
  - NO extend option
  - Mandatory cooldown: 20 minutes minimum (adjustable)
  - Full-screen overlay during cooldown
  - Emergency escape hatch: Hidden key combo (e.g., Ctrl+Alt+Shift+E, hold 3 seconds)
  - Logs emergency exit (affects streak)
  - Available during breaks AND cooldown period

#### Focused Mode (Deep Work)
- Work interval: No breaks during entire allocated time
- Break behavior: NONE during work
- Session end:
  - Media plays (session-end signal or user media) - ONE dramatic signal
  - Full-screen overlay
  - Mandatory break: 30 minutes minimum (adjustable)
  - Can scale with work duration:
    - 1-2 hours → 30 min break
    - 2-4 hours → 45 min break
    - 4+ hours → 60 min break
  - Cannot work until break completes
  - Emergency escape hatch: Hidden key combo (e.g., Ctrl+Alt+Shift+E, hold 3 seconds)
  - Logs emergency exit (affects streak)
  - Available during the mandatory end break only

### 3. Break Media System
- **Media Types:**
  - Videos: MP4 only
  - Images: JPG, PNG only
- **Media Categories by Mode:**
  - Normal Mode: Surprise effects + motivational quotes + hydration reminders + user uploads
  - Strict Mode: Intense effects + warnings + user uploads
  - Focused Mode: Session-end signals + rest reminders + user uploads
- **Media Storage:**
  ```
  assets/
  ├── media/
  │   ├── normal/
  │   │   ├── defaults/     # Bundled content
  │   │   └── user/         # User uploads
  │   ├── strict/
  │   │   ├── defaults/
  │   │   └── user/
  │   └── focused/
  │       ├── defaults/
  │       └── user/
  ```
- **Media Behavior:**
  - Selection: Random from enabled pool + always include hidden surprise effect
  - Hidden surprise effects: Cannot be disabled, encrypted folder (future enhancement)
  - User uploads: Unlimited, automatically enabled
  - Shuffle: Randomized order, prevent repeats if possible
  - One media per break: No slideshows
- **Default Media:**
  - App comes with default surprise effects (non-negotiable)
  - Fallback "Take a Break" image/video if no media set
  - User won't see surprise effects in settings UI (hidden)

### 4. System Tray Integration
- Runs in background: Not a visible window application
- Tray icon: Always present
- Tray menu:
  - Start new task
  - View active session
  - Quick stats
  - Open settings
  - Exit application
- Notifications: System tray notifications for upcoming breaks

### 5. Audio & Visual Controls
- **Volume Settings:**
  - Surprise effect volume (0-100, default: 80)
  - Alarm volume (0-100, default: 70)
  - Break music volume (0-100, default: 50)
- **Visual Settings:**
  - Surprise effect brightness (0-100, default: 100 - max)
  - Screen brightness boost during surprise effects
- **Timing Settings:**
  - Alarm duration (seconds, default: 5)
  - Image display duration (seconds, default: 5)
- **Audio Events:**
  - Break start: Surprise effect/media with boosted volume
  - Break end: Alarm sound (few seconds, customizable duration)
  - Session end: Notification sound

### 6. Streak System
- **Three Streak Types:**
  - **A. Session Streak** (consecutive sessions completed properly)
    - Increments: Complete session without skipping breaks
    - Maintains: Snoozing allowed (partial credit)
    - Breaks: Skip any break OR use emergency escape hatch
    - Tracks: Current count, best count
  - **B. Perfect Session Streak** (no snoozing/skipping)
    - Increments: Complete session with ALL breaks taken (no snooze, no skip, no emergency exit)
    - Breaks: Any snooze, skip, or emergency escape
    - Tracks: Current count, best count
  - **C. Daily Consistency** (worked at least once per day)
    - Increments: Complete at least 1 session per day
    - Breaks: Miss a day
    - Doesn't care: Break quality (snooze/skip doesn't matter)
    - Note: Emergency exits still count as completed sessions for daily consistency
    - Tracks: Current count, best count
- **Streak Tracking:**
  - work_sessions table stores:
    - breaks_taken (full credit)
    - breaks_snoozed (partial credit)
    - breaks_skipped (no credit)
    - emergency_exits (logs escape hatch usage - breaks perfect streak)
- **Streak Quality Score:**
  - quality_score = breaks_taken / (breaks_taken + breaks_snoozed + breaks_skipped)
  - Emergency exits reduce quality score by 0.2 per exit

### 7. Emergency Escape Hatch System
- **Availability:**
  - Normal Mode: Not available (already flexible with skip option)
  - Strict Mode: Available during breaks and cooldown period
  - Focused Mode: Available during mandatory end break only
- **Activation:**
  - Hidden key combination (default: Ctrl+Alt+Shift+E)
  - Must hold for 3 seconds to confirm (prevents accidental activation)
  - Customizable in settings
- **Visual Feedback:**
  - Progress indicator appears when keys held
  - "Emergency Exit - Hold for 3 seconds" message
  - Countdown: 3... 2... 1... EXIT
- **Consequences:**
  - Logs timestamp and reason in database
  - Breaks perfect session streak
  - Reduces session quality score
  - Tracked in analytics as "emergency_exits" count
  - Maintains daily consistency streak (session still counts as completed)
- **Use Cases:**
  - Genuine emergencies (phone call, urgent situation)
  - System issues or bugs
  - User absolutely must leave
  - Safety valve to prevent frustration

### 8. Analytics & History
- **Session History:**
  - All completed sessions
  - Task name, duration, mode used
  - Break compliance (taken/snoozed/skipped counts)
  - Emergency exit count
  - Session quality score
  - Date/time stamps
- **Visualizations:**
  - Calendar heatmap: Days with completed sessions
  - Session completion rate: Pie chart
  - Time distribution: Bar chart (work hours per day)
  - Break compliance: Line chart over time
  - Mode usage: Distribution chart (Normal vs Strict vs Focused)
  - Streak history: Line graph showing streak progression
  - Emergency exits: Track frequency and patterns
- **Statistics Dashboard:**
  - Total sessions completed
  - Total work time (hours)
  - Average session duration
  - Total breaks taken/snoozed/skipped
  - Total emergency exits
  - Current all streaks
  - Best all-time streaks
  - Most productive day/week
  - Favorite mode
  - Average quality score

### 9. Settings Panel
- **General Settings:**
  - Username
  - Default work mode
  - Enable/disable features
- **Timing Presets by Mode:**
  - **Normal Mode:**
    - Work interval (default: 25 min)
    - Break duration (default: 5 min)
    - Snooze duration (default: 5 min)
  - **Strict Mode:**
    - Work interval (default: 52 min)
    - Break duration (default: 17 min)
    - Cooldown duration (default: 20 min)
  - **Focused Mode:**
    - Minimum break duration (default: 30 min)
    - Break scaling (enable/disable)
- **Audio Settings:**
  - Surprise effect volume
  - Alarm volume
  - Music volume (if break music enabled)
  - Enable/disable break music
- **Visual Settings:**
  - Surprise effect brightness boost
  - Image display duration
- **Media Management:**
  - Grid view: Thumbnails of all user-uploaded media
  - Upload new media: File picker (MP4, JPG, PNG)
  - Delete media: Remove user uploads
  - Preview: Click to preview media
  - Hidden: Surprise effects not visible here
- **Advanced Settings:**
  - Emergency escape hatch key combo (customize)
  - Emergency escape hold duration (1-5 seconds)
  - Enable/disable skip in Normal mode
  - Shuffle media (on/off)
  - Export data (CSV/JSON)
  - Import data (restore from backup)
  - Reset all data (with confirmation)

### 10. Notifications System
- Break incoming: 2-minute warning before break (Normal/Strict modes only)
- Break starting now: Surprise effect triggered
- Break ending soon: 1-minute warning
- Break complete: Alarm sound + notification
- Session complete: End-of-work notification
- Streak milestone: "10-day streak! 🔥"
- Emergency exit: "Emergency exit used - Perfect streak affected"

### 11. Psychological Design Tricks
- **During Normal Mode Breaks:**
  - Buttons stay active (temptation design)
  - Streak counter prominent and growing
  - Confirmation dialog for Skip/Snooze: "Are you sure? Streak will be affected!"
  - Skip button turns redder as timer progresses
  - Visual emphasis on streak as countdown nears end
  - Micro-animations on "Take Break" button (encouraging)
- **General:**
  - Streak achievements with celebratory animations
  - Loss aversion messaging: "Don't break your 12-day streak!"
  - Progress bars for session completion
  - Satisfying completion sounds
  - Emergency exit warning: "This will affect your perfect streak"

### 12. Data Persistence
- **Database (SQLite):**
  - tasks - Task configurations
  - work_sessions - Session records (includes emergency_exits count)
  - breaks - Individual break logs
  - break_media - Media library
  - streaks - Streak counters
  - settings - User preferences (includes escape hatch settings)
- **Local Storage:**
  - Database file: focusbreaker.db
  - Media files: assets/media/
  - Logs: logs/app.log
- **Backup/Export:**
  - Manual export to JSON/CSV
  - Automatic daily backup (optional)
  - Import from previous exports

## 🎯 User Flows

### First-Time Setup:
1. Welcome screen
2. Enter username
3. Brief mode explanation
4. Create first task
5. Choose mode
6. Session starts

### Create New Task Flow:
1. Tray Icon → New Task
2. Step 1: Task Info
   - Task name: [_____]
   - Duration: [_____] minutes
   - [Next]
3. Step 2: Mode Selection
   - [Normal] [Focused] [Strict]
   - (Each with description + escape hatch info for Strict/Focused)
4. Step 3: Break Settings (if not Focused)
   - ○ Auto-calculate (recommended)
   - ○ Manual:
     - Number of breaks: [___]
     - Break duration: [___]
5. [Start Session]

### Active Session Flow (Normal Mode):
Work → (25 min) → Break Trigger
                    ↓
                  Surprise effect plays
                    ↓
                  Break window appears
                    ↓
            [Take Break] [Snooze] [Skip]
                    ↓
            Countdown: 5:00
                    ↓
            (User waits or clicks button)
                    ↓
            Break ends → Alarm plays
                    ↓
            Window closes → Resume work

### Active Session Flow (Strict/Focused with Emergency Exit):
Strict Mode Break or Focused End Break
            ↓
      Full-screen overlay
            ↓
      (User holds Ctrl+Alt+Shift+E)
            ↓
      "Hold for 3 seconds... 2... 1..."
            ↓
      Emergency exit confirmed
            ↓
      Overlay closes
            ↓
      Log event: emergency_exit++
            ↓
      Show notification: "Emergency exit used"

### Session End Flow:
- **Normal/Focused:**
  - Work complete → Notification
  - [Extend] [End Session]
  - If Extend: Add more time, continue breaks
  - If End: Save to history, update streaks
- **Strict:**
  - Work complete → Mandatory cooldown (20 min)
  - Full-screen overlay
  - (Emergency exit available)
  - Cooldown complete → Session saved

## 🔧 Technical Architecture

### Technology Stack:
Core:
- Language: Python 3.10+
- UI Framework: Flet
- Database: SQLite3

System Integration:
- System Tray: pystray
- Audio: pygame.mixer
- Brightness: screen_brightness_control
- Volume: pycaw (Windows) / osascript (macOS)
- Keyboard Hooks: keyboard (for emergency escape)

Visualization (for analytics):
- Charts: Matplotlib / Plotly

Timing:
- Threading: threading

### Project Structure:
```
focusBreaker/
├── docs/
│   └── specification.md
├── pyproject.toml
├── README.md
├── src/
│   ├── assets/
│   │   ├── icon.png
│   │   ├── media/
│   │   └── splash_android.png
│   ├── config.py
│   ├── core/
│   │   ├── escape_hatch.py
│   │   ├── mode_controller.py
│   │   ├── scheduler.py
│   │   ├── session_manager.py
│   │   ├── streak_manager.py
│   │   └── timer.py
│   ├── data/
│   │   ├── db.py
│   │   └── models.py
│   ├── main.py
│   ├── requirements.txt
│   ├── system/
│   │   ├── audio.py
│   │   ├── display.py
│   │   └── input_blocker.py
│   ├── tests/
│   │   └── test_timer.py
│   └── ui/
│       ├── analytics.py
│       ├── break_window.py
│       ├── main_window.py
│       └── settings.py
```

##  Progress Tracker (By Folder)

### ✅ Data Layer (`src/data/`) - COMPLETED FIRST [Dec 2025]
- ✅ Database operations and analytics queries
- ✅ Data models and schemas
- ✅ Package initialization
- ✅ Export/import functionality (JSON backup/restore)

### ✅ Core Logic (`src/core/`) - COMPLETED SECOND [Dec 2025]
- ✅ `escape_hatch.py` - Emergency escape system logic
- ✅ `mode_controller.py` - Work mode management (Normal/Strict/Focused)
- ✅ `scheduler.py` - Break scheduling and timing logic
- ✅ `session_manager.py` - Session lifecycle management
- ✅ `streak_manager.py` - Streak calculation and tracking
- ✅ `timer.py` - Enhanced timer implementation
- ✅ `__init__.py` - Package initialization
- ✅ Comprehensive test suite (16+ tests covering all modules)

### ✅ Configuration Centralization (`src/config.py`) - COMPLETED THIRD [Jan 5, 2026]
- ✅ Centralized all configuration constants and settings
- ✅ Revised all core modules to use config constants instead of hardcoded values
- ✅ Optimized imports from `import config` to specific class imports (e.g., `from config import StreakConfig`)
- ✅ Added missing config constants (STATISTICS_PERIOD_DAYS, HOURS_IN_DAY, etc.)
- ✅ Comprehensive validation rules and configuration classes
- ✅ Added config imports to system modules (audio.py, display.py, input_blocker.py)
- ✅ Updated system modules to use AudioConfig, UIConfig, and EscapeHatchConfig constants

### 🔄 System Integration (`src/system/`) - CURRENTLY WORKING ON [Jan 5, 2026]
- ✅ Audio playback and volume controls (using AudioConfig constants)
- ✅ Screen brightness and overlay controls (using UIConfig constants)
- ✅ Input blocking for strict mode (using EscapeHatchConfig constants)
- Package initialization

### ⏳ User Interface (`src/ui/`) - PENDING
- Analytics dashboard (backend logic complete, UI pending)
- Break notification windows
- Main application interface
- Settings panel

### ⏳ Configuration & Entry (`src/`) - PENDING
- Application configuration
- Application entry point
- Package initialization

### ⏳ Assets (`src/assets/`) - PENDING
- Application icon
- Default media files
- Splash screen

### ✅ Tests (`src/tests/`) - COMPLETED [Jan 5, 2026]
- ✅ Escape hatch tests
- ✅ Mode controller tests
- ✅ Scheduler tests
- ✅ Session manager tests (16 comprehensive tests)
- ✅ Streak manager tests
- ✅ Timer tests (updated)
- ✅ Package initialization

### ⏳ Project Configuration - MOSTLY COMPLETE
- ✅ Project configuration
- ✅ Dependencies
- ✅ Git ignore rules
- ✅ Project documentation
- ✅ This specification
- Data backup/restore
- Advanced statistics
- Customizable themes
- Mobile companion app

## 📝 Implementation Notes

### Development Strategy:
**Actual development sequence followed:**
1. ✅ **Data Layer First**: Started with `src/data/` (db.py, models.py) to establish the foundation
2. ✅ **Core Business Logic Second**: Built all `src/core/` modules with initial hardcoded values
3. ✅ **Configuration Centralization Third**: Created comprehensive `config.py` and revised all core modules to use config constants instead of hardcoded values
4. 🔄 **System Integration Current**: Now working on `src/system/` modules using config variables
5. ⏳ **UI Development Next**: `src/ui/` folder (interface components and analytics dashboard)
6. ⏳ **Final Steps**: Configuration files, main.py entry point, and default assets

**Key architectural decisions:**
- **Bottom-up approach**: Data layer → Business logic → Configuration → System integration → UI
- **Configuration-driven design**: All magic numbers eliminated, everything configurable
- **Test-first development**: Comprehensive test suite built alongside core modules
- **Modular imports**: Optimized from `import config` to specific class imports for performance
- **Centralized configuration**: Single source of truth for all app settings and constants

### Configuration Architecture:
**Development sequence for config centralization:**
1. Built core modules with initial hardcoded values for rapid development
2. Created comprehensive `config.py` with specialized config classes (StreakConfig, TimerConfig, ModeConfig, etc.)
6. Added config imports to system modules and updated them to use config constants
8. Cleaned up requirements.txt by removing unnecessary transitive dependencies
9. All system modules now use config variables for consistency and maintainability

### Current Focus:
- 🔄 **Currently Working On**: `src/system/` folder (audio, display system integration using config variables)
- ✅ **Completed**: `input_blocker.py` - Cross-platform input blocking with evdev for Linux, Quartz for macOS, keyboard/mouse hooks for Windows
- ✅ **Completed**: Config imports added to all system modules (audio.py, display.py, input_blocker.py)
- ✅ **Completed**: Fixed RichTestResult TypeError issues across all test files
- ✅ **Completed**: Cleaned up requirements.txt - removed unnecessary transitive dependencies
- ⏳ **Next**: `src/ui/` folder (interface components and analytics dashboard)
- ⏳ **Finally**: Main entry point and default assets
- ✅ **Completed**: Data layer, core business logic, and configuration centralization

### Testing:
- ✅ Core modules fully tested (16+ comprehensive test cases)
- ✅ System modules tested (input_blocker: 29 comprehensive test cases covering initialization, blocking modes, cross-platform support, timeout mechanisms, escape detection, error handling, and cleanup)
- ✅ Integration testing for system-level features (audio, display controls)
- UI testing for responsiveness and user experience
- Cross-platform compatibility testing
- Emergency exit functionality validation
- Database integrity and crash recovery testing

### Technical Challenges:
- Cross-platform system integration (Windows/macOS/Linux)
- Real-time audio and display control
- Input blocking mechanisms for strict mode
- Performance optimization for media playback
- System tray integration across different desktop environments

## 🎨 Future Enhancements (Post-Launch)
- Themes: Dark mode, custom colors
- Sounds: Custom alarm sounds, more variety
- Social: Share streak achievements
- Cloud sync: Optional data backup
- Mobile companion: View stats on phone
- Integrations: Calendar sync, task apps
- AI suggestions: Optimal break times based on your patterns
- Pomodoro timer mode: Traditional 25/5/25/5/25/5/long break
- Focus music: Binaural beats during work sessions
- Screen dimming: Reduce eye strain during work
- Posture reminders: Webcam-based posture detection
- Emergency exit analytics: Pattern detection ("You use escape every Friday...")
- Customizable escape consequences: User can set their own penalties

## 🔐 Emergency Escape Hatch - Design Philosophy
The escape hatch serves as a safety valve for the strict enforcement systems:
- **Why It's Needed:**
  - Real emergencies happen (fire alarm, urgent call, medical issues)
  - Software bugs shouldn't trap users
  - Prevents user frustration and app abandonment
  - Builds trust: "The app respects my autonomy"
- **Why It Has Consequences:**
  - Prevents casual abuse ("I'll just escape every break")
  - Maintains integrity of streak system
  - Tracks patterns: frequent escapes = user needs to adjust settings
  - Creates accountability
- **Balance:**
  - Easy enough to use in true emergencies (3-second hold)
  - Hard enough to make you think twice (not a single click)
  - Visible consequences (streak notification)
  - But not so punishing that users avoid the app
- **The goal:** Users should feel empowered, not trapped, while still maintaining the discipline structure that makes the app effective.

**Version:** 0.3.0  
**Last Updated:** January 5, 2026  
**Status:** Core Implementation Complete - Configuration Centralized - System Integration In Progress (Config Imports Complete, Test Suite Fixed)