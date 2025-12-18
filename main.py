from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
import sys
from pathlib import Path
import subprocess
import uuid
import time
import os
import shutil
import random
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password"""
    return pwd_context.verify(plain_password, hashed_password)

# Database imports
from database import get_db, init_db, close_db
from database.crud import (
    create_job, 
    get_job, 
    update_job_status,
    create_api_log,
    create_music_group,
    get_music_group,
    get_all_music_groups,
    update_music_group,
    delete_music_group,
    add_music_to_group,
    remove_music_from_group,
    get_group_members,
    get_music_groups_for_file,
    create_watermark_group,
    get_watermark_group,
    get_all_watermark_groups,
    update_watermark_group,
    delete_watermark_group,
    add_watermark_to_group,
    remove_watermark_from_group,
    get_watermark_groups_for_file,
    create_footage_group,
    get_footage_group,
    get_all_footage_groups,
    update_footage_group,
    delete_footage_group,
    add_footage_to_group,
    remove_footage_from_group,
    get_footage_groups_for_file,
    create_proxy,
    get_proxy,
    get_all_proxies,
    update_proxy,
    delete_proxy,
    create_user,
    get_user,
    get_user_by_username,
    get_user_by_email,
    get_all_users,
    update_user,
    delete_user,
    create_user_group,
    get_user_group,
    get_all_user_groups,
    update_user_group,
    delete_user_group,
    add_user_to_group,
    remove_user_from_group,
    get_user_groups_for_user,
    get_group_members_for_user_group
)

# Ensure we can import startUniq.py from the STEP1.../code directory

CODE_DIR = Path("/Users/maxsymonenko/tik_tok_forces_api/unicalizator/STEP1-MassMetadataUnifyerEndEffects/code").resolve()
CODE_DIR2 = Path("/Users/maxsymonenko/tik_tok_forces_api/unicalizator/STEP5-MassFootagesAdd/code").resolve()
CODE_DIR4 = Path("/Users/maxsymonenko/tik_tok_forces_api/STEP4-MassMusicAdd/code").resolve()
CODE_DIR19 = Path("/Users/maxsymonenko/tik_tok_forces_api/STEP19-SubtitlesOverlays/code").resolve()
CODE_DIR20 = Path("/Users/maxsymonenko/tik_tok_forces_api/STEP20-WaterMarkOverlays/code").resolve()

if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))
if str(CODE_DIR2) not in sys.path:
    sys.path.insert(0, str(CODE_DIR2))
if str(CODE_DIR4) not in sys.path:
    sys.path.insert(0, str(CODE_DIR4))
if str(CODE_DIR19) not in sys.path:
    sys.path.insert(0, str(CODE_DIR19))
if str(CODE_DIR20) not in sys.path:
    sys.path.insert(0, str(CODE_DIR20))

try:
    from startUniq import ImagesAndVideoMassUniq  # type: ignore
except Exception as import_error:  # pragma: no cover
    ImagesAndVideoMassUniq = None  # fallback for import failure

app = FastAPI(title="TikTok Forces API", version="1.0.0")

# Enable CORS for React frontend (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=False,  # Must be False when using allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Application lifecycle events
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_db()
    print("✅ Database initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown"""
    await close_db()
    print("✅ Database connections closed")


@app.get("/")
async def root():
    return {
        "message": "TikTok Forces API",
        "version": "1.0.0",
        "docs": "/docs",
        "database": "connected"
    }


@app.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List all jobs with optional filtering"""
    from database.crud import get_jobs
    jobs = await get_jobs(db, status=status, job_type=job_type, limit=limit, offset=offset)
    
    return {
        "count": len(jobs),
        "jobs": [
            {
                "id": str(job.id),
                "job_type": job.job_type,
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "progress_percentage": job.progress_percentage,
                "processing_time_seconds": job.processing_time_seconds
            }
            for job in jobs
        ]
    }


@app.delete("/job/{job_id}")
async def delete_job_endpoint(job_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a job by ID"""
    from database.crud import delete_job
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    deleted = await delete_job(db, job_uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"status": "deleted", "job_id": job_id}


@app.get("/browse")
async def browse_filesystem(path: str = None):
    """Browse filesystem for file/folder selection"""
    from pathlib import Path as PathLib
    import os
    
    try:
        # Default to project root if no path provided
        if not path:
            browse_path = PathLib(__file__).parent
        else:
            browse_path = PathLib(path).expanduser().resolve()
        
        # Security: only allow browsing within user's home directory or project
        home_dir = PathLib.home()
        project_dir = PathLib(__file__).parent
        
        # Check if path is safe
        if not (str(browse_path).startswith(str(home_dir)) or str(browse_path).startswith(str(project_dir))):
            raise HTTPException(status_code=403, detail="Access denied to this path")
        
        if not browse_path.exists():
            raise HTTPException(status_code=404, detail="Path does not exist")
        
        items = []
        
        # Add parent directory link if not at root
        if browse_path.parent != browse_path:
            items.append({
                "name": "..",
                "path": str(browse_path.parent),
                "type": "directory",
                "is_parent": True
            })
        
        # List directory contents
        if browse_path.is_dir():
            for item in sorted(browse_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                # Skip hidden files
                if item.name.startswith('.'):
                    continue
                
                try:
                    stat = item.stat()
                    items.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size if item.is_file() else None,
                        "modified": stat.st_mtime,
                        "extension": item.suffix if item.is_file() else None
                    })
                except Exception:
                    # Skip files we can't access
                    continue
        
        return {
            "current_path": str(browse_path),
            "parent_path": str(browse_path.parent) if browse_path.parent != browse_path else None,
            "items": items,
            "is_directory": browse_path.is_dir()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/quickpaths")
async def get_quick_paths():
    """Get quick access paths for common directories"""
    from pathlib import Path as PathLib
    
    project_root = PathLib(__file__).parent
    
    quick_paths = [
        {
            "name": "🏠 Project Root",
            "path": str(project_root)
        },
        {
            "name": "📁 Home Directory",
            "path": str(PathLib.home())
        },
        {
            "name": "🎬 STEP19 - Input Videos",
            "path": str(project_root / "STEP19-SubtitlesOverlays" / "input_video")
        },
        {
            "name": "📤 STEP19 - Output Videos",
            "path": str(project_root / "STEP19-SubtitlesOverlays" / "output_video")
        },
        {
            "name": "💧 STEP20 - Watermarks Input",
            "path": str(project_root / "STEP20-WaterMarkOverlays" / "input_video")
        },
        {
            "name": "🎵 STEP4 - Music Input",
            "path": str(project_root / "STEP4-MassMusicAdd" / "input_video")
        },
        {
            "name": "🎥 STEP5 - Footages Input",
            "path": str(project_root / "STEP5-MassFootagesAdd" / "input_video")
        },
    ]
    
    return {"quick_paths": quick_paths}


@app.get("/video_metadata")
async def get_video_metadata(video_path: str):
    """Get video metadata using ffprobe"""
    from pathlib import Path as PathLib
    import json
    
    try:
        video_file = PathLib(video_path).expanduser().resolve()
        
        if not video_file.exists():
            raise HTTPException(status_code=404, detail="Video file not found")
        
        # Use ffprobe to get video metadata
        ffprobe_cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_file)
        ]
        
        result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)
        
        # Extract useful information
        video_stream = next((s for s in metadata.get("streams", []) if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in metadata.get("streams", []) if s.get("codec_type") == "audio"), None)
        format_info = metadata.get("format", {})
        
        response = {
            "file_path": str(video_file),
            "file_name": video_file.name,
            "file_size": int(format_info.get("size", 0)),
            "duration": float(format_info.get("duration", 0)),
            "bitrate": int(format_info.get("bit_rate", 0)),
        }
        
        if video_stream:
            # Calculate FPS
            fps_parts = video_stream.get("r_frame_rate", "30/1").split("/")
            fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
            
            response.update({
                "width": video_stream.get("width"),
                "height": video_stream.get("height"),
                "fps": round(fps, 2),
                "codec": video_stream.get("codec_name"),
                "video_bitrate": int(video_stream.get("bit_rate", 0)) if video_stream.get("bit_rate") else None,
            })
        
        if audio_stream:
            response.update({
                "has_audio": True,
                "audio_codec": audio_stream.get("codec_name"),
                "audio_bitrate": int(audio_stream.get("bit_rate", 0)) if audio_stream.get("bit_rate") else None,
                "audio_sample_rate": int(audio_stream.get("sample_rate", 0)) if audio_stream.get("sample_rate") else None,
            })
        else:
            response["has_audio"] = False
        
        return response
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFprobe error: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/video_params")
async def get_video_params(video_path: str):
    """Get video parameters formatted for processing API
    
    Returns video metadata formatted as parameters ready to use with /process endpoint.
    Useful for getting default values based on the input video.
    """
    from pathlib import Path as PathLib
    import json
    
    try:
        video_file = PathLib(video_path).expanduser().resolve()
        
        if not video_file.exists():
            raise HTTPException(status_code=404, detail="Video file not found")
        
        # Use ffprobe to get video metadata
        ffprobe_cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_file)
        ]
        
        result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)
        
        # Extract useful information
        video_stream = next((s for s in metadata.get("streams", []) if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in metadata.get("streams", []) if s.get("codec_type") == "audio"), None)
        format_info = metadata.get("format", {})
        
        # Calculate FPS
        fps = 30.0  # default
        if video_stream:
            fps_parts = video_stream.get("r_frame_rate", "30/1").split("/")
            fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
        
        # Get bitrates
        video_bitrate = int(video_stream.get("bit_rate", 0)) if video_stream and video_stream.get("bit_rate") else 5000000
        audio_bitrate = int(audio_stream.get("bit_rate", 0)) if audio_stream and audio_stream.get("bit_rate") else 128000
        
        # Convert to kbps for processing
        video_bitrate_kbps = round(video_bitrate / 1000)
        audio_bitrate_kbps = round(audio_bitrate / 1000)
        
        # Determine resolution preset
        width = video_stream.get("width") if video_stream else None
        height = video_stream.get("height") if video_stream else None
        
        resolution_preset = ""
        if width and height:
            if height >= 1080:
                resolution_preset = "hd1080"
            elif height >= 720:
                resolution_preset = "hd720"
            elif height >= 480:
                resolution_preset = "hd480"
        
        # Build response with parameters formatted for /process endpoint
        params = {
            "metadata": {  # Full metadata info
                "file_path": str(video_file),
                "file_name": video_file.name,
                "file_size": int(format_info.get("size", 0)),
                "duration": float(format_info.get("duration", 0)),
                "width": width,
                "height": height,
                "fps": round(fps, 2),
                "codec": video_stream.get("codec_name") if video_stream else None,
                "has_audio": audio_stream is not None,
                "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
            },
            "params": {  # Parameters ready to use with /process
                # Video properties
                "fps": str(int(fps)),
                "bit_m_video": f"{video_bitrate_kbps}k",
                "bit_m_audio": f"{audio_bitrate_kbps}k",
                "width_height": resolution_preset if resolution_preset else "",
                
                # Default video processing values
                "scale": "iw:ih",
                "crop": "iw:ih",
                "metadata": "-1",  # Remove metadata
                "output": ".mp4",
                
                # Color/adjustments (defaults)
                "saturation": "1.0",
                "contrast": "1.0",
                "gamma": "1.0",
                "gamma_r": "1.0",
                "gamma_g": "1.0",
                "gamma_b": "1.0",
                "gamma_weight": "0.4",
                "vibrance": "0.0",
                "eq": "0.0",
                
                # Geometric transforms (defaults)
                "crop_width": "0",
                "crop_height": "0",
                "rotate": "0",
                "mirror_horizontally": "False",
                "mirror_vertically": "False",
                
                # Effects (defaults)
                "gblur": "0",
                "tmix_frames": "0",
                "noise": "0",
                "fade": "in:0:40",
                
                # Speed (defaults)
                "speed_video": "1.0*PTS",
                "speed_audio": "1.0",
                
                # Options
                "delete_input": "False",
                "random_config": "False",
            }
        }
        
        return params
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFprobe error: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/serve_video")
async def serve_video(video_path: str):
    """Serve a video file from the filesystem"""
    from pathlib import Path as PathLib
    
    try:
        video_file = PathLib(video_path).expanduser().resolve()
        
        # Security: only allow serving files within project or home directory
        home_dir = PathLib.home()
        project_dir = PathLib(__file__).parent
        
        if not (str(video_file).startswith(str(home_dir)) or str(video_file).startswith(str(project_dir))):
            raise HTTPException(status_code=403, detail="Access denied to this path")
        
        if not video_file.exists():
            raise HTTPException(status_code=404, detail="Video file not found")
        
        if not video_file.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
        
        # Return the video file with appropriate headers for video streaming
        return FileResponse(
            str(video_file),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Disposition": f'inline; filename="{video_file.name}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/job/{job_id}")
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get job status by ID"""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    job = await get_job(db, job_uuid)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": str(job.id),
        "job_type": job.job_type,
        "status": job.status,
        "progress_percentage": job.progress_percentage,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "failed_at": job.failed_at.isoformat() if job.failed_at else None,
        "error_message": job.error_message,
        "input_params": job.input_params,
        "output_result": job.output_result,
        "processing_time_seconds": job.processing_time_seconds
    }


class ProcessRequest(BaseModel):
    mode: str
    count: int
    # Generic catch-all (still supported)
    params: Optional[Dict[str, Any]] = None
    
    # Path parameters
    video_path: Optional[str] = None
    output_path: Optional[str] = None

    # Explicit overrides for all supported ffmpeg-related params
    fps: Optional[Union[str, Dict[str, Any]]] = None
    metadata: Optional[str] = None
    scale: Optional[str] = None
    crop: Optional[str] = None
    width_height: Optional[str] = None
    bit_m_audio: Optional[Union[str, Dict[str, Any]]] = None
    bit_m_video: Optional[Union[str, Dict[str, Any]]] = None
    crop_width: Optional[Union[str, Dict[str, Any]]] = None
    crop_height: Optional[Union[str, Dict[str, Any]]] = None
    fade: Optional[str] = None
    vibrance: Optional[Union[str, Dict[str, Any]]] = None
    gamma_weight: Optional[Union[str, Dict[str, Any]]] = None
    gamma_r: Optional[Union[str, Dict[str, Any]]] = None
    gamma_g: Optional[Union[str, Dict[str, Any]]] = None
    gamma_b: Optional[Union[str, Dict[str, Any]]] = None
    gamma: Optional[Union[str, Dict[str, Any]]] = None
    saturation: Optional[Union[str, Dict[str, Any]]] = None
    contrast: Optional[Union[str, Dict[str, Any]]] = None
    eq: Optional[Union[str, Dict[str, Any]]] = None
    rotate: Optional[Union[str, Dict[str, Any]]] = None
    speed_audio: Optional[Union[str, Dict[str, Any]]] = None
    speed_video: Optional[Union[str, Dict[str, Any]]] = None
    output: Optional[str] = None
    delete_input: Optional[Union[str, bool]] = None
    random_config: Optional[Union[str, bool]] = None
    mirror_horizontally: Optional[str] = None
    mirror_vertically: Optional[str] = None
    gblur: Optional[Union[str, Dict[str, Any]]] = None
    tmix_frames: Optional[Union[str, Dict[str, Any]]] = None
    noise: Optional[Union[str, Dict[str, Any]]] = None
    music_group_id: Optional[str] = None
    watermark_group_id: Optional[str] = None
    footage_group_id: Optional[str] = None
    music_volume: Optional[float] = None
    music_delete_video_audio: Optional[bool] = None
    watermark_size: Optional[float] = None
    watermark_opacity: Optional[float] = None
    footage_opacity: Optional[float] = None


@app.post("/process")
async def process_media(req: ProcessRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Process media with background task and database job tracking"""
    if ImagesAndVideoMassUniq is None:
        raise HTTPException(status_code=500, detail="Failed to load processing engine (startUniq.py)")

    # Build input params
    try:
        body = req.model_dump()  # pydantic v2
    except Exception:
        body = req.dict()  # fallback for pydantic v1
    
    # Optional group handling
    music_group_files: list[str] = []
    watermark_group_files: list[str] = []
    footage_group_files: list[str] = []

    music_group_files, music_group_summary, resolved_group_id = await resolve_music_group(req.music_group_id, db)
    if music_group_summary:
        body["music_group_id"] = resolved_group_id
        body["music_group"] = music_group_summary
        body["music_group_files"] = music_group_files

    watermark_group_files, watermark_group_summary, resolved_watermark_group_id = await resolve_watermark_group(req.watermark_group_id, db)
    if watermark_group_summary:
        body["watermark_group_id"] = resolved_watermark_group_id
        body["watermark_group"] = watermark_group_summary
        body["watermark_group_files"] = watermark_group_files

    footage_group_files, footage_group_summary, resolved_footage_group_id = await resolve_footage_group(req.footage_group_id, db)
    if footage_group_summary:
        body["footage_group_id"] = resolved_footage_group_id
        body["footage_group"] = footage_group_summary
        body["footage_group_files"] = footage_group_files
    
    # Create job in database
    job = await create_job(
        db=db,
        job_type="process",
        input_params=body,
        status="pending"
    )

    async def run_job():
        # Get a new database session for the background task
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as bg_db:
            try:
                # Update job status to processing
                await update_job_status(bg_db, job.id, "processing")
                
                # Build overrides from explicit fields + params
                overrides: Dict[str, Any] = {}
                skip_override_keys = {
                    "mode",
                    "count",
                    "params",
                    "music_group",
                    "music_group_files",
                    "music_group_id",
                    "music_volume",
                    "music_delete_video_audio",
                    "watermark_group",
                    "watermark_group_files",
                    "watermark_group_id",
                    "watermark_size",
                    "watermark_opacity",
                    "footage_group",
                    "footage_group_files",
                    "footage_group_id",
                    "footage_opacity",
                }
                for k, v in body.items():
                    if k in skip_override_keys:
                        continue
                    if v is not None:
                        overrides[k] = v
                music_group_files_local = body.get("music_group_files", [])
                watermark_group_files_local = body.get("watermark_group_files", [])
                footage_group_files_local = body.get("footage_group_files", [])
                music_group_summary = body.get("music_group")
                watermark_group_summary = body.get("watermark_group")
                footage_group_summary = body.get("footage_group")
                # Merge generic params last
                if req.params:
                    overrides.update(req.params)
                
                # Run the processing
                engine = ImagesAndVideoMassUniq()
                try:
                    engine.set_overrides(overrides)
                except Exception:
                    pass
                engine.start(req.mode, str(req.count))
                
                # Get reports
                try:
                    reports = engine.get_reports()
                except Exception:
                    reports = []
                
                # Extract video paths from reports
                video_paths = []
                if reports:
                    for report in reports:
                        if isinstance(report, dict) and report.get('output'):
                            video_paths.append(report['output'])
                
                base_video_paths = list(video_paths)
                processing_paths = list(video_paths)

                footage_outputs: list[Dict[str, Any]] = []
                footage_group_error: Optional[str] = None
                if footage_group_files_local:
                    footage_opacity_value = body.get("footage_opacity")
                    footage_outputs, footage_group_error = apply_footage_group_to_videos(
                        processing_paths,
                        footage_group_files_local,
                        footage_opacity_value,
                    )
                    if footage_outputs:
                        processing_paths = [
                            item["output_video"] for item in footage_outputs if item.get("output_video")
                        ]

                watermark_outputs: list[Dict[str, Any]] = []
                watermark_group_error: Optional[str] = None
                if watermark_group_files_local:
                    target_paths = processing_paths if processing_paths else base_video_paths
                    watermark_outputs, watermark_group_error = apply_watermark_group_to_videos(
                        target_paths,
                        watermark_group_files_local,
                        body.get("watermark_size"),
                        body.get("watermark_opacity"),
                    )
                    if watermark_outputs:
                        processing_paths = [
                            item["output_video"] for item in watermark_outputs if item.get("output_video")
                        ]

                music_outputs: list[Dict[str, Any]] = []
                music_group_error: Optional[str] = None
                if music_group_files_local:
                    target_paths = processing_paths if processing_paths else base_video_paths
                    music_outputs, music_group_error = apply_music_group_to_videos(
                        target_paths,
                        music_group_files_local,
                        body.get("music_volume"),
                        body.get("music_delete_video_audio"),
                    )
                    if music_outputs:
                        processing_paths = [
                            item["output_video"] for item in music_outputs if item.get("output_video")
                        ]

                final_video_paths = processing_paths if processing_paths else base_video_paths
                
                # Update job as completed
                await update_job_status(
                    bg_db, 
                    job.id, 
                    "completed",
                    output_result={
                        "reports": reports, 
                        "mode": req.mode, 
                        "count": req.count,
                        "videos": base_video_paths if base_video_paths else None,
                        "final_videos": final_video_paths if final_video_paths else None,
                        "music_group": music_group_summary,
                        "music_group_outputs": music_outputs if music_outputs else None,
                        "music_group_error": music_group_error,
                        "watermark_group": watermark_group_summary,
                        "watermark_group_outputs": watermark_outputs if watermark_outputs else None,
                        "watermark_group_error": watermark_group_error,
                        "footage_group": footage_group_summary,
                        "footage_group_outputs": footage_outputs if footage_outputs else None,
                        "footage_group_error": footage_group_error
                    }
                )
            except Exception as e:
                # Update job as failed
                await update_job_status(
                    bg_db,
                    job.id,
                    "failed",
                    error_message=str(e)
                )

    background_tasks.add_task(run_job)
    return {
        "status": "started", 
        "job_id": str(job.id),
        "mode": req.mode, 
        "count": req.count,
        "check_status_url": f"/job/{job.id}"
    }


@app.post("/process_sync")
async def process_media_sync(req: ProcessRequest, db: AsyncSession = Depends(get_db)):
    if ImagesAndVideoMassUniq is None:
        raise HTTPException(status_code=500, detail="Failed to load processing engine (startUniq.py)")

    engine = ImagesAndVideoMassUniq()
    # Build overrides from explicit fields + params
    overrides: Dict[str, Any] = {}
    try:
        body = req.model_dump()
    except Exception:
        body = req.dict()

    music_group_files: list[str] = []
    watermark_group_files: list[str] = []
    footage_group_files: list[str] = []

    music_group_files, music_group_summary, resolved_group_id = await resolve_music_group(req.music_group_id, db)
    if music_group_summary:
        body["music_group_id"] = resolved_group_id
        body["music_group"] = music_group_summary
        body["music_group_files"] = music_group_files

    skip_override_keys = {
        "mode",
        "count",
        "params",
        "music_group",
        "music_group_files",
        "music_group_id",
        "watermark_group",
        "watermark_group_files",
        "watermark_group_id",
        "footage_group",
        "footage_group_files",
        "footage_group_id"
    }
    for k, v in body.items():
        if k in skip_override_keys:
            continue
        if v is not None:
            overrides[k] = v
    music_group_summary = body.get("music_group")
    watermark_group_summary = body.get("watermark_group")
    footage_group_summary = body.get("footage_group")
    if req.params:
        overrides.update(req.params)

    try:
        engine.set_overrides(overrides)
    except Exception:
        pass

    engine.start(req.mode, str(req.count))
    # Gather structured reports
    try:
        reports = engine.get_reports()
    except Exception:
        reports = []

    video_paths = []
    if reports:
        for report in reports:
            if isinstance(report, dict) and report.get("output"):
                video_paths.append(report["output"])

    base_video_paths = list(video_paths)
    processing_paths = list(video_paths)

    footage_outputs: list[Dict[str, Any]] = []
    footage_group_error: Optional[str] = None
    if footage_group_files:
        footage_outputs, footage_group_error = apply_footage_group_to_videos(
            processing_paths,
            footage_group_files,
            body.get("footage_opacity"),
        )
        if footage_outputs:
            processing_paths = [
                item["output_video"] for item in footage_outputs if item.get("output_video")
            ]

    watermark_outputs: list[Dict[str, Any]] = []
    watermark_group_error: Optional[str] = None
    if watermark_group_files:
        target_paths = processing_paths if processing_paths else base_video_paths
        watermark_outputs, watermark_group_error = apply_watermark_group_to_videos(
            target_paths,
            watermark_group_files,
            body.get("watermark_size"),
            body.get("watermark_opacity"),
        )
        if watermark_outputs:
            processing_paths = [
                item["output_video"] for item in watermark_outputs if item.get("output_video")
            ]

    music_outputs: list[Dict[str, Any]] = []
    music_group_error: Optional[str] = None
    if music_group_files:
        target_paths = processing_paths if processing_paths else base_video_paths
        music_outputs, music_group_error = apply_music_group_to_videos(
            target_paths,
            music_group_files,
            body.get("music_volume"),
            body.get("music_delete_video_audio"),
        )
        if music_outputs:
            processing_paths = [
                item["output_video"] for item in music_outputs if item.get("output_video")
            ]

    final_video_paths = processing_paths if processing_paths else base_video_paths

    return {
        "status": "completed",
        "mode": req.mode,
        "count": req.count,
        "reports": reports,
        "videos": base_video_paths if base_video_paths else None,
        "final_videos": final_video_paths if final_video_paths else None,
        "music_group": music_group_summary,
        "music_group_outputs": music_outputs if music_outputs else None,
        "music_group_error": music_group_error,
        "watermark_group": watermark_group_summary,
        "watermark_group_outputs": watermark_outputs if watermark_outputs else None,
        "watermark_group_error": watermark_group_error,
        "footage_group": footage_group_summary,
        "footage_group_outputs": footage_outputs if footage_outputs else None,
        "footage_group_error": footage_group_error
    }


@app.post("/footages_add")
async def footages_add(background_tasks: BackgroundTasks):
    """Run STEP5 MassFootagesAdd script as a background task."""
    script_path = Path("/Users/maxsymonenko/tik_tok_forces_api/unicalizator/STEP5-MassFootagesAdd/code/massFootages.py").resolve()

    def run_script():
        # Use venv python if available, else fallback to system python
        venv_python = Path("/Users/maxsymonenko/tik_tok_forces_api/.venv/bin/python")
        python_bin = str(venv_python) if venv_python.exists() else sys.executable
        try:
            subprocess.run([python_bin, str(script_path)], cwd=str(script_path.parent), check=True)
        except Exception:
            pass

    background_tasks.add_task(run_script)
    return {"status": "started", "script": str(script_path)}


class FootagesRequest(BaseModel):
    video: str
    footage: str
    output_dir: Optional[str] = None


@app.post("/footages_add_sync")
async def footages_add_sync(req: FootagesRequest):
    script_path = Path("/Users/maxsymonenko/tik_tok_forces_api/unicalizator/STEP5-MassFootagesAdd/code/massFootages.py").resolve()
    venv_python = Path("/Users/maxsymonenko/tik_tok_forces_api/.venv/bin/python")
    python_bin = str(venv_python) if venv_python.exists() else sys.executable
    cmd = [python_bin, str(script_path), "--video", req.video, "--footage", req.footage]
    if req.output_dir:
        cmd += ["--output_dir", req.output_dir]
    try:
        result = subprocess.run(cmd, cwd=str(script_path.parent), check=True, capture_output=True, text=True)
        output_path = result.stdout.strip().splitlines()[-1] if result.stdout else None
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.stderr or str(e))
    return {"status": "completed", "video": req.video, "footage": req.footage, "output": output_path}


class MusicRequest(BaseModel):
    video: str
    music: str
    output_dir: Optional[str] = None
    delete_video_audio: Optional[bool] = True
    music_volume: Optional[float] = 1.0


@app.post("/music_add_sync")
async def music_add_sync(req: MusicRequest):
    script_path = Path("/Users/maxsymonenko/tik_tok_forces_api/STEP4-MassMusicAdd/code/massMusic.py").resolve()
    venv_python = Path("/Users/maxsymonenko/tik_tok_forces_api/.venv/bin/python")
    python_bin = str(venv_python) if venv_python.exists() else sys.executable
    # Validate input files exist
    if not Path(req.video).expanduser().exists():
        raise HTTPException(status_code=400, detail=f"Video file not found: {req.video}")
    if not Path(req.music).expanduser().exists():
        raise HTTPException(status_code=400, detail=f"Music file not found: {req.music}")
    cmd = [python_bin, str(script_path), "--video", req.video, "--music", req.music]
    if req.output_dir:
        cmd += ["--output_dir", req.output_dir]
    if req.delete_video_audio is not None:
        cmd += ["--delete_video_audio", "true" if req.delete_video_audio else "false"]
    if req.music_volume is not None:
        cmd += ["--music_volume", str(req.music_volume)]
    try:
        result = subprocess.run(cmd, cwd=str(script_path.parent), check=True, capture_output=True, text=True)
        output_path = result.stdout.strip().splitlines()[-1] if result.stdout else None
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.stderr or str(e))
    return {"status": "completed", "video": req.video, "music": req.music, "output": output_path}


class WatermarkRequest(BaseModel):
    video: str
    watermark: str
    output_dir: Optional[str] = None
    size: Optional[float] = 1.0
    position: Optional[str] = "top-right"
    opacity: Optional[float] = 1.0
    delete_watermark_audio: Optional[bool] = True


@app.post("/watermark_add_sync")
async def watermark_add_sync(req: WatermarkRequest):
    script_path = Path("/Users/maxsymonenko/tik_tok_forces_api/STEP20-WaterMarkOverlays/code/waterMarkOverlays.py").resolve()
    venv_python = Path("/Users/maxsymonenko/tik_tok_forces_api/.venv/bin/python")
    python_bin = str(venv_python) if venv_python.exists() else sys.executable
    # Validate input files
    if not Path(req.video).expanduser().exists():
        raise HTTPException(status_code=400, detail=f"Video file not found: {req.video}")
    if not Path(req.watermark).expanduser().exists():
        raise HTTPException(status_code=400, detail=f"Watermark file not found: {req.watermark}")
    cmd = [python_bin, str(script_path), "--video", req.video, "--watermark", req.watermark]
    if req.output_dir:
        cmd += ["--output_dir", req.output_dir]
    if req.size is not None:
        cmd += ["--size", str(req.size)]
    if req.position:
        cmd += ["--position", req.position]
    if req.opacity is not None:
        cmd += ["--opacity", str(req.opacity)]
    if req.delete_watermark_audio is not None:
        cmd += ["--delete_watermark_audio", "true" if req.delete_watermark_audio else "false"]
    try:
        result = subprocess.run(cmd, cwd=str(script_path.parent), check=True, capture_output=True, text=True)
        output_path = result.stdout.strip().splitlines()[-1] if result.stdout else None
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.stderr or str(e))
    return {"status": "completed", "video": req.video, "watermark": req.watermark, "output": output_path}


class SubtitlesRequest(BaseModel):
    video: str
    subtitle: Optional[str] = None
    subtitle_text: Optional[str] = None
    output_dir: Optional[str] = None
    size: Optional[float] = 1.0
    position: Optional[str] = "bottom-center"
    opacity: Optional[float] = 1.0
    delete_subtitle_audio: Optional[bool] = True
    font_size: Optional[int] = 48
    font_color: Optional[str] = "white"
    auto_transcribe: Optional[bool] = False
    whisper_model: Optional[str] = "base"
    use_srt: Optional[bool] = False


@app.post("/subtitles_add_sync")
async def subtitles_add_sync(req: SubtitlesRequest):
    script_path = Path("/Users/maxsymonenko/tik_tok_forces_api/STEP19-SubtitlesOverlays/code/subtitlesOverlays.py").resolve()
    venv_python = Path("/Users/maxsymonenko/tik_tok_forces_api/.venv/bin/python")
    python_bin = str(venv_python) if venv_python.exists() else sys.executable
    # Validate input files
    if not Path(req.video).expanduser().exists():
        raise HTTPException(status_code=400, detail=f"Video file not found: {req.video}")
    if not req.subtitle_text and not req.subtitle and not req.auto_transcribe:
        raise HTTPException(status_code=400, detail="Either subtitle (video path), subtitle_text (text string), or auto_transcribe must be provided")
    if req.subtitle and not Path(req.subtitle).expanduser().exists():
        raise HTTPException(status_code=400, detail=f"Subtitle file not found: {req.subtitle}")
    
    cmd = [python_bin, str(script_path), "--video", req.video]
    if req.subtitle:
        cmd += ["--subtitle", req.subtitle]
    if req.subtitle_text:
        cmd += ["--subtitle_text", req.subtitle_text]
    if req.output_dir:
        cmd += ["--output_dir", req.output_dir]
    if req.size is not None:
        cmd += ["--size", str(req.size)]
    if req.position:
        cmd += ["--position", req.position]
    if req.opacity is not None:
        cmd += ["--opacity", str(req.opacity)]
    if req.delete_subtitle_audio is not None:
        cmd += ["--delete_subtitle_audio", "true" if req.delete_subtitle_audio else "false"]
    if req.font_size is not None:
        cmd += ["--font_size", str(req.font_size)]
    if req.font_color:
        cmd += ["--font_color", req.font_color]
    if req.auto_transcribe is not None:
        cmd += ["--auto_transcribe", "true" if req.auto_transcribe else "false"]
    if req.whisper_model:
        cmd += ["--whisper_model", req.whisper_model]
    if req.use_srt is not None:
        cmd += ["--use_srt", "true" if req.use_srt else "false"]
    
    print(f"[SUBTITLES] Starting: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=str(script_path.parent), check=True, capture_output=True, text=True)
        print(f"[SUBTITLES] stdout: {result.stdout}")
        print(f"[SUBTITLES] stderr: {result.stderr}")
        output_path = result.stdout.strip().splitlines()[-1] if result.stdout else None
    except subprocess.CalledProcessError as e:
        print(f"[SUBTITLES] Error: {e.stderr}")
        raise HTTPException(status_code=500, detail=e.stderr or str(e))
    return {"status": "completed", "video": req.video, "subtitle": req.subtitle or req.subtitle_text, "output": output_path}


@app.post("/subtitles_add_async")
async def subtitles_add_async(req: SubtitlesRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Background version for long-running transcriptions with database tracking."""
    
    # Build input params
    try:
        body = req.model_dump()
    except Exception:
        body = req.dict()
    
    # Create job in database
    job = await create_job(
        db=db,
        job_type="subtitles_add",
        input_params=body,
        status="pending"
    )
    
    async def run_job():
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as bg_db:
            try:
                await update_job_status(bg_db, job.id, "processing")
                
                script_path = Path("/Users/maxsymonenko/tik_tok_forces_api/STEP19-SubtitlesOverlays/code/subtitlesOverlays.py").resolve()
                venv_python = Path("/Users/maxsymonenko/tik_tok_forces_api/.venv/bin/python")
                python_bin = str(venv_python) if venv_python.exists() else sys.executable
                
                cmd = [python_bin, str(script_path), "--video", req.video]
                if req.subtitle:
                    cmd += ["--subtitle", req.subtitle]
                if req.subtitle_text:
                    cmd += ["--subtitle_text", req.subtitle_text]
                if req.output_dir:
                    cmd += ["--output_dir", req.output_dir]
                if req.size is not None:
                    cmd += ["--size", str(req.size)]
                if req.position:
                    cmd += ["--position", req.position]
                if req.opacity is not None:
                    cmd += ["--opacity", str(req.opacity)]
                if req.delete_subtitle_audio is not None:
                    cmd += ["--delete_subtitle_audio", "true" if req.delete_subtitle_audio else "false"]
                if req.font_size is not None:
                    cmd += ["--font_size", str(req.font_size)]
                if req.font_color:
                    cmd += ["--font_color", req.font_color]
                if req.auto_transcribe is not None:
                    cmd += ["--auto_transcribe", "true" if req.auto_transcribe else "false"]
                if req.whisper_model:
                    cmd += ["--whisper_model", req.whisper_model]
                if req.use_srt is not None:
                    cmd += ["--use_srt", "true" if req.use_srt else "false"]
                
                print(f"[JOB {job.id}] Starting: {' '.join(cmd)}")
                env = os.environ.copy()
                env['PYTHONUNBUFFERED'] = '1'
                result = subprocess.run(cmd, cwd=str(script_path.parent), check=True, capture_output=True, text=True, env=env)
                print(f"[JOB {job.id}] stdout: {result.stdout}")
                print(f"[JOB {job.id}] stderr: {result.stderr}")
                output_path = result.stdout.strip().splitlines()[-1] if result.stdout else None
                
                await update_job_status(
                    bg_db,
                    job.id,
                    "completed",
                    output_result={
                        "output": output_path,
                        "video": req.video,
                        "subtitle": req.subtitle or req.subtitle_text,
                        "videos": [output_path] if output_path else None
                    }
                )
                print(f"[JOB {job.id}] Completed: {output_path}")
            except Exception as e:
                await update_job_status(
                    bg_db,
                    job.id,
                    "failed",
                    error_message=str(e)
                )
                print(f"[JOB {job.id}] Failed: {e}")
    
    background_tasks.add_task(run_job)
    return {"status": "started", "job_id": str(job.id), "check_status_url": f"/job/{job.id}"}


# ============================================================================
# ASSET MANAGEMENT (Musics, Watermarks, Footages) CRUD
# ============================================================================

# Define storage directories
PROJECT_ROOT = Path(__file__).parent
ASSETS_DIR = PROJECT_ROOT / "assets"
MUSICS_DIR = ASSETS_DIR / "musics"
WATERMARKS_DIR = ASSETS_DIR / "watermarks"
FOOTAGES_DIR = ASSETS_DIR / "footages"

# Ensure directories exist
for dir_path in [ASSETS_DIR, MUSICS_DIR, WATERMARKS_DIR, FOOTAGES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


@app.get("/assets/musics")
async def list_musics():
    """List all music files"""
    musics = []
    if MUSICS_DIR.exists():
        for file_path in MUSICS_DIR.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg']:
                stat = file_path.stat()
                musics.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": stat.st_mtime,
                    "extension": file_path.suffix
                })
    return {"musics": sorted(musics, key=lambda x: x["name"])}


@app.post("/assets/musics/upload")
async def upload_music(file: UploadFile = File(...)):
    """Upload a music file"""
    # Validate file extension
    allowed_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg']
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}")
    
    # Save file
    file_path = MUSICS_DIR / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        stat = file_path.stat()
        return {
            "status": "uploaded",
            "name": file.filename,
            "path": str(file_path),
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@app.delete("/assets/musics/{filename}")
async def delete_music(filename: str):
    """Delete a music file"""
    # Security: prevent path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = MUSICS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        file_path.unlink()
        return {"status": "deleted", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


class RenameMusicRequest(BaseModel):
    new_name: str


@app.patch("/assets/musics/{filename}/rename")
async def rename_music(filename: str, req: RenameMusicRequest):
    """Rename a music file"""
    # Security: prevent path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if '..' in req.new_name or '/' in req.new_name or '\\' in req.new_name:
        raise HTTPException(status_code=400, detail="Invalid new filename")
    
    old_file_path = MUSICS_DIR / filename
    if not old_file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Validate new name has valid extension
    old_ext = old_file_path.suffix
    new_name_with_ext = req.new_name
    if not new_name_with_ext.endswith(old_ext):
        new_name_with_ext += old_ext
    
    new_file_path = MUSICS_DIR / new_name_with_ext
    if new_file_path.exists() and new_file_path != old_file_path:
        raise HTTPException(status_code=400, detail="A file with this name already exists")
    
    try:
        old_file_path.rename(new_file_path)
        return {"status": "renamed", "old_name": filename, "new_name": new_name_with_ext}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rename file: {str(e)}")


@app.get("/assets/watermarks")
async def list_watermarks():
    """List all watermark files"""
    watermarks = []
    if WATERMARKS_DIR.exists():
        for file_path in WATERMARKS_DIR.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv', '.png', '.jpg', '.jpeg', '.webp']:
                stat = file_path.stat()
                watermarks.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": stat.st_mtime,
                    "extension": file_path.suffix
                })
    return {"watermarks": sorted(watermarks, key=lambda x: x["name"])}


@app.post("/assets/watermarks/upload")
async def upload_watermark(file: UploadFile = File(...)):
    """Upload a watermark file"""
    # Validate file extension
    allowed_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.png', '.jpg', '.jpeg', '.webp']
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}")
    
    # Save file
    file_path = WATERMARKS_DIR / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        stat = file_path.stat()
        return {
            "status": "uploaded",
            "name": file.filename,
            "path": str(file_path),
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@app.delete("/assets/watermarks/{filename}")
async def delete_watermark(filename: str):
    """Delete a watermark file"""
    # Security: prevent path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = WATERMARKS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        file_path.unlink()
        return {"status": "deleted", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@app.get("/assets/footages")
async def list_footages():
    """List all footage files"""
    footages = []
    if FOOTAGES_DIR.exists():
        for file_path in FOOTAGES_DIR.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
                stat = file_path.stat()
                footages.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": stat.st_mtime,
                    "extension": file_path.suffix
                })
    return {"footages": sorted(footages, key=lambda x: x["name"])}


@app.post("/assets/footages/upload")
async def upload_footage(file: UploadFile = File(...)):
    """Upload a footage file"""
    # Validate file extension
    allowed_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}")
    
    # Save file
    file_path = FOOTAGES_DIR / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        stat = file_path.stat()
        return {
            "status": "uploaded",
            "name": file.filename,
            "path": str(file_path),
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@app.delete("/assets/footages/{filename}")
async def delete_footage(filename: str):
    """Delete a footage file"""
    # Security: prevent path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = FOOTAGES_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        file_path.unlink()
        return {"status": "deleted", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


# ============================================================================
# MUSIC GROUPS MANAGEMENT
# ============================================================================

class CreateGroupRequest(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = None


class UpdateGroupRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class AddMusicToGroupRequest(BaseModel):
    music_filename: str
    order: Optional[int] = None


class AddWatermarkToGroupRequest(BaseModel):
    watermark_filename: str
    order: Optional[int] = None


class AddFootageToGroupRequest(BaseModel):
    footage_filename: str
    order: Optional[int] = None


def apply_music_group_to_videos(
    video_paths: list[str],
    music_files: list[str],
    music_volume: Optional[float] = None,
    delete_video_audio: Optional[bool] = None,
) -> tuple[list[Dict[str, Any]], Optional[str]]:
    """Apply music files to generated videos using STEP4 massMusic script."""
    outputs: list[Dict[str, Any]] = []
    error: Optional[str] = None

    if not music_files:
        return outputs, "Music group contains no valid files."

    if not video_paths:
        return outputs, "No generated videos available to apply the music group."

    script_path = CODE_DIR4 / "massMusic.py"
    if not script_path.exists():
        return outputs, "STEP4 massMusic script not found."

    venv_python = Path("/Users/maxsymonenko/tik_tok_forces_api/.venv/bin/python")
    python_bin = str(venv_python) if venv_python.exists() else sys.executable

    for idx, video_path in enumerate(video_paths):
        try:
            video_file = Path(video_path).expanduser().resolve()
            if not video_file.exists():
                continue

            music_file = Path(music_files[idx % len(music_files)]).expanduser().resolve()
            if not music_file.exists():
                continue

            output_dir = video_file.parent / "music_group_outputs"
            output_dir.mkdir(parents=True, exist_ok=True)

            delete_audio_flag = True if delete_video_audio is None else bool(delete_video_audio)

            cmd = [
                python_bin,
                str(script_path),
                "--video",
                str(video_file),
                "--music",
                str(music_file),
                "--output_dir",
                str(output_dir),
                "--delete_video_audio",
                "true" if delete_audio_flag else "false"
            ]
            if music_volume is not None:
                cmd += ["--music_volume", str(music_volume)]
            try:
                result = subprocess.run(
                    cmd,
                    cwd=str(script_path.parent),
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                error = e.stderr or str(e)
                break

            output_file = output_dir / f"output_{video_file.name}"
            outputs.append({
                "input_video": str(video_file),
                "music_file": str(music_file),
                "output_video": str(output_file),
                "stdout": result.stdout.strip() if result.stdout else None,
                "stderr": result.stderr.strip() if result.stderr else None
            })
        except Exception as exc:
            error = str(exc)
            break

    return outputs, error


def apply_watermark_group_to_videos(
    video_paths: list[str],
    watermark_files: list[str],
    watermark_size: Optional[float] = None,
    watermark_opacity: Optional[float] = None
) -> tuple[list[Dict[str, Any]], Optional[str]]:
    """Apply watermark overlays to videos using STEP20 WaterMarkOverlays script."""
    outputs: list[Dict[str, Any]] = []
    error: Optional[str] = None

    if not watermark_files:
        return outputs, "Watermark group contains no valid files."

    if not video_paths:
        return outputs, "No generated videos available to apply the watermark group."

    script_path = CODE_DIR20 / "waterMarkOverlays.py"
    if not script_path.exists():
        return outputs, "STEP20 WaterMarkOverlays script not found."

    venv_python = Path("/Users/maxsymonenko/tik_tok_forces_api/.venv/bin/python")
    python_bin = str(venv_python) if venv_python.exists() else sys.executable

    for idx, video_path in enumerate(video_paths):
        try:
            video_file = Path(video_path).expanduser().resolve()
            if not video_file.exists():
                continue

            watermark_file = Path(watermark_files[idx % len(watermark_files)]).expanduser().resolve()
            if not watermark_file.exists():
                continue

            output_dir = video_file.parent / "watermark_group_outputs"
            output_dir.mkdir(parents=True, exist_ok=True)

            size_value = str(watermark_size) if watermark_size is not None else "1.0"
            opacity_value = str(watermark_opacity) if watermark_opacity is not None else "1.0"

            cmd = [
                python_bin,
                str(script_path),
                "--video",
                str(video_file),
                "--watermark",
                str(watermark_file),
                "--output_dir",
                str(output_dir),
                "--size",
                size_value,
                "--position",
                "top-right",
                "--opacity",
                opacity_value,
                "--delete_watermark_audio",
                "true",
            ]

            try:
                result = subprocess.run(
                    cmd,
                    cwd=str(script_path.parent),
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                error = e.stderr or str(e)
                break

            output_file = output_dir / f"output_{video_file.name}"
            outputs.append({
                "input_video": str(video_file),
                "watermark_file": str(watermark_file),
                "output_video": str(output_file),
                "stdout": result.stdout.strip() if result.stdout else None,
                "stderr": result.stderr.strip() if result.stderr else None
            })
        except Exception as exc:
            error = str(exc)
            break

    return outputs, error


def apply_footage_group_to_videos(
    video_paths: list[str],
    footage_files: list[str],
    footage_opacity: Optional[float] = None
) -> tuple[list[Dict[str, Any]], Optional[str]]:
    """Apply footage overlays to videos using STEP5 MassFootagesAdd script."""
    outputs: list[Dict[str, Any]] = []
    error: Optional[str] = None

    if not footage_files:
        return outputs, "Footage group contains no valid files."

    if not video_paths:
        return outputs, "No generated videos available to apply the footage group."

    script_path = CODE_DIR2 / "massFootages.py"
    if not script_path.exists():
        return outputs, "STEP5 MassFootagesAdd script not found."

    venv_python = Path("/Users/maxsymonenko/tik_tok_forces_api/.venv/bin/python")
    python_bin = str(venv_python) if venv_python.exists() else sys.executable

    for idx, video_path in enumerate(video_paths):
        try:
            video_file = Path(video_path).expanduser().resolve()
            if not video_file.exists():
                continue

            footage_file = Path(footage_files[idx % len(footage_files)]).expanduser().resolve()
            if not footage_file.exists():
                continue

            output_dir = video_file.parent / "footage_group_outputs"
            output_dir.mkdir(parents=True, exist_ok=True)

            cmd = [
                python_bin,
                str(script_path),
                "--video",
                str(video_file),
                "--footage",
                str(footage_file),
                "--output_dir",
                str(output_dir),
            ]
            if footage_opacity is not None:
                cmd += ["--opacity", str(footage_opacity)]

            try:
                result = subprocess.run(
                    cmd,
                    cwd=str(script_path.parent),
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                error = e.stderr or str(e)
                break

            output_file = output_dir / f"output_{video_file.name}"
            outputs.append({
                "input_video": str(video_file),
                "footage_file": str(footage_file),
                "output_video": str(output_file),
                "stdout": result.stdout.strip() if result.stdout else None,
                "stderr": result.stderr.strip() if result.stderr else None
            })
        except Exception as exc:
            error = str(exc)
            break

    return outputs, error


async def resolve_music_group(music_group_id: Optional[str], db: AsyncSession) -> tuple[list[str], Optional[Dict[str, Any]], Optional[str]]:
    """Validate and load music group information."""
    if not music_group_id:
        return [], None, None

    try:
        music_group_uuid = uuid.UUID(music_group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid music_group_id format")

    group = await get_music_group(db, music_group_uuid)
    if not group:
        raise HTTPException(status_code=404, detail="Music group not found")

    members_summary = []
    music_group_files: list[str] = []
    missing_files: list[str] = []

    sorted_members = sorted(group.members, key=lambda m: (m.order if m.order is not None else 0, m.music_filename))
    for member in sorted_members:
        file_path = MUSICS_DIR / member.music_filename
        exists = file_path.exists()
        member_info = {
            "filename": member.music_filename,
            "order": member.order,
            "path": str(file_path),
            "exists": exists
        }
        members_summary.append(member_info)
        if exists:
            music_group_files.append(str(file_path))
        else:
            missing_files.append(member.music_filename)

    if not music_group_files:
        raise HTTPException(status_code=400, detail="Music group has no available music files on disk")

    summary = {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "color": group.color,
        "member_count": len(members_summary),
        "members": members_summary,
        "missing_files": missing_files
    }

    return music_group_files, summary, str(group.id)


async def resolve_watermark_group(watermark_group_id: Optional[str], db: AsyncSession) -> tuple[list[str], Optional[Dict[str, Any]], Optional[str]]:
    if not watermark_group_id:
        return [], None, None

    try:
        group_uuid = uuid.UUID(watermark_group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid watermark_group_id format")

    group = await get_watermark_group(db, group_uuid)
    if not group:
        raise HTTPException(status_code=404, detail="Watermark group not found")

    members_summary: list[Dict[str, Any]] = []
    watermark_files: list[str] = []
    missing_files: list[str] = []

    sorted_members = sorted(group.members, key=lambda m: (m.order if m.order is not None else 0, m.watermark_filename))
    for member in sorted_members:
        file_path = WATERMARKS_DIR / member.watermark_filename
        exists = file_path.exists()
        members_summary.append({
            "filename": member.watermark_filename,
            "order": member.order,
            "path": str(file_path),
            "exists": exists
        })
        if exists:
            watermark_files.append(str(file_path))
        else:
            missing_files.append(member.watermark_filename)

    if not watermark_files:
        raise HTTPException(status_code=400, detail="Watermark group has no available files on disk")

    summary = {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "color": group.color,
        "member_count": len(members_summary),
        "members": members_summary,
        "missing_files": missing_files
    }

    return watermark_files, summary, str(group.id)


async def resolve_footage_group(footage_group_id: Optional[str], db: AsyncSession) -> tuple[list[str], Optional[Dict[str, Any]], Optional[str]]:
    if not footage_group_id:
        return [], None, None

    try:
        group_uuid = uuid.UUID(footage_group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid footage_group_id format")

    group = await get_footage_group(db, group_uuid)
    if not group:
        raise HTTPException(status_code=404, detail="Footage group not found")

    members_summary: list[Dict[str, Any]] = []
    footage_files: list[str] = []
    missing_files: list[str] = []

    sorted_members = sorted(group.members, key=lambda m: (m.order if m.order is not None else 0, m.footage_filename))
    for member in sorted_members:
        file_path = FOOTAGES_DIR / member.footage_filename
        exists = file_path.exists()
        members_summary.append({
            "filename": member.footage_filename,
            "order": member.order,
            "path": str(file_path),
            "exists": exists
        })
        if exists:
            footage_files.append(str(file_path))
        else:
            missing_files.append(member.footage_filename)

    if not footage_files:
        raise HTTPException(status_code=400, detail="Footage group has no available files on disk")

    summary = {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "color": group.color,
        "member_count": len(members_summary),
        "members": members_summary,
        "missing_files": missing_files
    }

    return footage_files, summary, str(group.id)


@app.get("/assets/musics/groups")
async def list_music_groups(db: AsyncSession = Depends(get_db)):
    """List all music groups with their members"""
    groups = await get_all_music_groups(db)
    return {
        "groups": [
            {
                "id": str(group.id),
                "name": group.name,
                "description": group.description,
                "color": group.color,
                "member_count": len(group.members),
                "members": [
                    {
                        "music_filename": member.music_filename,
                        "order": member.order,
                        "added_at": member.added_at.isoformat() if member.added_at else None
                    }
                    for member in sorted(group.members, key=lambda m: m.order)
                ],
                "created_at": group.created_at.isoformat() if group.created_at else None,
                "updated_at": group.updated_at.isoformat() if group.updated_at else None
            }
            for group in groups
        ]
    }


@app.post("/assets/musics/groups")
async def create_group(req: CreateGroupRequest, db: AsyncSession = Depends(get_db)):
    """Create a new music group"""
    try:
        group = await create_music_group(
            db=db,
            name=req.name,
            description=req.description,
            color=req.color
        )
        return {
            "id": str(group.id),
            "name": group.name,
            "description": group.description,
            "color": group.color,
            "member_count": 0,
            "created_at": group.created_at.isoformat() if group.created_at else None
        }
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="A group with this name already exists")
        raise HTTPException(status_code=500, detail=f"Failed to create group: {str(e)}")


@app.get("/assets/musics/groups/{group_id}")
async def get_group(group_id: str, db: AsyncSession = Depends(get_db)):
    """Get a music group by ID"""
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")
    
    group = await get_music_group(db, group_uuid)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "color": group.color,
        "member_count": len(group.members),
        "members": [
            {
                "music_filename": member.music_filename,
                "order": member.order,
                "added_at": member.added_at.isoformat() if member.added_at else None
            }
            for member in sorted(group.members, key=lambda m: m.order)
        ],
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None
    }


@app.patch("/assets/musics/groups/{group_id}")
async def update_group(group_id: str, req: UpdateGroupRequest, db: AsyncSession = Depends(get_db)):
    """Update a music group"""
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")
    
    group = await update_music_group(
        db=db,
        group_id=group_uuid,
        name=req.name,
        description=req.description,
        color=req.color
    )
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "color": group.color,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None
    }


@app.delete("/assets/musics/groups/{group_id}")
async def delete_group(group_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a music group"""
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")
    
    deleted = await delete_music_group(db, group_uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return {"status": "deleted", "group_id": group_id}


@app.post("/assets/musics/groups/{group_id}/members")
async def add_member_to_group(group_id: str, req: AddMusicToGroupRequest, db: AsyncSession = Depends(get_db)):
    """Add a music file to a group"""
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")
    
    # Verify music file exists
    music_path = MUSICS_DIR / req.music_filename
    if not music_path.exists():
        raise HTTPException(status_code=404, detail="Music file not found")
    
    member = await add_music_to_group(
        db=db,
        group_id=group_uuid,
        music_filename=req.music_filename,
        order=req.order
    )
    
    if not member:
        # Check if group exists or if already in group
        group = await get_music_group(db, group_uuid)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        raise HTTPException(status_code=400, detail="Music file already in this group")
    
    return {
        "status": "added",
        "group_id": group_id,
        "music_filename": req.music_filename,
        "order": member.order
    }


@app.delete("/assets/musics/groups/{group_id}/members/{music_filename}")
async def remove_member_from_group(group_id: str, music_filename: str, db: AsyncSession = Depends(get_db)):
    """Remove a music file from a group"""
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")
    
    # Security: prevent path traversal
    if '..' in music_filename or '/' in music_filename or '\\' in music_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    removed = await remove_music_from_group(
        db=db,
        group_id=group_uuid,
        music_filename=music_filename
    )
    
    if not removed:
        raise HTTPException(status_code=404, detail="Music file not found in group")
    
    return {"status": "removed", "group_id": group_id, "music_filename": music_filename}


@app.get("/assets/musics/{music_filename}/groups")
async def get_groups_for_music(music_filename: str, db: AsyncSession = Depends(get_db)):
    """Get all groups that contain a specific music file"""
    # Security: prevent path traversal
    if '..' in music_filename or '/' in music_filename or '\\' in music_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    groups = await get_music_groups_for_file(db, music_filename)
    return {
        "music_filename": music_filename,
        "groups": [
            {
                "id": str(group.id),
                "name": group.name,
                "description": group.description,
                "color": group.color
            }
            for group in groups
        ]
    }


# ============================================================================
# WATERMARK GROUPS MANAGEMENT
# ============================================================================

@app.get("/assets/watermarks/groups")
async def list_watermark_groups(db: AsyncSession = Depends(get_db)):
    groups = await get_all_watermark_groups(db)
    return {
        "groups": [
            {
                "id": str(group.id),
                "name": group.name,
                "description": group.description,
                "color": group.color,
                "member_count": len(group.members),
                "members": [
                    {
                        "watermark_filename": member.watermark_filename,
                        "order": member.order,
                        "added_at": member.added_at.isoformat() if member.added_at else None
                    }
                    for member in sorted(group.members, key=lambda m: m.order if m.order is not None else 0)
                ],
                "created_at": group.created_at.isoformat() if group.created_at else None,
                "updated_at": group.updated_at.isoformat() if group.updated_at else None
            }
            for group in groups
        ]
    }


@app.post("/assets/watermarks/groups")
async def create_watermark_group_endpoint(req: CreateGroupRequest, db: AsyncSession = Depends(get_db)):
    try:
        group = await create_watermark_group(
            db=db,
            name=req.name,
            description=req.description,
            color=req.color
        )
        return {
            "id": str(group.id),
            "name": group.name,
            "description": group.description,
            "color": group.color,
            "member_count": 0,
            "created_at": group.created_at.isoformat() if group.created_at else None
        }
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="A watermark group with this name already exists")
        raise HTTPException(status_code=500, detail=f"Failed to create watermark group: {str(e)}")


@app.get("/assets/watermarks/groups/{group_id}")
async def get_watermark_group_endpoint(group_id: str, db: AsyncSession = Depends(get_db)):
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")

    group = await get_watermark_group(db, group_uuid)
    if not group:
        raise HTTPException(status_code=404, detail="Watermark group not found")

    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "color": group.color,
        "member_count": len(group.members),
        "members": [
            {
                "watermark_filename": member.watermark_filename,
                "order": member.order,
                "added_at": member.added_at.isoformat() if member.added_at else None
            }
            for member in sorted(group.members, key=lambda m: m.order if m.order is not None else 0)
        ],
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None
    }


@app.patch("/assets/watermarks/groups/{group_id}")
async def update_watermark_group_endpoint(group_id: str, req: UpdateGroupRequest, db: AsyncSession = Depends(get_db)):
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")

    group = await update_watermark_group(
        db=db,
        group_id=group_uuid,
        name=req.name,
        description=req.description,
        color=req.color
    )

    if not group:
        raise HTTPException(status_code=404, detail="Watermark group not found")

    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "color": group.color,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None
    }


@app.delete("/assets/watermarks/groups/{group_id}")
async def delete_watermark_group_endpoint(group_id: str, db: AsyncSession = Depends(get_db)):
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")

    deleted = await delete_watermark_group(db, group_uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Watermark group not found")

    return {"status": "deleted", "group_id": group_id}


@app.post("/assets/watermarks/groups/{group_id}/members")
async def add_watermark_member(group_id: str, req: AddWatermarkToGroupRequest, db: AsyncSession = Depends(get_db)):
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")

    if '..' in req.watermark_filename or '/' in req.watermark_filename or '\\' in req.watermark_filename:
        raise HTTPException(status_code=400, detail="Invalid watermark filename")

    watermark_path = WATERMARKS_DIR / req.watermark_filename
    if not watermark_path.exists():
        raise HTTPException(status_code=404, detail="Watermark file not found")

    member = await add_watermark_to_group(
        db=db,
        group_id=group_uuid,
        watermark_filename=req.watermark_filename,
        order=req.order
    )

    if not member:
        group = await get_watermark_group(db, group_uuid)
        if not group:
            raise HTTPException(status_code=404, detail="Watermark group not found")
        raise HTTPException(status_code=400, detail="Watermark already in this group")

    return {
        "status": "added",
        "group_id": group_id,
        "watermark_filename": req.watermark_filename,
        "order": member.order
    }


@app.delete("/assets/watermarks/groups/{group_id}/members/{watermark_filename}")
async def remove_watermark_member(group_id: str, watermark_filename: str, db: AsyncSession = Depends(get_db)):
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")

    if '..' in watermark_filename or '/' in watermark_filename or '\\' in watermark_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    removed = await remove_watermark_from_group(
        db=db,
        group_id=group_uuid,
        watermark_filename=watermark_filename
    )

    if not removed:
        raise HTTPException(status_code=404, detail="Watermark file not found in group")

    return {"status": "removed", "group_id": group_id, "watermark_filename": watermark_filename}


@app.get("/assets/watermarks/{watermark_filename}/groups")
async def get_groups_for_watermark(watermark_filename: str, db: AsyncSession = Depends(get_db)):
    if '..' in watermark_filename or '/' in watermark_filename or '\\' in watermark_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    groups = await get_watermark_groups_for_file(db, watermark_filename)
    return {
        "watermark_filename": watermark_filename,
        "groups": [
            {
                "id": str(group.id),
                "name": group.name,
                "description": group.description,
                "color": group.color
            }
            for group in groups
        ]
    }


# ============================================================================
# FOOTAGE GROUPS MANAGEMENT
# ============================================================================

@app.get("/assets/footages/groups")
async def list_footage_groups(db: AsyncSession = Depends(get_db)):
    groups = await get_all_footage_groups(db)
    return {
        "groups": [
            {
                "id": str(group.id),
                "name": group.name,
                "description": group.description,
                "color": group.color,
                "member_count": len(group.members),
                "members": [
                    {
                        "footage_filename": member.footage_filename,
                        "order": member.order,
                        "added_at": member.added_at.isoformat() if member.added_at else None
                    }
                    for member in sorted(group.members, key=lambda m: m.order if m.order is not None else 0)
                ],
                "created_at": group.created_at.isoformat() if group.created_at else None,
                "updated_at": group.updated_at.isoformat() if group.updated_at else None
            }
            for group in groups
        ]
    }


@app.post("/assets/footages/groups")
async def create_footage_group_endpoint(req: CreateGroupRequest, db: AsyncSession = Depends(get_db)):
    try:
        group = await create_footage_group(
            db=db,
            name=req.name,
            description=req.description,
            color=req.color
        )
        return {
            "id": str(group.id),
            "name": group.name,
            "description": group.description,
            "color": group.color,
            "member_count": 0,
            "created_at": group.created_at.isoformat() if group.created_at else None
        }
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="A footage group with this name already exists")
        raise HTTPException(status_code=500, detail=f"Failed to create footage group: {str(e)}")


@app.get("/assets/footages/groups/{group_id}")
async def get_footage_group_endpoint(group_id: str, db: AsyncSession = Depends(get_db)):
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")

    group = await get_footage_group(db, group_uuid)
    if not group:
        raise HTTPException(status_code=404, detail="Footage group not found")

    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "color": group.color,
        "member_count": len(group.members),
        "members": [
            {
                "footage_filename": member.footage_filename,
                "order": member.order,
                "added_at": member.added_at.isoformat() if member.added_at else None
            }
            for member in sorted(group.members, key=lambda m: m.order if m.order is not None else 0)
        ],
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None
    }


@app.patch("/assets/footages/groups/{group_id}")
async def update_footage_group_endpoint(group_id: str, req: UpdateGroupRequest, db: AsyncSession = Depends(get_db)):
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")

    group = await update_footage_group(
        db=db,
        group_id=group_uuid,
        name=req.name,
        description=req.description,
        color=req.color
    )

    if not group:
        raise HTTPException(status_code=404, detail="Footage group not found")

    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "color": group.color,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None
    }


@app.delete("/assets/footages/groups/{group_id}")
async def delete_footage_group_endpoint(group_id: str, db: AsyncSession = Depends(get_db)):
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")

    deleted = await delete_footage_group(db, group_uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Footage group not found")

    return {"status": "deleted", "group_id": group_id}


@app.post("/assets/footages/groups/{group_id}/members")
async def add_footage_member(group_id: str, req: AddFootageToGroupRequest, db: AsyncSession = Depends(get_db)):
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")

    if '..' in req.footage_filename or '/' in req.footage_filename or '\\' in req.footage_filename:
        raise HTTPException(status_code=400, detail="Invalid footage filename")

    footage_path = FOOTAGES_DIR / req.footage_filename
    if not footage_path.exists():
        raise HTTPException(status_code=404, detail="Footage file not found")

    member = await add_footage_to_group(
        db=db,
        group_id=group_uuid,
        footage_filename=req.footage_filename,
        order=req.order
    )

    if not member:
        group = await get_footage_group(db, group_uuid)
        if not group:
            raise HTTPException(status_code=404, detail="Footage group not found")
        raise HTTPException(status_code=400, detail="Footage already in this group")

    return {
        "status": "added",
        "group_id": group_id,
        "footage_filename": req.footage_filename,
        "order": member.order
    }


@app.delete("/assets/footages/groups/{group_id}/members/{footage_filename}")
async def remove_footage_member(group_id: str, footage_filename: str, db: AsyncSession = Depends(get_db)):
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")

    if '..' in footage_filename or '/' in footage_filename or '\\' in footage_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    removed = await remove_footage_from_group(
        db=db,
        group_id=group_uuid,
        footage_filename=footage_filename
    )

    if not removed:
        raise HTTPException(status_code=404, detail="Footage file not found in group")

    return {"status": "removed", "group_id": group_id, "footage_filename": footage_filename}


@app.get("/assets/footages/{footage_filename}/groups")
async def get_groups_for_footage(footage_filename: str, db: AsyncSession = Depends(get_db)):
    if '..' in footage_filename or '/' in footage_filename or '\\' in footage_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    groups = await get_footage_groups_for_file(db, footage_filename)
    return {
        "footage_filename": footage_filename,
        "groups": [
            {
                "id": str(group.id),
                "name": group.name,
                "description": group.description,
                "color": group.color
            }
            for group in groups
        ]
    }


# ============================================================================
# PROXY MANAGEMENT
# ============================================================================

class CreateProxyRequest(BaseModel):
    login: str
    password: str
    ip: str
    port: int


class UpdateProxyRequest(BaseModel):
    login: Optional[str] = None
    password: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None


@app.post("/proxies")
async def create_proxy_endpoint(req: CreateProxyRequest, db: AsyncSession = Depends(get_db)):
    """Create a new proxy"""
    try:
        proxy = await create_proxy(
            db=db,
            login=req.login,
            password=req.password,
            ip=req.ip,
            port=req.port
        )
        return {
            "id": str(proxy.id),
            "login": proxy.login,
            "ip": proxy.ip,
            "port": proxy.port,
            "created_at": proxy.created_at.isoformat() if proxy.created_at else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create proxy: {str(e)}")


@app.get("/proxies")
async def list_proxies(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List all proxies"""
    proxies = await get_all_proxies(db, limit=limit, offset=offset)
    
    return {
        "count": len(proxies),
        "proxies": [
            {
                "id": str(proxy.id),
                "login": proxy.login,
                "ip": proxy.ip,
                "port": proxy.port,
                "created_at": proxy.created_at.isoformat() if proxy.created_at else None,
                "updated_at": proxy.updated_at.isoformat() if proxy.updated_at else None
            }
            for proxy in proxies
        ]
    }


@app.get("/proxies/{proxy_id}")
async def get_proxy_endpoint(proxy_id: str, db: AsyncSession = Depends(get_db)):
    """Get a proxy by ID"""
    try:
        proxy_uuid = uuid.UUID(proxy_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid proxy ID format")
    
    proxy = await get_proxy(db, proxy_uuid)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    
    return {
        "id": str(proxy.id),
        "login": proxy.login,
        "ip": proxy.ip,
        "port": proxy.port,
        "created_at": proxy.created_at.isoformat() if proxy.created_at else None,
        "updated_at": proxy.updated_at.isoformat() if proxy.updated_at else None
    }


@app.patch("/proxies/{proxy_id}")
async def update_proxy_endpoint(proxy_id: str, req: UpdateProxyRequest, db: AsyncSession = Depends(get_db)):
    """Update a proxy"""
    try:
        proxy_uuid = uuid.UUID(proxy_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid proxy ID format")
    
    proxy = await update_proxy(
        db=db,
        proxy_id=proxy_uuid,
        login=req.login,
        password=req.password,
        ip=req.ip,
        port=req.port
    )
    
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    
    return {
        "id": str(proxy.id),
        "login": proxy.login,
        "ip": proxy.ip,
        "port": proxy.port,
        "updated_at": proxy.updated_at.isoformat() if proxy.updated_at else None
    }


@app.delete("/proxies/{proxy_id}")
async def delete_proxy_endpoint(proxy_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a proxy (only if no users are using it)"""
    try:
        proxy_uuid = uuid.UUID(proxy_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid proxy ID format")
    
    try:
        deleted = await delete_proxy(db, proxy_uuid)
        if not deleted:
            raise HTTPException(status_code=404, detail="Proxy not found")
        
        return {"status": "deleted", "proxy_id": proxy_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# USER MANAGEMENT
# ============================================================================

class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: str  # Now required
    proxy_id: str  # Required - proxy must be created first
    full_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False


class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None
    proxy_id: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


@app.get("/users")
async def list_users(
    include_inactive: bool = False,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List all users"""
    users = await get_all_users(db, include_inactive=include_inactive, limit=limit, offset=offset)
    
    return {
        "count": len(users),
        "users": [
            {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "proxy_id": str(user.proxy_id),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "group_count": len(user.group_memberships)
            }
            for user in users
        ]
    }


@app.post("/users")
async def create_user_endpoint(req: CreateUserRequest, db: AsyncSession = Depends(get_db)):
    """Create a new user (proxy is required)"""
    # Validate proxy_id
    try:
        proxy_uuid = uuid.UUID(req.proxy_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid proxy ID format")
    
    # Check if proxy exists
    proxy = await get_proxy(db, proxy_uuid)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    
    # Check if username already exists
    existing_user = await get_user_by_username(db, req.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if email already exists
        existing_email = await get_user_by_email(db, req.email)
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
    
    # Hash password
    password_hash = hash_password(req.password)
    
    try:
        user = await create_user(
            db=db,
            username=req.username,
            password_hash=password_hash,
            email=req.email,
            proxy_id=proxy_uuid,
            full_name=req.full_name,
            is_active=req.is_active,
            is_admin=req.is_admin
        )
        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "proxy_id": str(user.proxy_id),
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="Username or email already exists")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@app.get("/users/{user_id}")
async def get_user_endpoint(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get a user by ID"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    user = await get_user(db, user_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user groups
    user_groups = await get_user_groups_for_user(db, user_uuid)
    
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "proxy_id": str(user.proxy_id),
        "proxy": {
            "id": str(user.proxy.id),
            "ip": user.proxy.ip,
            "port": user.proxy.port,
            "login": user.proxy.login
        } if user.proxy else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "groups": [
            {
                "id": str(group.id),
                "name": group.name,
                "description": group.description,
                "color": group.color
            }
            for group in user_groups
        ]
    }


@app.patch("/users/{user_id}")
async def update_user_endpoint(user_id: str, req: UpdateUserRequest, db: AsyncSession = Depends(get_db)):
    """Update a user"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    # Check if username already exists (if updating)
    if req.username:
        existing_user = await get_user_by_username(db, req.username)
        if existing_user and existing_user.id != user_uuid:
            raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if email already exists (if updating)
    if req.email:
        existing_email = await get_user_by_email(db, req.email)
        if existing_email and existing_email.id != user_uuid:
            raise HTTPException(status_code=400, detail="Email already exists")
    
    # Validate proxy_id if provided
    proxy_uuid = None
    if req.proxy_id:
        try:
            proxy_uuid = uuid.UUID(req.proxy_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid proxy ID format")
        
        # Check if proxy exists
        proxy = await get_proxy(db, proxy_uuid)
        if not proxy:
            raise HTTPException(status_code=404, detail="Proxy not found")
    
    # Hash password if provided
    password_hash = None
    if req.password:
        password_hash = hash_password(req.password)
    
    try:
        user = await update_user(
            db=db,
            user_id=user_uuid,
            username=req.username,
            password_hash=password_hash,
            email=req.email,
            proxy_id=proxy_uuid,
            full_name=req.full_name,
            is_active=req.is_active,
            is_admin=req.is_admin
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
            "proxy_id": str(user.proxy_id),
        "updated_at": user.updated_at.isoformat() if user.updated_at else None
    }


@app.delete("/users/{user_id}")
async def delete_user_endpoint(user_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a user"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    deleted = await delete_user(db, user_uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"status": "deleted", "user_id": user_id}


# ============================================================================
# USER GROUP MANAGEMENT
# ============================================================================

@app.get("/users/groups")
async def list_user_groups(db: AsyncSession = Depends(get_db)):
    """List all user groups with their members"""
    groups = await get_all_user_groups(db)
    return {
        "groups": [
            {
                "id": str(group.id),
                "name": group.name,
                "description": group.description,
                "color": group.color,
                "permissions": group.permissions,
                "member_count": len(group.members),
                "members": [
                    {
                        "user_id": str(member.user_id),
                        "role": member.role,
                        "added_at": member.added_at.isoformat() if member.added_at else None
                    }
                    for member in sorted(group.members, key=lambda m: m.added_at)
                ],
                "created_at": group.created_at.isoformat() if group.created_at else None,
                "updated_at": group.updated_at.isoformat() if group.updated_at else None
            }
            for group in groups
        ]
    }


@app.post("/users/groups")
async def create_user_group_endpoint(req: CreateGroupRequest, db: AsyncSession = Depends(get_db)):
    """Create a new user group"""
    try:
        group = await create_user_group(
            db=db,
            name=req.name,
            description=req.description,
            color=req.color
        )
        return {
            "id": str(group.id),
            "name": group.name,
            "description": group.description,
            "color": group.color,
            "member_count": 0,
            "created_at": group.created_at.isoformat() if group.created_at else None
        }
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="A user group with this name already exists")
        raise HTTPException(status_code=500, detail=f"Failed to create user group: {str(e)}")


@app.get("/users/groups/{group_id}")
async def get_user_group_endpoint(group_id: str, db: AsyncSession = Depends(get_db)):
    """Get a user group by ID"""
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")
    
    group = await get_user_group(db, group_uuid)
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")
    
    # Get full member details with user info
    members_list = await get_group_members_for_user_group(db, group_uuid)
    
    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "color": group.color,
        "permissions": group.permissions,
        "member_count": len(members_list),
        "members": [
            {
                "user_id": str(member.user_id),
                "username": member.user.username if member.user else None,
                "email": member.user.email if member.user else None,
                "full_name": member.user.full_name if member.user else None,
                "role": member.role,
                "added_at": member.added_at.isoformat() if member.added_at else None
            }
            for member in members_list
        ],
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None
    }


@app.patch("/users/groups/{group_id}")
async def update_user_group_endpoint(group_id: str, req: UpdateGroupRequest, db: AsyncSession = Depends(get_db)):
    """Update a user group"""
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")
    
    group = await update_user_group(
        db=db,
        group_id=group_uuid,
        name=req.name,
        description=req.description,
        color=req.color
    )
    
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")
    
    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "color": group.color,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None
    }


@app.delete("/users/groups/{group_id}")
async def delete_user_group_endpoint(group_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a user group"""
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID format")
    
    deleted = await delete_user_group(db, group_uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="User group not found")
    
    return {"status": "deleted", "group_id": group_id}


class AddUserToGroupRequest(BaseModel):
    user_id: str
    role: Optional[str] = None


@app.post("/users/groups/{group_id}/members")
async def add_user_to_group_endpoint(group_id: str, req: AddUserToGroupRequest, db: AsyncSession = Depends(get_db)):
    """Add a user to a group"""
    try:
        group_uuid = uuid.UUID(group_id)
        user_uuid = uuid.UUID(req.user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID or user ID format")
    
    member = await add_user_to_group(
        db=db,
        group_id=group_uuid,
        user_id=user_uuid,
        role=req.role
    )
    
    if not member:
        # Check if group exists or if already in group
        group = await get_user_group(db, group_uuid)
        if not group:
            raise HTTPException(status_code=404, detail="User group not found")
        user = await get_user(db, user_uuid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        raise HTTPException(status_code=400, detail="User already in this group")
    
    return {
        "status": "added",
        "group_id": group_id,
        "user_id": req.user_id,
        "role": member.role
    }


@app.delete("/users/groups/{group_id}/members/{user_id}")
async def remove_user_from_group_endpoint(group_id: str, user_id: str, db: AsyncSession = Depends(get_db)):
    """Remove a user from a group"""
    try:
        group_uuid = uuid.UUID(group_id)
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group ID or user ID format")
    
    removed = await remove_user_from_group(
        db=db,
        group_id=group_uuid,
        user_id=user_uuid
    )
    
    if not removed:
        raise HTTPException(status_code=404, detail="User not found in group")
    
    return {"status": "removed", "group_id": group_id, "user_id": user_id}


@app.get("/users/{user_id}/groups")
async def get_groups_for_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get all groups that contain a specific user"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    groups = await get_user_groups_for_user(db, user_uuid)
    return {
        "user_id": user_id,
        "groups": [
            {
                "id": str(group.id),
                "name": group.name,
                "description": group.description,
                "color": group.color,
                "permissions": group.permissions
            }
            for group in groups
        ]
    }