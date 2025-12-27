# Focus Breaker App [Under Development]

This is This is a personal project I am developing to remind me to take breaks and help me not lose track of time.

FocusBreaker is a customizable productivity timer app built with Python and Flet. Inspired by the Pomodoro technique, it aims to help its user stay in track of the time they spend working by scheduling automated breaks, tracking streaks, and offering different modes (normal, strict, focused) to prevent burnout.

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
│   └── specification.md  # Complete feature spec and technical details
├── pyproject.toml        # Project configuration and dependencies
├── README.md             # This file - project overview and setup
├── src/
│   ├── assets/
│   │   ├── icon.png      # App icon
│   │   ├── media/        # Media files for breaks
│   │   └── splash_android.png  # Android splash screen
│   ├── config.py         # Configuration settings
│   ├── core/
│   │   ├── escape_hatch.py     # Emergency exit system
│   │   ├── mode_controller.py  # Work mode logic
│   │   ├── scheduler.py        # Break scheduling
│   │   ├── session_manager.py  # Session handling
│   │   ├── streak_manager.py   # Streak calculations
│   │   └── timer.py            # Timer implementation
│   ├── data/
│   │   ├── db.py         # Database operations
│   │   └── models.py     # Data models
│   ├── main.py           # Application entry point
│   ├── requirements.txt  # Python dependencies
│   ├── system/
│   │   ├── audio.py      # Audio control
│   │   ├── display.py    # Display/screen management
│   │   └── input_blocker.py  # Input blocking for strict mode
│   ├── tests/
│   │   └── test_timer.py # Timer unit tests
│   └── ui/
│       ├── analytics.py  # Analytics dashboard
│       ├── break_window.py    # Break pop-up windows
│       ├── main_window.py     # Main application window
│       └── settings.py        # Settings panel
```

## Specification

For the complete feature plan and technical details, see [docs/specification.md](docs/specification.md).

## Development Roadmap

- **Phase 1: MVP** (Core Functionality) - ✅ Database schema & models completed
- **Phase 2: Mode Implementation** - Normal, Strict, Focused modes with escape hatch
- **Phase 3: Media System** - Upload, randomization, image/video integration
- **Phase 4: Streak & Analytics** - Tracking, dashboard, visualizations
- **Phase 5: Polish & UX** - Animations, notifications, onboarding
- **Phase 6: Advanced Features** - Music player, backups, themes

---

**Version:** 0.1.0  
**Last Updated:** December 27, 2024  
**Status:** Under Development