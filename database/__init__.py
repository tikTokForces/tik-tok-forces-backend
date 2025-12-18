"""
Database package initialization
"""
from database.config import get_db, init_db, close_db, engine, AsyncSessionLocal
from database.models import (
    Base,
    Job,
    Video,
    ProcessingHistory,
    Asset,
    ProcessingPreset,
    APILog,
    JobQueue,
    MusicGroup,
    MusicGroupMember,
    WatermarkGroup,
    WatermarkGroupMember,
    FootageGroup,
    FootageGroupMember
)

__all__ = [
    "get_db",
    "init_db",
    "close_db",
    "engine",
    "AsyncSessionLocal",
    "Base",
    "Job",
    "Video",
    "ProcessingHistory",
    "Asset",
    "ProcessingPreset",
    "APILog",
    "JobQueue",
    "MusicGroup",
    "MusicGroupMember",
    "WatermarkGroup",
    "WatermarkGroupMember",
    "FootageGroup",
    "FootageGroupMember",
]

