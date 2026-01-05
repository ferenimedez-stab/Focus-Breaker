# Focus Breaker App [Core Implementation Complete]

This is a personal project I am developing to remind me to take breaks and help me not lose track of time.

FocusBreaker is a customizable productivity timer app built with Python and Flet. Inspired by the Pomodoro technique, it aims to help its user stay in track of the time they spend working by scheduling automated breaks, tracking streaks, and offering different modes (normal, strict, focused) to prevent burnout.

**Current Status**: Core business logic and comprehensive test suite fully implemented. System integration and UI development next.

**Development Approach**: Started with data layer (db/models), then core business logic modules, then centralized configuration in config.py and revised core modules to use config constants, now working on system modules using config variables.

## Features

- **Task Management**: Create tasks with names, durations, and work modes.
- **Three Work Modes**:
  - **Normal Mode**: Flexible with 25-minute work intervals and 5-minute breaks. Includes snooze/skip options.
  - **Strict Mode**: Enforced with 52-minute work intervals, 17-minute breaks, and mandatory cooldowns. Full-screen overlays.
  - **Focused Mode**: Deep work with no breaks until the end, followed by mandatory breaks.
- **Break Media System**: Randomized media playback (videos/images) during breaks, including default media and user uploads.
- **Streak System**: Track session streaks, perfect sessions, and daily consistency with quality scores.
- **Emergency Escape Hatch**: Hidden key combo for emergencies in strict/focused modes (with consequences).
- **Analytics & History**: Session history, visualizations (charts/heatmaps), and statistics dashboard.
- **System Tray Integration**: Background operation with tray menu for quick access.
- **Settings Panel**: Customize timings, audio/visual controls, media management, and advanced options.

## Installation

### Prerequisites
- Python 3.8+
- [uv](https://github.com/astral-sh/uv) (for dependency management)

### Setup
1. Clone the repository:
   ```
   git clone https://github.com/ferenimedez-stab/Focus-Breaker.git
   cd Focus-Breaker
   ```

2. Install dependencies:
   ```
   uv sync
   ```

## Usage

### Run as Desktop App
```
uv run flet run
```

### Run as Web App
```
uv run flet run --web
```

- Start a timer, select a mode, and let FocusBreaker guide your productivity sessions.
- Customize settings via the UI for intervals, media, and notifications.

## Building

### Android APK
```
flet build apk -v
```

### iOS IPA
```
flet build ipa -v
```

### macOS App
```
flet build macos -v
```

### Linux Package
```
flet build linux -v
```

### Windows EXE
```
flet build windows -v
```

For detailed build instructions, see the [Flet Documentation](https://docs.flet.dev/).

## Project Structure

```
focusBreaker/
├── docs/
│   └── specification.md          # Complete feature spec and progress tracking
├── pyproject.toml                # Project configuration and dependencies
├── README.md                     # This file - project overview and setup
├── src/
│   ├── assets/                   # Media files and app assets (pending)
│   │   ├── icon.png
│   │   ├── media/
│   │   └── splash_android.png
│   ├── config.py                 # ✅ COMPLETED - Centralized configuration settings
│   ├── core/                     # ✅ COMPLETED - Core business logic
│   │   ├── __init__.py
│   │   ├── escape_hatch.py       # Emergency exit system
│   │   ├── mode_controller.py    # Work mode management
│   │   ├── scheduler.py          # Break scheduling logic
│   │   ├── session_manager.py    # Session lifecycle management
│   │   ├── streak_manager.py     # Streak calculations and tracking
│   │   └── timer.py              # Enhanced timer implementation
│   ├── data/                     # ✅ COMPLETED - Data layer
│   │   ├── __init__.py
│   │   ├── db.py                 # Database operations and analytics
│   │   └── models.py             # Data models and schemas
│   ├── main.py                   # Application entry point (pending)
│   ├── requirements.txt          # Python dependencies
│   ├── system/                   # 🔄 NEXT UP - System integrations
│   │   ├── audio.py              # Audio playback and controls
│   │   ├── display.py            # Screen brightness and overlays
│   │   └── input_blocker.py      # Input blocking for strict mode
│   ├── tests/                    # ✅ MOSTLY COMPLETE - Test suite
│   │   ├── __init__.py
│   │   ├── test_escape_hatch.py
│   │   ├── test_mode_controller.py
│   │   ├── test_scheduler.py
│   │   ├── test_session_manager.py  # 16 comprehensive tests
│   │   ├── test_streak_manager.py
│   │   └── test_timer.py
│   └── ui/                       # ⏳ PENDING - User interface
│       ├── analytics.py          # Analytics dashboard (backend ready)
│       ├── break_window.py       # Break notification windows
│       ├── main_window.py        # Main application window
│       └── settings.py           # Settings panel
```

## Specification

For the complete feature plan, technical details, and current progress tracking, see [docs/specification.md](docs/specification.md).

## 📊 Progress Tracker 

### ✅ Data Layer (`src/data/`) - COMPLETED FIRST [Dec 2025]
- ✅ Database operations and analytics queries
- ✅ Data models and schemas
- ✅ Package initialization
- ✅ Export/import functionality (JSON backup/restore)

### ✅ Core Logic (`src/core/`) - COMPLETED SECOND [Dec 2025]
- ✅ `escape_hatch.py` - Emergency escape system
- ✅ `mode_controller.py` - Work mode management
- ✅ `scheduler.py` - Break scheduling logic
- ✅ `session_manager.py` - Session lifecycle management
- ✅ `streak_manager.py` - Streak calculations and tracking
- ✅ `timer.py` - Enhanced timer implementation
- ✅ `__init__.py` - Package initialization
- ✅ Comprehensive test suite (16+ tests covering all modules)

### ✅ Configuration Centralization (`src/config.py`) - COMPLETED THIRD [Jan 5, 2026]
- ✅ Centralized all configuration constants and settings
- ✅ Revised all core modules to use config constants instead of hardcoded values
- ✅ Added config imports to system modules (audio.py, display.py, input_blocker.py)
- ✅ Updated system modules to use AudioConfig, UIConfig, and EscapeHatchConfig constants
- ✅ Replaced hardcoded values with configurable constants throughout system integration

### 🔄 System Integration (`src/system/`) - CURRENTLY WORKING ON [Jan 5, 2026]
- ✅ Audio playback and volume controls (using AudioConfig constants)
- ✅ Screen brightness and overlay controls (using UIConfig constants) 
- ✅ Input blocking for strict mode (using EscapeHatchConfig constants)
- Package initialization

### ⏳ User Interface (`src/ui/`) - PENDING
- Analytics dashboard (backend logic complete)
- Break notification windows
- Main application interface
- Settings panel

### ⏳ Configuration & Entry (`src/`) - MOSTLY COMPLETE
- ✅ Application configuration (centralized in config.py)
- Application entry point
- Package initialization

### ⏳ Assets (`src/assets/`) - PENDING
- Application icon
- Default media files
- Splash screen

### ⏳ Tests (`src/tests/`) - MOSTLY COMPLETE
- ✅ Escape hatch tests
- ✅ Mode controller tests
- ✅ Scheduler tests
- ✅ Session manager tests (16 comprehensive tests)
- ✅ Streak manager tests
- ✅ Timer tests (updated)
- ✅ Package initialization
- ✅ Config tests (added for validation rules)
- ✅ Used rich library for enhanced CLI test output with progress bars, colored results, and formatted summaries

### ⏳ Project Configuration - MOSTLY COMPLETE
- ✅ Project configuration
- ✅ Dependencies
- ✅ Git ignore rules
- ✅ Project documentation

---

**Version:** 0.3.0  
**Last Updated:** January 5, 2026  
**Status:** Core Implementation Complete - Configuration Centralized - System Integration In Progress - Test Suite Fixed