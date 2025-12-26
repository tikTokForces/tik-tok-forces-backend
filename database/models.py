"""
Database models for TikTok Forces API
Using SQLAlchemy with async support
"""
from sqlalchemy import Column, String, Integer, BigInteger, Float, Boolean, Text, TIMESTAMP, ForeignKey, UniqueConstraint, JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


# Database-agnostic UUID type that works with both SQLite and PostgreSQL
class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type when available, otherwise uses String(36).
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            # PostgreSQL UUID type can handle UUID objects directly
            return value if isinstance(value, uuid.UUID) else uuid.UUID(value) if value else None
        else:
            # SQLite stores as string
            return str(value) if isinstance(value, uuid.UUID) else value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            # PostgreSQL returns UUID objects directly
            return value if isinstance(value, uuid.UUID) else uuid.UUID(value) if value else None
        else:
            # SQLite returns strings, convert to UUID
            return uuid.UUID(value) if not isinstance(value, uuid.UUID) else value


class Job(Base):
    """
    Stores all processing jobs (replaces in-memory jobs_store)
    """
    __tablename__ = "jobs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(100), nullable=False, index=True)  # 'process', 'footages_add', 'music_add', etc.
    status = Column(String(50), nullable=False, default='pending', index=True)  # 'pending', 'processing', 'completed', 'failed', 'cancelled'
    
    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)
    started_at = Column(TIMESTAMP, nullable=True)
    completed_at = Column(TIMESTAMP, nullable=True)
    failed_at = Column(TIMESTAMP, nullable=True)
    
    # Processing details
    error_message = Column(Text, nullable=True)
    progress_percentage = Column(Integer, default=0)
    input_params = Column(JSON, nullable=True)  # Store all request parameters
    output_result = Column(JSON, nullable=True)  # Store output paths and metadata
    processing_time_seconds = Column(Integer, nullable=True)
    
    # Relationships
    processing_histories = relationship("ProcessingHistory", back_populates="job", cascade="all, delete-orphan")
    queue_entry = relationship("JobQueue", back_populates="job", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Job(id={self.id}, type={self.job_type}, status={self.status})>"


class Video(Base):
    """
    Stores video file metadata
    """
    __tablename__ = "videos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False, unique=True)
    
    # Video properties
    file_size_bytes = Column(BigInteger, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    fps = Column(Float, nullable=True)
    codec = Column(String(50), nullable=True)
    bitrate = Column(Integer, nullable=True)
    has_audio = Column(Boolean, default=True)
    
    # Metadata
    thumbnail_path = Column(String(1000), nullable=True)
    video_metadata = Column(JSON, nullable=True)  # Additional video metadata
    
    # Timestamps
    uploaded_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)
    is_deleted = Column(Boolean, default=False, index=True)
    
    # Relationships
    input_histories = relationship("ProcessingHistory", foreign_keys="ProcessingHistory.input_video_id", back_populates="input_video")
    output_histories = relationship("ProcessingHistory", foreign_keys="ProcessingHistory.output_video_id", back_populates="output_video")

    def __repr__(self):
        return f"<Video(id={self.id}, filename={self.original_filename})>"


class ProcessingHistory(Base):
    """
    Tracks video processing operations
    """
    __tablename__ = "processing_history"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID(), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    input_video_id = Column(GUID(), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True, index=True)
    output_video_id = Column(GUID(), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True, index=True)
    
    processing_type = Column(String(100), nullable=False)  # 'metadata_unify', 'footages', 'music', etc.
    parameters_used = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    job = relationship("Job", back_populates="processing_histories")
    input_video = relationship("Video", foreign_keys=[input_video_id], back_populates="input_histories")
    output_video = relationship("Video", foreign_keys=[output_video_id], back_populates="output_histories")

    def __repr__(self):
        return f"<ProcessingHistory(id={self.id}, type={self.processing_type})>"


class Asset(Base):
    """
    Stores assets like footages, music, watermarks, subtitles
    """
    __tablename__ = "assets"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    asset_type = Column(String(50), nullable=False, index=True)  # 'footage', 'music', 'watermark', 'subtitle', 'transition'
    name = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False, unique=True)
    
    # File properties
    file_size_bytes = Column(BigInteger, nullable=True)
    duration_seconds = Column(Float, nullable=True)  # for video/audio assets
    thumbnail_path = Column(String(1000), nullable=True)
    
    # Metadata and organization
    is_public = Column(Boolean, default=False)  # shared library vs private
    tags = Column(JSON, nullable=True)  # for searchability (stored as JSON array)
    asset_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Asset(id={self.id}, type={self.asset_type}, name={self.name})>"


class ProcessingPreset(Base):
    """
    Stores reusable processing configurations
    """
    __tablename__ = "processing_presets"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    preset_type = Column(String(100), nullable=False, index=True)  # 'process', 'footages', 'music', etc.
    parameters = Column(JSON, nullable=False)  # All the processing parameters
    
    is_default = Column(Boolean, default=False)
    usage_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ProcessingPreset(id={self.id}, name={self.name}, type={self.preset_type})>"


class APILog(Base):
    """
    Logs API requests for debugging and analytics
    """
    __tablename__ = "api_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    endpoint = Column(String(500), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    
    # Request/Response data
    request_body = Column(JSON, nullable=True)
    response_status = Column(Integer, nullable=True)
    response_body = Column(JSON, nullable=True)
    
    # Client info
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Performance
    execution_time_ms = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<APILog(id={self.id}, endpoint={self.endpoint}, status={self.response_status})>"


class JobQueue(Base):
    """
    Manages job queue for async processing with priority and retry logic
    """
    __tablename__ = "job_queue"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID(), ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    priority = Column(Integer, default=5, index=True)  # 1-10, higher = more important
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    scheduled_at = Column(TIMESTAMP, nullable=True)
    claimed_by = Column(String(200), nullable=True)  # worker identifier
    claimed_at = Column(TIMESTAMP, nullable=True)
    
    # Relationship
    job = relationship("Job", back_populates="queue_entry")

    def __repr__(self):
        return f"<JobQueue(id={self.id}, job_id={self.job_id}, priority={self.priority})>"


class MusicGroup(Base):
    """
    Groups for organizing music files
    """
    __tablename__ = "music_groups"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code for UI
    
    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = relationship("MusicGroupMember", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MusicGroup(id={self.id}, name={self.name})>"


class MusicGroupMember(Base):
    """
    Association table linking music files to groups
    """
    __tablename__ = "music_group_members"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    group_id = Column(GUID(), ForeignKey("music_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    music_filename = Column(String(500), nullable=False)  # Name of music file in assets/musics/
    
    # Order within group
    order = Column(Integer, default=0, index=True)
    
    # Timestamps
    added_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    group = relationship("MusicGroup", back_populates="members")
    
    # Unique constraint: a music file can only be in a group once
    __table_args__ = (
        UniqueConstraint('group_id', 'music_filename', name='uq_group_music'),
    )

    def __repr__(self):
        return f"<MusicGroupMember(id={self.id}, group_id={self.group_id}, music={self.music_filename})>"


class WatermarkGroup(Base):
    """
    Groups for organizing watermark files
    """
    __tablename__ = "watermark_groups"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)

    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = relationship("WatermarkGroupMember", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WatermarkGroup(id={self.id}, name={self.name})>"


class WatermarkGroupMember(Base):
    """
    Association table linking watermark files to groups
    """
    __tablename__ = "watermark_group_members"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    group_id = Column(GUID(), ForeignKey("watermark_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    watermark_filename = Column(String(500), nullable=False)
    order = Column(Integer, default=0, index=True)
    added_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)

    group = relationship("WatermarkGroup", back_populates="members")

    __table_args__ = (
        UniqueConstraint('group_id', 'watermark_filename', name='uq_group_watermark'),
    )

    def __repr__(self):
        return f"<WatermarkGroupMember(id={self.id}, group_id={self.group_id}, watermark={self.watermark_filename})>"


class FootageGroup(Base):
    """
    Groups for organizing footage overlay files
    """
    __tablename__ = "footage_groups"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)

    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = relationship("FootageGroupMember", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FootageGroup(id={self.id}, name={self.name})>"


class FootageGroupMember(Base):
    """
    Association table linking footage files to groups
    """
    __tablename__ = "footage_group_members"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    group_id = Column(GUID(), ForeignKey("footage_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    footage_filename = Column(String(500), nullable=False)
    order = Column(Integer, default=0, index=True)
    added_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)

    group = relationship("FootageGroup", back_populates="members")

    __table_args__ = (
        UniqueConstraint('group_id', 'footage_filename', name='uq_group_footage'),
    )

    def __repr__(self):
        return f"<FootageGroupMember(id={self.id}, group_id={self.group_id}, footage={self.footage_filename})>"


class Proxy(Base):
    """
    Proxy server configuration
    """
    __tablename__ = "proxies"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    login = Column(String(200), nullable=False)
    password = Column(String(255), nullable=False)
    ip = Column(String(50), nullable=False, index=True)  # IP address
    port = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="proxy", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Proxy(id={self.id}, ip={self.ip}:{self.port})>"


class User(Base):
    """
    User accounts with authentication
    Requires a proxy to be created
    """
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)  # Hashed password
    email = Column(String(255), nullable=False, unique=True, index=True)  # Now required
    full_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False, index=True)
    
    # Priority for automatic user assignment (1 = highest priority, 100 = lowest)
    priority = Column(Integer, default=50, nullable=False, index=True)
    
    # Required proxy relationship
    proxy_id = Column(GUID(), ForeignKey("proxies.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    # Metadata
    user_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(TIMESTAMP, nullable=True)
    
    # Relationships
    proxy = relationship("Proxy", back_populates="users")
    group_memberships = relationship("UserGroupMember", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


class UserGroup(Base):
    """
    Groups for organizing users
    """
    __tablename__ = "user_groups"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code for UI
    
    # Permissions/metadata
    permissions = Column(JSON, nullable=True)  # Store group permissions as JSON
    
    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = relationship("UserGroupMember", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserGroup(id={self.id}, name={self.name})>"


class UserGroupMember(Base):
    """
    Association table linking users to groups
    """
    __tablename__ = "user_group_members"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    group_id = Column(GUID(), ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Role within group (optional)
    role = Column(String(50), nullable=True)  # e.g., 'admin', 'member', 'viewer'
    
    # Timestamps
    added_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    group = relationship("UserGroup", back_populates="members")
    user = relationship("User", back_populates="group_memberships")
    
    # Unique constraint: a user can only be in a group once
    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', name='uq_group_user'),
    )

    def __repr__(self):
        return f"<UserGroupMember(id={self.id}, group_id={self.group_id}, user_id={self.user_id})>"

