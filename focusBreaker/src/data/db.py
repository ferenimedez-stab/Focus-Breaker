"""
Database Manager- SQLite Operations
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

class DBManager:
    def __init__(self, db_path: str = "focusbreaker.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        return self.conn
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def init_database(self):
        """Initialize all database tables"""
        self.connect()
        cursor = self.conn.cursor()

        # Task table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL,
                       allocated_time_minutes INTEGER NOT NULL,
                       start_time TEXT,
                       end_time TEXT,
                       mode TEXT NOT NULL DEFAULT 'normal',
                       auto_calculate_breaks BOOLEAN NOT NULL DEFAULT 1,
                       num_breaks INTEGER NOT NULL DEFAULT 0,
                       break_duration_minutes INTEGER NOT NULL DEFAULT 5,
                       created_at TEXT NOT NULL
                       )
                """)
        
        # Work Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_sessions (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       task_id INTEGER NOT NULL,
                       start_time TEXT NOT NULL,
                       end_time TEXT,
                       planned_duration_minutes INTEGER NOT NULL,
                       actual_duration_minutes INTEGER,
                       mode TEXT NOT NULL,
                       status TEXT NOT NULL DEFAULT 'in_progress',
                       breaks_taken INTEGER DEFAULT 0,
                       breaks_snoozed INTEGER DEFAULT 0,
                       breaks_skipped INTEGER DEFAULT 0,
                       extended_count INTEGER DEFAULT 0,
                       emergency_exits INTEGER DEFAULT 0,
                       snooze_passes_remaining INTEGER DEFAULT 3,
                       archived BOOLEAN DEFAULT 0,
                       created_at TEXT NOT NULL,
                       FOREIGN KEY (task_id) REFERENCES tasks(id)
                       )
                """)

        # Breaks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS breaks (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       session_id INTEGER NOT NULL,
                       scheduled_time TEXT NOT NULL,
                       actual_time TEXT,
                       duration_minutes INTEGER NOT NULL,
                       status TEXT NOT NULL DEFAULT 'pending',
                       snooze_count INTEGER DEFAULT 0,
                       snooze_duration_minutes INTEGER DEFAULT 0,
                       created_at TEXT NOT NULL,
                       FOREIGN KEY (session_id) REFERENCES work_sessions(id)
                       )
                """)
        
        # Break Media table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS break_media (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       filename TEXT NOT NULL,
                       media_type TEXT NOT NULL CHECK(media_type IN ('image', 'video')),
                       file_path TEXT NOT NULL,
                       duration_seconds INTEGER,
                       mode TEXT NOT NULL CHECK(mode IN ('normal', 'focused', 'strict')),
                       is_jumpscare BOOLEAN NOT NULL DEFAULT 0,
                       enabled BOOLEAN NOT NULL DEFAULT 1,
                       created_at TEXT NOT NULL
                       )
                """)
        
        #Streaks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS streaks (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       streak_type TEXT NOT NULL UNIQUE,
                       current_count INTEGER DEFAULT 0,
                       best_count INTEGER DEFAULT 0,
                       last_updated TEXT NOT NULL,
                       metadata TEXT
                       )
                """)
        
        # Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       media_volume INTEGER DEFAULT 80,
                       alarm_volume INTEGER DEFAULT 70,
                       music_volume INTEGER DEFAULT 50,
                       screen_brightness INTEGER DEFAULT 100,
                       alarm_duration_seconds INTEGER DEFAULT 5,
                       image_display_duration_seconds INTEGER DEFAULT 5,
                       normal_work_interval_minutes INTEGER DEFAULT 25,
                       normal_break_duration_minutes INTEGER DEFAULT 5,
                       normal_snooze_duration_minutes INTEGER DEFAULT 5,
                       strict_work_interval_minutes INTEGER DEFAULT 52,
                       strict_break_duration_minutes INTEGER DEFAULT 17,
                       strict_cooldown_minutes INTEGER DEFAULT 20,
                       focused_mandatory_break_minutes INTEGER DEFAULT 30,
                       max_snooze_passes INTEGER DEFAULT 3,
                       snooze_redistributes_breaks BOOLEAN DEFAULT 1,
                       enable_break_music BOOLEAN DEFAULT 0,
                       shuffle_media BOOLEAN DEFAULT 1,
                       allow_skip_in_normal_mode BOOLEAN DEFAULT 1,
                       created_at TEXT NOT NULL,
                       updated_at TEXT NOT NULL
                       )
                """)
        
        # Indexes for performance
        cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_task
                ON work_sessions(task_id)
                """)
        
        cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_break_session
                ON breaks(session_id)
                """)
        
        cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_created
                ON work_sessions(created_at)
                """)
        
        cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_archived
                ON work_sessions(created_at)
                """)
    
        # Initialise default settings if not exists
        cursor.execute("SELECT COUNT(*) FROM settings")
        if cursor.fetchone()[0] == 0:
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO settings (
                               media_volume, alarm_volume, music_volume,
                               screen_brightness,
                               alarm_duration_seconds, image_display_duration_seconds,
                               normal_work_interval_minutes, normal_break_duration_minutes,
                               normal_snooze_duration_minutes, 
                               strict_work_interval_minutes, strict_break_duration_minutes,
                               strict_cooldown_minutes, focused_mandatory_break_minutes,
                               max_snooze_passes, snooze_redistributes_breaks,
                               enable_break_music, shuffle_media, allow_skip_in_normal_mode,
                               created_at, updated_at
                           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            80, 70, 50,
                            100,
                            5, 5,
                            25, 5, 5,
                            52, 17, 20,
                            30,
                            3, 1,
                            0, 1, 1,
                            now, now
                        ))
            
        streak_types = ["daily_consistency", "session_streak", "perfect_session"]
        for streak_type in streak_types:
            cursor.execute("""
                           INSERT OR IGNORE INTO streaks(
                               streak_type, current_count, best_count,
                               last_updated, metadata
                           ) VALUES (?, ?, ?, ?, ?)
                           """, (
                               streak_type, 0, 0, 
                               datetime.now().isoformat(), "{}"
                        ))
            
        self.conn.commit()
        print("Database initialised successfully!")

# ====================================== TASKS OPERATIONS =====================================
    def createTask(self, task) -> int:
        """Create a new task and return its ID"""
        cursor = self.conn.cursor()
        cursor.execute("""  
                        INSERT INTO tasks (
                            name, allocated_time_minutes, start_time, end_time,
                            mode, auto_calculate_breaks, num_breaks,
                            break_duration_minutes, created_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) 
                    """, (
                        task.name, task.allocated_time_minutes,
                        task.start_time, task.end_time, task.mode, 
                        task.auto_calculate_breaks, task.num_breaks,
                        task.break_duration_minutes, task.created_at
                        ))
        self.conn.commit()
        return cursor.lastrowid

    def getTask(self, task_id: int):
        """Get a task by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if row:
            from data.models import Task
            return Task(**dict(row))
        return None

    def getAllTasks(self, limit: int = 50) -> List:
        """Get all tasks, most recent first"""
        cursor = self.conn.cursor()
        cursor.execute("""
                       SELECT * FROM TASKS
                       ORDER BY created_at DESC
                       LIMIT ?
                       """, (limit))
        from data.models import Task
        return [Task(**dict(row)) for row in cursor.fetchall()]
    
    def updateTask(self, task_id: int, **kwargs):
        """Update task fields"""
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)

        values.append(task_id)
        query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"

        cursor = self.conn.cursor() 
        cursor.execute(query, values)
        self.conn.commit()

    def deleteTask(self, task_id: int):
        """Delete a task"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()

# ================================== WORK SESSIONS OPERATIONS =================================
    def createSession(self, session) -> int:
        """Create a new work session and return its ID"""
        cursor = self.conn.cursor()
        cursor.execute("""  
                        INSERT INTO work_sessions (
                            task_id, start_time, end_time,
                            planned_duration_minutes, actual_duration_minutes,
                            mode, status, breaks_taken, breaks_snoozed,
                            breaks_skipped, extended_count, emergency_exits,
                            created_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 
                    """, (
                        session.task_id, session.start_time,
                        session.end_time, session.planned_duration_minutes,
                        session.actual_duration_minutes, session.mode,
                        session.status, session.breaks_taken,
                        session.breaks_snoozed, session.breaks_skipped,
                        session.extended_count, session.emergency_exits,
                        session.created_at
                        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def getSession(self, session_id: int):
        """Get a work session by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM work_sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()

        if row:
            from data.models import WorkSession
            return WorkSession(**dict(row))
        return None
    
    def getSessionsByTask(self, task_id: int, include_archived: bool = False) -> List:
        """Get all sessions for a specific task"""
        cursor = self.conn.cursor()

        if include_archived:
            cursor.execute("""
                           SELECT * from work_sessions
                           WHERE task_id = ?
                           ORDER BY start_time DESC
                        """, (task_id))
        
        else:
            cursor.execute("""
                           SELECT * from work_sessions
                           WHERE task_id = ? AND archived = 0
                           ORDER BY start_time DESC 
                        """, (task_id))
        
        from data.models import WorkSession
        return [WorkSession(**dict(row)) for row in cursor.fetchall()]
    
    def getActiveSession(self):
        """Get the currently active session"""
        cursor = self.conn.cursor()
        cursor.execute("""
                       SELECT * FROM work_sessions
                       WHERE status = 'in_progress'
                       ORDER BY start_time DESC
                       LIMIT 1
                    """)
        
        row = cursor.fetchone()
        if row:
            from data.models import WorkSession
            return WorkSession(**dict(row))
        return None
    
    def getRecentSessions(self, limit: int = 20, include_archived: bool = False) -> List:
        """Get recent sessions"""
        cursor = self.conn.cursor()

        if include_archived:
            cursor.execute("""
                           SELECT * FROM work_sessions
                           ORDER BY start_time DESC
                           LIMIT ?
                        """, (limit))
        
        else:
            cursor.execute("""
                           SELECT * FROM work_sessions
                           WHERE archived = 0
                           ORDER BY start_time DESC
                           LIMIT ?
                        """, (limit))
        
        from data.models import WorkSession
        return [WorkSession(**dict(row)) for row in cursor.fetchall()]
    
    def updateSession(self, session_id: int, **kwargs):
        fields = []
        values = []

        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)
        
        values.append(session_id)
        query = f"UPDATE work_sessions SET {', '.join(fields)} WHERE id = ?"

        cursor = self.conn.cursor()
        cursor.execute(query, values)
        self.conn.commit()

    def archiveSession(self, session_id: int):
        """Archive a session"""
        self.updateSession(session_id, archived = 1)

    def restoreSession(self, session_id: int):
        """Restore an archived session"""
        self.updateSession(session_id, archived = 0)
    
    def getArchivedSessions(self, limit: int = 50) -> List:
        """Get all archived sessions"""        
        cursor = self.conn.cursor()
        cursor.execute("""
                       SELECT * FROM work_sessions
                       WHERE archived = 1
                       ORDER BY created_at DESC
                       LIMIT ?
                    """, (limit))
        
        from data.models import WorkSession
        return [WorkSession(**dict(row)) for row in cursor.fetchall()]
    
    def permanentlyDeleteSession(self, session_id: int):
        """ Permanent deletion of session"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM breaks WHERE session_id = ? ", (session_id,))
        cursor.execute("DELETE FROM work_sessions WHERE id = ? ", (session_id,))
        self.conn.commit()

# ====================================== BREAK OPERATIONS =====================================
    def createBreak(self, break_obj) -> int:
        """Create a new break and return its ID"""
        cursor = self.conn.cursor()
        cursor.execute("""
                       INSERT INTO breaks (
                            session_id, scheduled_time, actual_time, duration_minutes,
                            status, snooze_count, snooze_duration_minutes, created_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        break_obj.session_id, break_obj.scheduled_time, 
                        break_obj.actual_time, break_obj.duration_minutes,
                        break_obj.status, break_obj.snooze_count, 
                        break_obj.snooze_duration_minutes, break_obj.created_at
                    ))
        self.conn.commit()
        return cursor.lastrowid
    
    def getBreak(self, break_id: int):
        """Get a break by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * from breaks WHERE id = ?", (break_id,))

        row = cursor.fetchone()
        if row:
            from data.models import Break
            return Break(**dict(row))
        return None
    
    def getSessionBreaks(self, session_id: int) -> List:
        """Get all breaks for a session"""
        cursor = self.conn.cursor()
        cursor.execute("""
                       SELECT * FROM breaks
                       WHERE session_id = ?
                       ORDER by scheduled_time
                    """, (session_id))
        
        from data.models import Break
        return [Break(**dict(row)) for row in cursor.fetchall()]

    def getNextPendingBreak(self, session_id: int):
        """Get the next pending break for a session"""
        cursor = self.conn.cursor()
        cursor.execute("""
                       SELECT * FROM breaks
                       WHERE session_id = ? AND status = 'pending'
                       ORDER BY scheduled_time
                       LIMIT 1
                    """, (session_id))
        
        row = cursor.fetchone()
        if row:
            from data.models import Break
            return Break(**dict(row))
        return None
    
    def getPendingBreaks(self, session_id: int) -> List:
        """Get all pending breaks for a session"""
        cursor = self.conn.cursor()
        cursor.execute("""
                       SELECT * FROM breaks
                       WHERE session_id = ? AND status = 'pending'
                       ORDER BY scheduled_time
                    """, (session_id))
        
        from data.models import Break
        return [Break(**dict(row)) for row in cursor.fetchall()]

    def updateBreak(self, break_id: int, **kwargs):
        """Update break fields"""
        fields = []
        values = []

        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)

        values.append(break_id)
        query = f"UPDATE breaks SET {', '.join(fields)} WHERE id = ?"

        cursor = self.conn.cursor()
        cursor.execute(query, values)
        self.conn.commit()

    def scheduleBreaksForSessions(self, session_id: int, mode: str, work_duration_minutes: int) -> List[int]:
        """Schedule breaks for a session base on mode and duration; returns list of break IDs"""
        settings = self.getSettings()
        session = self.getSession(session_id)
        start_time = datetime.fromisoformat(session.start_time)

        # Get mode-specific intervals
        if mode == 'normal':
            work_interval = settings.normal_work_interval_minutes
            break_duration = settings.normal_break_duration_minutes
        
        elif mode == 'strict':
            work_interval = settings.strict_work_interval_minutes
            break_duration = settings.strict_break_duration_minutes
        
        elif mode == 'focused':
            return []
        
        else: 
            work_interval = 25
            break_duration = 5
        
        # Calculate number of breaks
        num_breaks = work_duration_minutes // work_interval

        # Schedule breaks
        break_ids = []
        for i in range(num_breaks):
            break_time = start_time + timedelta(minutes = (i + 1) * work_interval)

            from data.models import Break
            break_obj = Break(id = None,
                              session_id = session_id,
                              scheduled_time = break_time.isoformat(),
                              actual_time = None,
                              duration_minutes = break_duration,
                              status = 'pending',
                              snooze_count = 0,
                              snooze_duration_minutes = 0,
                              created_at = datetime.now().isoformat())
            
            break_id = self.createBreak(break_obj)
            break_ids.append(break_id)
        
        return break_ids

# =================================== BREAK MEDIA OPERATIONS ==================================
    def createBreakMedia(self, media) -> int:
        """Add new media to library"""
        cursor = self.conn.cursor()
        cursor.execute("""
                       INSERT INTO break_media (
                       filename, media_type, file_path, duration_seconds,
                       mode, is_jumpscare, enabled, created_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                         media.filename, media.media_type, media.file_path,
                         media.duration_seconds, media.mode, media.is_jumpscare, 
                         media.enabled, media.created_at
                      ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def getMedia(self, media_id: int):
        """Get media by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM break_media WHERE id = ?", (media_id,))

        row = cursor.fetchone()
        if row:
            from data.models import BreakMedia
            return BreakMedia(**dict(row))
        return None
    
    def getAllMedia(self, mode: str = None, include_jumpscares: bool = False) -> List:
        """ Get all media, optionally filtered by mode"""
        cursor = self.conn.cursor()

        if mode:
            if include_jumpscares:
                cursor.execute("""
                               SELECT * FROM break_media
                               WHERE mode = ? AND enabled = 1
                               ORDER BY created_at DESC
                            """, (mode))
            
            else:
                cursor.execute("""
                               SELECT * FROM break_media
                               WHERE mode = ? AND enabled = 1 AND is_jumpscare = 0
                               ORDER BY created_at DESC
                            """, (mode))
        
        else:
            if include_jumpscares:
                cursor.execute("""
                               SELECT * FROM break_media
                               WHERE enabled = 1
                               ORDER BY created_at DESC
                            """)
            
            else:
                cursor.execute("""
                               SELECT * FROM break_media
                               WHERE enabled = 1 AND is_jumpscare = 0
                               ORDER BY created_at DESC
                            """)
        
        from data.models import BreakMedia
        return [BreakMedia(**dict(row)) for row in cursor.fetchall()]
    
    def getRandomMedia(self, mode: str):
        """Get random media for break"""
        import random
        cursor = self.conn.cursor()

        # Get user media
        cursor.execute("""
                       SELECT * FROM break_media
                       WHERE mode = ? AND enabled = 1 and is_jumpscare = 0
                    """, (mode))
        
        user_media = [dict(row) for row in cursor.fetchall()]

        # Get a random jumpscare
        cursor.execute("""
                       SELECT * FROM break_media
                       WHERE mode = ? AND is_jumpscare = 1
                       ORDER BY RANDOM()
                       LIMIT 1
                    """, (mode))
        
        jumpscare_row = cursor.fetchone()

        # Combine
        all_media = user_media
        if jumpscare_row:
            all_media.append(dict(jumpscare_row))

        if not all_media:
            return None
        
        # Pick one randomly
        from data.models import BreakMedia
        selected = random.choice(all_media)
        return BreakMedia(**selected)
    
    def updateMedia(self, media_id: int, **kwargs):
        """Update media fields"""
        fields = []
        values = []

        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)

        values.append(media_id)
        query = f"UPDATE break_media SET {', '.join(fields)} WHERE id = ?"

        cursor = self.conn.cursor()
        cursor.execute(query, values)
        self.conn.commit()

    def deleteMedia(self, media_id: int):
        """Delete media from library"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM break_media WHERE id = ?", (media_id,))
        self.conn.commit()

    def toggleMedia(self, media_id: int, enabled: bool):
        """Enable/disabled media"""
        self.updateMedia(media_id, enabled = 1 if enabled else 0)

# ===================================== STREAK OPERATIONS ====================================
    def getStreak(self, streak_type: str):
        """Get a streak by type"""
        cursor = self.conn.cursor()
        cursor.execute("""
                       SELECT * FROM streaks WHERE streak_type = ?
                    """, (streak_type,))
        
        row = cursor.fetchone()
        if row:
            from data.models import Streak
            return Streak(**dict(row))
        return None
    
    def updateStreak(self, streak_type: str, current_count: int,
                     best_count: int, metadata: Dict[str, Any] = None):
        """Update a streak"""
        cursor = self.conn.cursor()
        cursor.execute("""
                       UPDATE streaks 
                       SET current_count = ?, best_count = ?,
                           last_updated = ?, metadata = ? 
                       WHERE streak_type = ?
                    """, (
                        current_count, best_count, datetime.now().isoformat(),
                        json.dumps(metadata or {}), streak_type
                    ))
        
        self.conn.commit()
    
    def getAllStreaks(self) -> List:
        """Get all streaks"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM streaks")

        from data.models import Streak
        return [Streak(**dict(row)) for row in cursor.fetchall()]
    
    def resetStreak(self, streak_type: str):
        """Reset a streak to 0"""
        self.updateStreak(streak_type, 0, self.getStreak(streak_type).best_count)

    def incrementStreak(self, streak_type: str):
        """Increment a streak by 1"""
        streak = self.getStreak(streak_type)
        new_count = streak.current_count + 1
        new_best = max(streak.best_count, new_count)
        
        self.updateStreak(streak_type, new_count, new_best)

# ===================================== SNOOZE OPERATIONS ====================================
    def useSnoozePass(self, session_id: int) -> bool:
        """Use one snooze pass; returns True if pass was available, otherwise False"""
        session = self.getSession(session_id)
        if not session:
            return False
        
        if session.snooze_passes_remaining > 0:
            self.updateSession(session_id,
                               snooze_passes_remaining = session.snooze_passes_remaining - 1,
                               breaks_snoozed = session.breaks_snoozed + 1)
            return True
        
        return False
    
    def getSnoozePassesRemaining(self, session_id: int) -> int:
        """Get remaining snooze passes for a session"""
        session = self.getSession(session_id)
        return session.snooze_passes_remaining if session else 0
    
    def canSnooze(self, session_id: int) -> bool:
        """Check if user can snooze (has remaining passes)"""
        return self.getSnoozePassesRemaining(session_id) > 0
    
    def redistributeRemainingBreaks(self, session_id: int):
        """After a snooze, redistribute remaining breaks"""
        session = self.getSession(session_id)
        if not session:
            return False
        
        # Get all pending breaks (including the snoozed one)
        pending_breaks = self.getPendingBreaks(session_id)
        if len(pending_breaks) == 0:
            return
        
        start_time = datetime.fromisoformat(session.start_time)
        now = datetime.now()
        elapsed_minutes = (now - start_time).total_seconds() / 60
        remaining_minutes = session.planned_duration_minutes - elapsed_minutes

        if remaining_minutes <= 0:
            return
        
        # Calculate new interval between breaks
        num_breaks = len(pending_breaks)
        interval = remaining_minutes / (num_breaks + 1)
        
        # Redistribute breaks evenly
        current_time = now
        for break_obj in pending_breaks:
            current_time = current_time + timedelta(minutes = interval)
            self.updateBreak(break_obj.id,
                             scheduled_time = current_time.isoformat(),
                             status = 'pending')
    
    def snoozeBreak(self, break_id: int, session_id: int, snooze_duration_minutes: int = None):
        """Snooze a break: delays and redistributes remaining breaks if enabled"""
        # Get settings for snooze duration
        settings = self.getSettings()
        if snooze_duration_minutes is None:
            snooze_duration_minutes = settings.normal_break_duration_minutes

        # Check if user has snooze passes
        if not self.canSnooze(session_id):
            return False
        
        # Use a snooze pass
        if not self.useSnoozePass(session_id):
            return False
        
        # Get break
        break_obj = self.getBreak(break_id)
        if not break_obj:
            return False
        
        # Delay break
        scheduled_time = datetime.fromisoformat(break_obj.scheduled_time)
        new_scheduled_time = scheduled_time + timedelta(minutes = snooze_duration_minutes)

        self.updateBreak(break_id,
                         scheduled_time = new_scheduled_time,
                         snooze_count = break_obj.snooze_count + 1,
                         snooze_duration_minutes = break_obj.snooze_duration_minutes + snooze_duration_minutes,
                         status = "snoozed")
        
        # Redistribute remaining breaks if enabled
        if settings.snooze_redistributes_breaks:
            self.redistributeRemainingBreaks(session_id)

        return True

    def resetSnoozePasses(self, session_id: int):
        """Reset snooze passes to maximum (for extending sessions)"""
        settings = self.getSettings()
        self.updateSession(session_id,
                           snooze_passes_remaining = settings.max_snooze_passes)
                           

# ==================================== SETTINGS OPERATIONS ===================================
    def getSettings(self):
        """Get application settings"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM settings LIMIT 1")

        row = cursor.fetchone()
        if row:
            from data.models import Settings
            return Settings(**dict(row))
        return None
    
    def updateSettings(self, **kwargs):
        """Update application settings"""
        fields = []
        values = []

        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)

        fields.append("updated_at = ?")
        values.append(datetime.now().isoformat())

        query = f"UPDATE settings SET {', '.join(fields)} WHERE id = 1"

        cursor = self.conn.cursor()
        cursor.execute(query, values)
        self.conn.commit()

# =================================== ANALYTICS OPERATIONS ===================================
    def getSessionStats(self, days: int = 30) -> Dict[str, Any]:
        """Get session statistics for the past N days"""
        cutoff_date = (datetime.now() - timedelta(days = days)).isoformat()
        
        cursor = self.conn.cursor()    
        cursor.execute("""
                       SELECT 
                            COUNT(*) as total_sessions,
                            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_sessions,
                            SUM(actual_duration_minutes) as total_minutes,
                            AVG(actual_duration_minutes) as avg_duration,
                            SUM(breaks_taken) as total_breaks_taken,
                            SUM(breaks_snoozed) as total_breaks_snoozed,
                            SUM(breaks_skipped) as total_breaks_skipped,
                            SUM(emergency_exits) as total_emergency_exits
                       FROM work_sessions
                       WHERE created_at >= ?
                    """, (cutoff_date))
        
        row = cursor.fetchone()
        return dict(row) if row else {}
    
    def getDailyActivity(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily activity breakdown"""
        cutoff_date = (datetime.now() - timedelta(days = days)).isoformat()

        cursor = self.conn.cursor()
        cursor.execute("""
                       SELECT
                            DATE(created_at) as date,
                            COUNT(*) as sessions,
                            SUM(actual_duration_minutes) as minutes_worked,
                            SUM(breaks_taken) as breaks_taken
                       FROM work_sessions
                       WHERE created_at >= ? and status = 'completed'
                       GROUP BY DATE(created_at)
                       ORDER BY date DESC
                    """, (cutoff_date))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def getBreakComplianceRate(self, days: int = 30) -> float:
        """Calculate break compliance rate (percentage of breaks taken)"""
        cutoff_date = (datetime.now() - timedelta(days = days)).isoformat()

        cursor = self.conn.cursor()
        cursor.execute("""
                       SELECT
                            SUM(breaks_taken) as taken,
                            SUM(breaks_snoozed) as snoozed,
                            SUM(breaks_skipped) as skipped
                       FROM work_sessions
                       WHERE created_at >= ?
                    """, (cutoff_date))
        
        row = cursor.fetchone()
        if row:
            taken = row['taken'] or 0
            snoozed = row['snoozed'] or 0
            skipped = row['skipped'] or 0
            total = taken + snoozed + skipped

            if total == 0:
                return 0.0
            
            return ((taken + snoozed) / total) * 100
        
        return 0.0
        
    def getModeDistribution(self, include_archived: bool = False) -> Dict[str, int]:
        """Get distribution of work modes used"""
        archived_filter = "" if include_archived else "WHERE archived = 0"
        cursor = self.conn.cursor()
        cursor.execute(f"""
                       SELECT mode, COUNT(*) as count
                       FROM work_sessions
                       {archived_filter}
                       GROUP BY mode
                    """)
        
        return {row['mode']: row['count'] for row in cursor.fetchall()}
    
    def getQualityScores(self, days: int = 30, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Get quality scores for recent sessions"""
        cutoff_date = (datetime.now() - timedelta(days = days)).isoformat()
        archived_filter = "" if include_archived else "AND archived = 0"
        
        cursor = self.conn.cursor()
        cursor.execute(f"""
                       SELECT
                            id,
                            mode,
                            DATE(created_at) as date,
                            breaks_taken,
                            breaks_snoozed,
                            breaks_skipped,
                            emergency_exits,
                            snooze_passes_remaining,
                            CASE
                                WHEN (breaks_taken + breaks_snoozed + breaks_skipped) = 0
                                THEN 1.0
                                ELSE CAST(breaks_taken AS FLOAT) / 
                                    (breaks_taken + breaks_snoozed + breaks_skipped)
                            END as break_quality_score,
                            CASE 
                                WHEN mode = 'focused' THEN 1.0
                                ELSE (CAST(snooze_passes_remaining AS FLOAT) / 
                                            (SELECT max_snooze_passes FROM settings LIMIT 1))
                            END AS snooze_discipline_score
                       FROM work_sessions
                       WHERE created_at >= ? AND status = 'completed' {archived_filter}
                       ORDER BY created_at DESC
                    """, (cutoff_date))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def getTotalWorkTime(self, include_archived: bool = False) -> int:
        """Get total work time in minutes (all time)"""
        archived_filter = "" if include_archived else "AND archived = 0"
        
        cursor = self.conn.cursor()
        cursor.execute(f"""
                       SELECT SUM(actual_duration_minutes) as total
                       FROM work_sessions
                       WHERE status = 'completed' {archived_filter}
                    """)
        
        row = cursor.fetchone()
        return row['total'] if row and row['total'] else 0
    
    def getMostProductiveDay(self, include_archived: bool = False) -> Optional[str]:
        """Get the day with most work done"""
        archived_filter = "" if include_archived else "AND archived = 0"
        
        cursor = self.conn.cursor()
        cursor.execute(f"""
                       SELECT DATE(created_at) as date, SUM(actual_duration_minutes) as total
                       FROM work_sessions
                       WHERE status = 'completed' {archived_filter}
                       GROUP BY DATE(created_at)
                       ORDER BY total DESC
                       LIMIT 1
                    """)
        
        row = cursor.fetchone()
        return row['date'] if row else None
    
    def getSnoozePassUsageStats(self, days: int = 30, include_archived: bool = False) -> Dict[str, Any]:
        """Get pass usage statistics"""
        cutoff_date = (datetime.now() - timedelta(days = days)).isoformat()
        archived_filter = "" if include_archived else "AND archived = 0"
        
        cursor = self.conn.cursor()
        cursor.execute(f"""
                       SELECT
                            COUNT(*) as total_sessions,
                            AVG(CAST(breaks_snoozed AS FLOAT)) as avg_snoozes_per_session,
                            SUM(breaks_snoozed) as total_snoozes,
                            COUNT(CASE WHEN breaks_snoozed = 0 THEN 1 END) as sessions_without_snooze,
                            COUNT(CASE WHEN breaks_snoozed > 0 THEN 1 END) as sessions_with_snooze
                       FROM work_sessions
                       WHERE created_at >= ? AND status = 'completed' {archived_filter}
                    """, (cutoff_date))
        
        row = cursor.fetchone()
        return dict(row) if row else {}

    def getSnoozePassExhaustionRate(self, days: int = 30, include_archived: bool = False) -> float:
        """Calculate how often users exhaust all snooze passes; 
        returns percentage of sessions where all snooze passes were used"""

        cutoff_date = (datetime.now() - timedelta(days = days)).isoformat()
        archived_filter = "" if include_archived else "AND archived = 0"
        
        cursor = self.conn.cursor()
        cursor.execute(f"""
                       SELECT
                            COUNT(*) as total_sessions,
                            COUNT(CASE WHEN snooze_passes_remaining = 0 THEN 1 END) as exhausted_sessions
                       FROM work_sessions
                       WHERE created_at >= ? AND status = 'completed' {archived_filter}
                    """, (cutoff_date))
        
        row = cursor.fetchone()
        if row and row['total_sessions'] > 0:
            return (row['exhausted_sessions'] / row['total_sessions']) * 100
        return 0.0
    
    def getAvgSnoozePassesRemaining(self, days: int = 30, include_archived: bool = False) -> float:
        """Average snooze passes left at end of sessions"""
        cutoff_date = (datetime.now() - timedelta(days = days)).isoformat()
        archived_filter = "" if include_archived else "AND archived = 0"
        
        cursor = self.conn.cursor()
        cursor.execute(f"""
                       SELECT AVG(CAST(snooze_passes_remaining AS FLOAT)) as avg_remaining
                       FROM work_sessions
                       WHERE created_at >= ? AND status = 'completed' {archived_filter}
                    """, (cutoff_date))
        
        row = cursor.fetchone()
        return row['avg_remaining'] if row and row['avg_remaining'] else 0.0
    
    def getModeSnoozeComparison(self, include_archived: bool = False) -> Dict[str, Dict]:
        """Compare snooze usage across different modes"""
        archived_filter = "" if include_archived else "WHERE archived = 0"
        
        cursor = self.conn.cursor()
        cursor.execute(f"""
                       SELECT
                            mode,
                            COUNT(*) as sessions,
                            AVG(CAST(breaks_snoozed AS FLOAT)) as avg_snoozes,
                            AVG(CAST(snooze_passes_remaining AS FLOAT)) as avg_passes_left
                       FROM work_sessions
                       {archived_filter}
                       GROUP BY mode
                       """)
        
        results = {}
        for row in cursor.fetchall():
            results[row['mode']] = {'sessions': row['sessions'],
                                    'avg_snoozes': row['avg_snoozes'],
                                    'avg_passes_left': row['avg_passes_left']}
        
        return results