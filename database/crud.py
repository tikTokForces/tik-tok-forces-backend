"""
CRUD operations for database models
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, desc
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from database.models import (
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
    FootageGroupMember,
    Proxy,
    User,
    UserGroup,
    UserGroupMember,
)


# ==================== JOB OPERATIONS ====================

async def create_job(
    db: AsyncSession,
    job_type: str,
    input_params: Optional[Dict[str, Any]] = None,
    status: str = "pending"
) -> Job:
    """Create a new job"""
    job = Job(
        id=uuid.uuid4(),
        job_type=job_type,
        status=status,
        input_params=input_params,
        created_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Optional[Job]:
    """Get job by ID"""
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    return result.scalar_one_or_none()


async def update_job_status(
    db: AsyncSession,
    job_id: uuid.UUID,
    status: str,
    error_message: Optional[str] = None,
    output_result: Optional[Dict[str, Any]] = None,
    progress: Optional[int] = None
) -> Optional[Job]:
    """Update job status and related fields"""
    job = await get_job(db, job_id)
    if not job:
        return None
    
    job.status = status
    
    if status == "processing" and not job.started_at:
        job.started_at = datetime.utcnow()
    elif status == "completed":
        job.completed_at = datetime.utcnow()
        if job.started_at:
            job.processing_time_seconds = int((job.completed_at - job.started_at).total_seconds())
    elif status == "failed":
        job.failed_at = datetime.utcnow()
        job.error_message = error_message
    
    if output_result is not None:
        job.output_result = output_result
    
    if progress is not None:
        job.progress_percentage = progress
    
    await db.commit()
    await db.refresh(job)
    return job


async def get_jobs(
    db: AsyncSession,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Job]:
    """Get jobs with optional filtering"""
    query = select(Job).order_by(desc(Job.created_at))
    
    if status:
        query = query.where(Job.status == status)
    if job_type:
        query = query.where(Job.job_type == job_type)
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def delete_job(db: AsyncSession, job_id: uuid.UUID) -> bool:
    """Delete a job"""
    result = await db.execute(
        delete(Job).where(Job.id == job_id)
    )
    await db.commit()
    return result.rowcount > 0


# ==================== VIDEO OPERATIONS ====================

async def create_video(
    db: AsyncSession,
    original_filename: str,
    file_path: str,
    **kwargs
) -> Video:
    """Create a new video record"""
    video = Video(
        id=uuid.uuid4(),
        original_filename=original_filename,
        file_path=file_path,
        uploaded_at=datetime.utcnow(),
        **kwargs
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video


async def get_video(db: AsyncSession, video_id: uuid.UUID) -> Optional[Video]:
    """Get video by ID"""
    result = await db.execute(
        select(Video).where(Video.id == video_id)
    )
    return result.scalar_one_or_none()


async def get_video_by_path(db: AsyncSession, file_path: str) -> Optional[Video]:
    """Get video by file path"""
    result = await db.execute(
        select(Video).where(Video.file_path == file_path)
    )
    return result.scalar_one_or_none()


async def get_videos(
    db: AsyncSession,
    include_deleted: bool = False,
    limit: int = 100,
    offset: int = 0
) -> List[Video]:
    """Get videos"""
    query = select(Video).order_by(desc(Video.uploaded_at))
    
    if not include_deleted:
        query = query.where(Video.is_deleted == False)
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def soft_delete_video(db: AsyncSession, video_id: uuid.UUID) -> bool:
    """Soft delete a video"""
    video = await get_video(db, video_id)
    if not video:
        return False
    
    video.is_deleted = True
    await db.commit()
    return True


# ==================== ASSET OPERATIONS ====================

async def create_asset(
    db: AsyncSession,
    asset_type: str,
    name: str,
    file_path: str,
    **kwargs
) -> Asset:
    """Create a new asset"""
    asset = Asset(
        id=uuid.uuid4(),
        asset_type=asset_type,
        name=name,
        file_path=file_path,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        **kwargs
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


async def get_assets_by_type(
    db: AsyncSession,
    asset_type: str,
    limit: int = 100,
    offset: int = 0
) -> List[Asset]:
    """Get assets by type"""
    result = await db.execute(
        select(Asset)
        .where(Asset.asset_type == asset_type)
        .order_by(desc(Asset.created_at))
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def search_assets(
    db: AsyncSession,
    query: str,
    asset_type: Optional[str] = None
) -> List[Asset]:
    """Search assets by name or tags"""
    search_query = select(Asset).where(
        or_(
            Asset.name.ilike(f"%{query}%"),
            Asset.tags.any(query)
        )
    )
    
    if asset_type:
        search_query = search_query.where(Asset.asset_type == asset_type)
    
    result = await db.execute(search_query)
    return list(result.scalars().all())


# ==================== PROCESSING HISTORY OPERATIONS ====================

async def create_processing_history(
    db: AsyncSession,
    job_id: uuid.UUID,
    processing_type: str,
    input_video_id: Optional[uuid.UUID] = None,
    output_video_id: Optional[uuid.UUID] = None,
    parameters_used: Optional[Dict[str, Any]] = None
) -> ProcessingHistory:
    """Create processing history record"""
    history = ProcessingHistory(
        id=uuid.uuid4(),
        job_id=job_id,
        input_video_id=input_video_id,
        output_video_id=output_video_id,
        processing_type=processing_type,
        parameters_used=parameters_used,
        created_at=datetime.utcnow()
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)
    return history


async def get_video_history(
    db: AsyncSession,
    video_id: uuid.UUID
) -> List[ProcessingHistory]:
    """Get processing history for a video"""
    result = await db.execute(
        select(ProcessingHistory)
        .where(
            or_(
                ProcessingHistory.input_video_id == video_id,
                ProcessingHistory.output_video_id == video_id
            )
        )
        .order_by(desc(ProcessingHistory.created_at))
    )
    return list(result.scalars().all())


# ==================== PRESET OPERATIONS ====================

async def create_preset(
    db: AsyncSession,
    name: str,
    preset_type: str,
    parameters: Dict[str, Any],
    description: Optional[str] = None,
    is_default: bool = False
) -> ProcessingPreset:
    """Create a processing preset"""
    preset = ProcessingPreset(
        id=uuid.uuid4(),
        name=name,
        preset_type=preset_type,
        parameters=parameters,
        description=description,
        is_default=is_default,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(preset)
    await db.commit()
    await db.refresh(preset)
    return preset


async def get_presets_by_type(
    db: AsyncSession,
    preset_type: str
) -> List[ProcessingPreset]:
    """Get presets by type"""
    result = await db.execute(
        select(ProcessingPreset)
        .where(ProcessingPreset.preset_type == preset_type)
        .order_by(desc(ProcessingPreset.usage_count))
    )
    return list(result.scalars().all())


async def increment_preset_usage(db: AsyncSession, preset_id: uuid.UUID):
    """Increment preset usage count"""
    await db.execute(
        update(ProcessingPreset)
        .where(ProcessingPreset.id == preset_id)
        .values(usage_count=ProcessingPreset.usage_count + 1)
    )
    await db.commit()


# ==================== API LOG OPERATIONS ====================

async def create_api_log(
    db: AsyncSession,
    endpoint: str,
    method: str,
    request_body: Optional[Dict[str, Any]] = None,
    response_status: Optional[int] = None,
    response_body: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    execution_time_ms: Optional[int] = None
) -> APILog:
    """Create an API log entry"""
    log = APILog(
        id=uuid.uuid4(),
        endpoint=endpoint,
        method=method,
        request_body=request_body,
        response_status=response_status,
        response_body=response_body,
        ip_address=ip_address,
        user_agent=user_agent,
        execution_time_ms=execution_time_ms,
        created_at=datetime.utcnow()
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_api_logs(
    db: AsyncSession,
    endpoint: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[APILog]:
    """Get API logs with optional filtering"""
    from database.models import APILog
    query = select(APILog).order_by(desc(APILog.created_at))
    
    if endpoint:
        query = query.where(APILog.endpoint == endpoint)
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    return list(result.scalars().all())


# ==================== JOB QUEUE OPERATIONS ====================

async def enqueue_job(
    db: AsyncSession,
    job_id: uuid.UUID,
    priority: int = 5,
    max_retries: int = 3
) -> JobQueue:
    """Add job to queue"""
    queue_entry = JobQueue(
        id=uuid.uuid4(),
        job_id=job_id,
        priority=priority,
        max_retries=max_retries
    )
    db.add(queue_entry)
    await db.commit()
    await db.refresh(queue_entry)
    return queue_entry


async def claim_next_job(
    db: AsyncSession,
    worker_id: str
) -> Optional[JobQueue]:
    """Claim next job from queue for processing"""
    result = await db.execute(
        select(JobQueue)
        .join(Job)
        .where(
            and_(
                Job.status == "pending",
                JobQueue.claimed_by.is_(None),
                JobQueue.retry_count < JobQueue.max_retries
            )
        )
        .order_by(desc(JobQueue.priority), JobQueue.scheduled_at)
        .limit(1)
    )
    queue_entry = result.scalar_one_or_none()
    
    if queue_entry:
        queue_entry.claimed_by = worker_id
        queue_entry.claimed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(queue_entry)
    
    return queue_entry


# ==================== MUSIC GROUP OPERATIONS ====================

async def create_music_group(
    db: AsyncSession,
    name: str,
    description: Optional[str] = None,
    color: Optional[str] = None
) -> MusicGroup:
    """Create a new music group"""
    group = MusicGroup(
        id=uuid.uuid4(),
        name=name,
        description=description,
        color=color,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


async def get_music_group(db: AsyncSession, group_id: uuid.UUID) -> Optional[MusicGroup]:
    """Get music group by ID with members"""
    result = await db.execute(
        select(MusicGroup)
        .options(selectinload(MusicGroup.members))
        .where(MusicGroup.id == group_id)
    )
    return result.scalar_one_or_none()


async def get_all_music_groups(db: AsyncSession) -> List[MusicGroup]:
    """Get all music groups with their members"""
    result = await db.execute(
        select(MusicGroup)
        .options(selectinload(MusicGroup.members))
        .order_by(MusicGroup.created_at.desc())
    )
    return list(result.scalars().all())


async def update_music_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[str] = None
) -> Optional[MusicGroup]:
    """Update a music group"""
    group = await get_music_group(db, group_id)
    if not group:
        return None
    
    if name is not None:
        group.name = name
    if description is not None:
        group.description = description
    if color is not None:
        group.color = color
    group.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(group)
    return group


async def delete_music_group(db: AsyncSession, group_id: uuid.UUID) -> bool:
    """Delete a music group and all its members"""
    group = await get_music_group(db, group_id)
    if not group:
        return False
    
    await db.delete(group)
    await db.commit()
    return True


async def add_music_to_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    music_filename: str,
    order: Optional[int] = None
) -> Optional[MusicGroupMember]:
    """Add a music file to a group"""
    # Check if group exists
    group = await get_music_group(db, group_id)
    if not group:
        return None
    
    # Check if already in group
    existing = await db.execute(
        select(MusicGroupMember).where(
            and_(
                MusicGroupMember.group_id == group_id,
                MusicGroupMember.music_filename == music_filename
            )
        )
    )
    if existing.scalar_one_or_none():
        return None  # Already in group
    
    # Get max order if not specified
    if order is None:
        result = await db.execute(
            select(MusicGroupMember.order)
            .where(MusicGroupMember.group_id == group_id)
            .order_by(desc(MusicGroupMember.order))
            .limit(1)
        )
        max_order = result.scalar_one_or_none() or -1
        order = max_order + 1
    
    member = MusicGroupMember(
        id=uuid.uuid4(),
        group_id=group_id,
        music_filename=music_filename,
        order=order,
        added_at=datetime.utcnow()
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def remove_music_from_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    music_filename: str
) -> bool:
    """Remove a music file from a group"""
    result = await db.execute(
        select(MusicGroupMember).where(
            and_(
                MusicGroupMember.group_id == group_id,
                MusicGroupMember.music_filename == music_filename
            )
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        return False
    
    await db.delete(member)
    await db.commit()
    return True


async def get_group_members(db: AsyncSession, group_id: uuid.UUID) -> List[MusicGroupMember]:
    """Get all members of a group"""
    result = await db.execute(
        select(MusicGroupMember)
        .where(MusicGroupMember.group_id == group_id)
        .order_by(MusicGroupMember.order)
    )
    return list(result.scalars().all())


async def get_music_groups_for_file(db: AsyncSession, music_filename: str) -> List[MusicGroup]:
    """Get all groups that contain a specific music file"""
    result = await db.execute(
        select(MusicGroup)
        .join(MusicGroupMember)
        .where(MusicGroupMember.music_filename == music_filename)
        .distinct()
    )
    return list(result.scalars().all())


# ==================== WATERMARK GROUP OPERATIONS ====================

async def create_watermark_group(
    db: AsyncSession,
    name: str,
    description: Optional[str] = None,
    color: Optional[str] = None
) -> WatermarkGroup:
    group = WatermarkGroup(
        id=uuid.uuid4(),
        name=name,
        description=description,
        color=color,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


async def get_watermark_group(db: AsyncSession, group_id: uuid.UUID) -> Optional[WatermarkGroup]:
    result = await db.execute(
        select(WatermarkGroup)
        .options(selectinload(WatermarkGroup.members))
        .where(WatermarkGroup.id == group_id)
    )
    return result.scalar_one_or_none()


async def get_all_watermark_groups(db: AsyncSession) -> List[WatermarkGroup]:
    result = await db.execute(
        select(WatermarkGroup)
        .options(selectinload(WatermarkGroup.members))
        .order_by(WatermarkGroup.created_at.desc())
    )
    return list(result.scalars().all())


async def update_watermark_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[str] = None
) -> Optional[WatermarkGroup]:
    group = await get_watermark_group(db, group_id)
    if not group:
        return None

    if name is not None:
        group.name = name
    if description is not None:
        group.description = description
    if color is not None:
        group.color = color
    group.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(group)
    return group


async def delete_watermark_group(db: AsyncSession, group_id: uuid.UUID) -> bool:
    group = await get_watermark_group(db, group_id)
    if not group:
        return False

    await db.delete(group)
    await db.commit()
    return True


async def add_watermark_to_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    watermark_filename: str,
    order: Optional[int] = None
) -> Optional[WatermarkGroupMember]:
    group = await get_watermark_group(db, group_id)
    if not group:
        return None

    existing = await db.execute(
        select(WatermarkGroupMember).where(
            and_(
                WatermarkGroupMember.group_id == group_id,
                WatermarkGroupMember.watermark_filename == watermark_filename
            )
        )
    )
    if existing.scalar_one_or_none():
        return None

    if order is None:
        result = await db.execute(
            select(WatermarkGroupMember.order)
            .where(WatermarkGroupMember.group_id == group_id)
            .order_by(desc(WatermarkGroupMember.order))
            .limit(1)
        )
        max_order = result.scalar_one_or_none() or -1
        order = max_order + 1

    member = WatermarkGroupMember(
        id=uuid.uuid4(),
        group_id=group_id,
        watermark_filename=watermark_filename,
        order=order,
        added_at=datetime.utcnow()
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def remove_watermark_from_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    watermark_filename: str
) -> bool:
    result = await db.execute(
        select(WatermarkGroupMember).where(
            and_(
                WatermarkGroupMember.group_id == group_id,
                WatermarkGroupMember.watermark_filename == watermark_filename
            )
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        return False

    await db.delete(member)
    await db.commit()
    return True


async def get_watermark_groups_for_file(db: AsyncSession, watermark_filename: str) -> List[WatermarkGroup]:
    result = await db.execute(
        select(WatermarkGroup)
        .join(WatermarkGroupMember)
        .where(WatermarkGroupMember.watermark_filename == watermark_filename)
        .distinct()
    )
    return list(result.scalars().all())


# ==================== FOOTAGE GROUP OPERATIONS ====================

async def create_footage_group(
    db: AsyncSession,
    name: str,
    description: Optional[str] = None,
    color: Optional[str] = None
) -> FootageGroup:
    group = FootageGroup(
        id=uuid.uuid4(),
        name=name,
        description=description,
        color=color,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


async def get_footage_group(db: AsyncSession, group_id: uuid.UUID) -> Optional[FootageGroup]:
    result = await db.execute(
        select(FootageGroup)
        .options(selectinload(FootageGroup.members))
        .where(FootageGroup.id == group_id)
    )
    return result.scalar_one_or_none()


async def get_all_footage_groups(db: AsyncSession) -> List[FootageGroup]:
    result = await db.execute(
        select(FootageGroup)
        .options(selectinload(FootageGroup.members))
        .order_by(FootageGroup.created_at.desc())
    )
    return list(result.scalars().all())


async def update_footage_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[str] = None
) -> Optional[FootageGroup]:
    group = await get_footage_group(db, group_id)
    if not group:
        return None

    if name is not None:
        group.name = name
    if description is not None:
        group.description = description
    if color is not None:
        group.color = color
    group.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(group)
    return group


async def delete_footage_group(db: AsyncSession, group_id: uuid.UUID) -> bool:
    group = await get_footage_group(db, group_id)
    if not group:
        return False

    await db.delete(group)
    await db.commit()
    return True


async def add_footage_to_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    footage_filename: str,
    order: Optional[int] = None
) -> Optional[FootageGroupMember]:
    group = await get_footage_group(db, group_id)
    if not group:
        return None

    existing = await db.execute(
        select(FootageGroupMember).where(
            and_(
                FootageGroupMember.group_id == group_id,
                FootageGroupMember.footage_filename == footage_filename
            )
        )
    )
    if existing.scalar_one_or_none():
        return None

    if order is None:
        result = await db.execute(
            select(FootageGroupMember.order)
            .where(FootageGroupMember.group_id == group_id)
            .order_by(desc(FootageGroupMember.order))
            .limit(1)
        )
        max_order = result.scalar_one_or_none() or -1
        order = max_order + 1

    member = FootageGroupMember(
        id=uuid.uuid4(),
        group_id=group_id,
        footage_filename=footage_filename,
        order=order,
        added_at=datetime.utcnow()
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def remove_footage_from_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    footage_filename: str
) -> bool:
    result = await db.execute(
        select(FootageGroupMember).where(
            and_(
                FootageGroupMember.group_id == group_id,
                FootageGroupMember.footage_filename == footage_filename
            )
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        return False

    await db.delete(member)
    await db.commit()
    return True


async def get_footage_groups_for_file(db: AsyncSession, footage_filename: str) -> List[FootageGroup]:
    result = await db.execute(
        select(FootageGroup)
        .join(FootageGroupMember)
        .where(FootageGroupMember.footage_filename == footage_filename)
        .distinct()
    )
    return list(result.scalars().all())


# ==================== PROXY OPERATIONS ====================

async def create_proxy(
    db: AsyncSession,
    login: str,
    password: str,
    ip: str,
    port: int
) -> Proxy:
    """Create a new proxy"""
    proxy = Proxy(
        id=uuid.uuid4(),
        login=login,
        password=password,
        ip=ip,
        port=port,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(proxy)
    await db.commit()
    await db.refresh(proxy)
    return proxy


async def get_proxy(db: AsyncSession, proxy_id: uuid.UUID) -> Optional[Proxy]:
    """Get proxy by ID"""
    result = await db.execute(
        select(Proxy).where(Proxy.id == proxy_id)
    )
    return result.scalar_one_or_none()


async def get_all_proxies(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0
) -> List[Proxy]:
    """Get all proxies"""
    query = select(Proxy).order_by(desc(Proxy.created_at))
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_proxy(
    db: AsyncSession,
    proxy_id: uuid.UUID,
    login: Optional[str] = None,
    password: Optional[str] = None,
    ip: Optional[str] = None,
    port: Optional[int] = None
) -> Optional[Proxy]:
    """Update a proxy"""
    proxy = await get_proxy(db, proxy_id)
    if not proxy:
        return None
    
    if login is not None:
        proxy.login = login
    if password is not None:
        proxy.password = password
    if ip is not None:
        proxy.ip = ip
    if port is not None:
        proxy.port = port
    
    proxy.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(proxy)
    return proxy


async def delete_proxy(db: AsyncSession, proxy_id: uuid.UUID) -> bool:
    """Delete a proxy (only if no users are using it)"""
    proxy = await get_proxy(db, proxy_id)
    if not proxy:
        return False
    
    # Check if any users are using this proxy
    users_count = await db.execute(
        select(User).where(User.proxy_id == proxy_id)
    )
    if users_count.scalars().first():
        raise ValueError("Cannot delete proxy: users are still using it")
    
    await db.delete(proxy)
    await db.commit()
    return True


# ==================== USER OPERATIONS ====================

async def create_user(
    db: AsyncSession,
    username: str,
    password_hash: str,
    email: str,
    proxy_id: uuid.UUID,
    full_name: Optional[str] = None,
    is_active: bool = True,
    is_admin: bool = False,
    priority: int = 50,
    user_metadata: Optional[Dict[str, Any]] = None
) -> User:
    """Create a new user (proxy is required)"""
    # Verify proxy exists
    proxy = await get_proxy(db, proxy_id)
    if not proxy:
        raise ValueError("Proxy not found")
    
    # Validate priority range
    if priority < 1 or priority > 100:
        raise ValueError("Priority must be between 1 and 100")
    
    user = User(
        id=uuid.uuid4(),
        username=username,
        password_hash=password_hash,
        email=email,
        proxy_id=proxy_id,
        full_name=full_name,
        is_active=is_active,
        is_admin=is_admin,
        priority=priority,
        user_metadata=user_metadata,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    """Get user by ID with proxy"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.proxy))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username"""
    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email"""
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_all_users(
    db: AsyncSession,
    include_inactive: bool = False,
    limit: int = 100,
    offset: int = 0
) -> List[User]:
    """Get all users"""
    from sqlalchemy.orm import selectinload
    query = select(User).options(selectinload(User.group_memberships)).order_by(desc(User.created_at))
    
    if not include_inactive:
        query = query.where(User.is_active == True)
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_users_by_priority(
    db: AsyncSession,
    limit: Optional[int] = None,
    include_inactive: bool = False
) -> List[User]:
    """Get users ordered by priority (1 = highest priority, 100 = lowest)"""
    from sqlalchemy.orm import selectinload
    query = select(User).options(selectinload(User.proxy)).order_by(User.priority.asc(), User.created_at.asc())
    
    if not include_inactive:
        query = query.where(User.is_active == True)
    
    if limit:
        query = query.limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def assign_users_to_videos(
    db: AsyncSession,
    video_count: int,
    include_inactive: bool = False
) -> List[Dict[str, Any]]:
    """
    Automatically assign users to videos based on priority.
    Returns list of assignments: [{"video_index": 0, "user_id": "...", "user": {...}, "proxy": {...}}, ...]
    """
    # Get users ordered by priority (1 = highest)
    users = await get_users_by_priority(db, limit=video_count, include_inactive=include_inactive)
    
    if not users:
        return []
    
    assignments = []
    for i in range(video_count):
        # Cycle through users if we have more videos than users
        user = users[i % len(users)]
        
        # Load proxy relationship if not already loaded
        if not hasattr(user, 'proxy') or user.proxy is None:
            proxy = await get_proxy(db, user.proxy_id)
        else:
            proxy = user.proxy
        
        assignments.append({
            "video_index": i,
            "user_id": str(user.id),
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "priority": user.priority,
                "proxy_id": str(user.proxy_id)
            },
            "proxy": {
                "id": str(proxy.id) if proxy else None,
                "login": proxy.login if proxy else None,
                "password": proxy.password if proxy else None,
                "ip": proxy.ip if proxy else None,
                "port": proxy.port if proxy else None
            } if proxy else None
        })
    
    return assignments


async def update_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    username: Optional[str] = None,
    password_hash: Optional[str] = None,
    email: Optional[str] = None,
    proxy_id: Optional[uuid.UUID] = None,
    full_name: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_admin: Optional[bool] = None,
    user_metadata: Optional[Dict[str, Any]] = None
) -> Optional[User]:
    """Update a user"""
    user = await get_user(db, user_id)
    if not user:
        return None
    
    if username is not None:
        user.username = username
    if password_hash is not None:
        user.password_hash = password_hash
    if email is not None:
        user.email = email
    if proxy_id is not None:
        # Verify proxy exists
        proxy = await get_proxy(db, proxy_id)
        if not proxy:
            raise ValueError("Proxy not found")
        user.proxy_id = proxy_id
    if full_name is not None:
        user.full_name = full_name
    if is_active is not None:
        user.is_active = is_active
    if is_admin is not None:
        user.is_admin = is_admin
    if user_metadata is not None:
        user.user_metadata = user_metadata
    
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_last_login(db: AsyncSession, user_id: uuid.UUID):
    """Update user's last login timestamp"""
    user = await get_user(db, user_id)
    if user:
        user.last_login_at = datetime.utcnow()
        await db.commit()


async def delete_user(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Delete a user"""
    user = await get_user(db, user_id)
    if not user:
        return False
    
    await db.delete(user)
    await db.commit()
    return True


# ==================== USER GROUP OPERATIONS ====================

async def create_user_group(
    db: AsyncSession,
    name: str,
    description: Optional[str] = None,
    color: Optional[str] = None,
    permissions: Optional[Dict[str, Any]] = None
) -> UserGroup:
    """Create a new user group"""
    group = UserGroup(
        id=uuid.uuid4(),
        name=name,
        description=description,
        color=color,
        permissions=permissions,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


async def get_user_group(db: AsyncSession, group_id: uuid.UUID) -> Optional[UserGroup]:
    """Get user group by ID with members"""
    result = await db.execute(
        select(UserGroup)
        .options(selectinload(UserGroup.members))
        .where(UserGroup.id == group_id)
    )
    return result.scalar_one_or_none()


async def get_all_user_groups(db: AsyncSession) -> List[UserGroup]:
    """Get all user groups with their members"""
    result = await db.execute(
        select(UserGroup)
        .options(selectinload(UserGroup.members))
        .order_by(UserGroup.created_at.desc())
    )
    return list(result.scalars().all())


async def update_user_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[str] = None,
    permissions: Optional[Dict[str, Any]] = None
) -> Optional[UserGroup]:
    """Update a user group"""
    group = await get_user_group(db, group_id)
    if not group:
        return None
    
    if name is not None:
        group.name = name
    if description is not None:
        group.description = description
    if color is not None:
        group.color = color
    if permissions is not None:
        group.permissions = permissions
    
    group.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(group)
    return group


async def delete_user_group(db: AsyncSession, group_id: uuid.UUID) -> bool:
    """Delete a user group and all its members"""
    group = await get_user_group(db, group_id)
    if not group:
        return False
    
    await db.delete(group)
    await db.commit()
    return True


async def add_user_to_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    role: Optional[str] = None
) -> Optional[UserGroupMember]:
    """Add a user to a group"""
    # Check if group exists
    group = await get_user_group(db, group_id)
    if not group:
        return None
    
    # Check if user exists
    user = await get_user(db, user_id)
    if not user:
        return None
    
    # Check if already in group
    existing = await db.execute(
        select(UserGroupMember).where(
            and_(
                UserGroupMember.group_id == group_id,
                UserGroupMember.user_id == user_id
            )
        )
    )
    if existing.scalar_one_or_none():
        return None  # Already in group
    
    member = UserGroupMember(
        id=uuid.uuid4(),
        group_id=group_id,
        user_id=user_id,
        role=role,
        added_at=datetime.utcnow()
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def remove_user_from_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_id: uuid.UUID
) -> bool:
    """Remove a user from a group"""
    result = await db.execute(
        select(UserGroupMember).where(
            and_(
                UserGroupMember.group_id == group_id,
                UserGroupMember.user_id == user_id
            )
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        return False
    
    await db.delete(member)
    await db.commit()
    return True


async def get_user_groups_for_user(db: AsyncSession, user_id: uuid.UUID) -> List[UserGroup]:
    """Get all groups that contain a specific user"""
    result = await db.execute(
        select(UserGroup)
        .join(UserGroupMember)
        .where(UserGroupMember.user_id == user_id)
        .distinct()
    )
    return list(result.scalars().all())


async def get_group_members_for_user_group(db: AsyncSession, group_id: uuid.UUID) -> List[UserGroupMember]:
    """Get all members of a user group"""
    result = await db.execute(
        select(UserGroupMember)
        .options(selectinload(UserGroupMember.user))
        .where(UserGroupMember.group_id == group_id)
        .order_by(UserGroupMember.added_at)
    )
    return list(result.scalars().all())

