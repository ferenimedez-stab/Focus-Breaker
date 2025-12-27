"""
Data Models - Dataclasses and Enums
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

class WorkMode(Enum):
    NORMAL = "normal"
    STRICT = "strict"
    FOCUSED = "focused"

class SessionStatus(Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    EXTENDED = "extended"

class BreakStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    SNOOZED = "snoozed"
    SKIPPED = "skipped"

@dataclass
class Task:
    id: Optional[str]
    name: str
    allocated_time_minutes: int
    start_time: Optional[str]
    end_time: Optional[str]
    mode: str
    auto_calculate_breaks: bool
    num_breaks: int
    break_duration_minutes: int
    created_at: str

    def to_dict(self):
        return asdict(self)

@dataclass
class WorkSession:
    id: Optional[str]
    task_id: int
    start_time: str
    end_time: Optional[str]
    planned_duration_minutes: int
    actual_duration_minutes: Optional[int]
    mode: str
    status: str
    breaks_taken: int
    breaks_snoozed: int
    breaks_skipped: int
    extended_count: int
    emergency_exits: int
    snooze_passes_remaining: int
    archived: bool
    created_at: str

    def to_dict(self):
        return asdict(self)

@dataclass
class Break:
    id: Optional[int]
    session_id: int
    scheduled_time: str
    actual_time: Optional[str]
    duration_minutes: int
    status: str
    snooze_count: int
    snooze_duration_minutes: int
    created_at: str

    def to_dict(self):
        return asdict(self)
    
@dataclass
class BreakMedia:
    id: Optional[int]
    filename: str
    media_type: str
    file_path: str
    duration_seconds: Optional[int]
    mode: str
    is_jumpscare: bool
    enabled: bool
    created_at: str

    def to_dict(self):
        return asdict(self)

@dataclass
class Streak:
    id: Optional[int]
    streak_type: str 
    current_count: int
    best_count: int
    last_updated: str
    metadata: str

    def to_dict(self):
        return asdict(self)

@dataclass
class Settings:
    id: Optional[int]

    media_volume: int
    alarm_volume: int
    music_volume: int

    screen_brightness: int

    alarm_duration_seconds: int
    image_display_duration_seconds: int

    normal_work_interval_minutes: int  
    normal_break_duration_minutes: int  
    normal_snooze_duration_minutes: int

    strict_work_interval_minutes: int  
    strict_break_duration_minutes: int  
    strict_cooldown_minutes: int

    focused_mandatory_break_minutes: int

    max_snooze_passes: int
    snooze_redistributes_breaks: int
    
    enable_break_music: bool
    shuffle_media: bool
    allow_skip_in_normal_mode: bool

    created_at: str
    updated_at: str

    def to_dict(self):
        return asdict(self)