"""
Database helper for processing steps
Import this in your processing scripts to automatically log to database
"""
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class StepDatabaseLogger:
    """
    Helper class for processing steps to log to database
    Usage in your processing scripts:
    
    from database.step_helper import StepDatabaseLogger
    
    db_logger = StepDatabaseLogger()
    video_id = db_logger.log_video_start(input_path, original_filename)
    # ... do processing ...
    output_id = db_logger.log_video_complete(output_path, output_filename, video_metadata)
    db_logger.log_processing(job_id, video_id, output_id, "footages_add", parameters)
    """
    
    def __init__(self, enabled: bool = None):
        """
        Initialize database logger
        
        Args:
            enabled: If True, force enable. If False, force disable. 
                    If None, auto-detect based on environment
        """
        self.enabled = enabled
        self.db = None
        self._session = None
        
        # Auto-detect if enabled
        if self.enabled is None:
            # Check if we can import database modules
            try:
                from database import AsyncSessionLocal
                from database.crud import create_video, create_processing_history
                self.enabled = True
            except Exception:
                self.enabled = False
        
        if self.enabled:
            try:
                from database import AsyncSessionLocal
                self.AsyncSessionLocal = AsyncSessionLocal
            except Exception as e:
                print(f"⚠️  Database modules not available: {e}")
                self.enabled = False
    
    async def get_session(self):
        """Get or create database session"""
        if not self.enabled:
            return None
        
        if self._session is None:
            self._session = self.AsyncSessionLocal()
        return self._session
    
    async def close_session(self):
        """Close database session"""
        if self._session:
            await self._session.close()
            self._session = None
    
    def log_video_start(
        self,
        file_path: str,
        original_filename: str,
        **metadata
    ) -> Optional[str]:
        """
        Log when video processing starts
        
        Returns:
            video_id (str) or None if database disabled
        """
        if not self.enabled:
            return None
        
        try:
            return asyncio.run(self._async_log_video_start(file_path, original_filename, **metadata))
        except Exception as e:
            print(f"⚠️  Failed to log video start: {e}")
            return None
    
    async def _async_log_video_start(self, file_path: str, original_filename: str, **metadata):
        """Async implementation of log_video_start"""
        from database.crud import create_video, get_video_by_path
        
        try:
            session = await self.get_session()
            if not session:
                return None
            
            # Check if video already exists
            existing = await get_video_by_path(session, file_path)
            if existing:
                return str(existing.id)
            
            # Get file info
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
            
            # Create video record
            video = await create_video(
                db=session,
                original_filename=original_filename,
                file_path=file_path,
                file_size_bytes=file_size,
                video_metadata=metadata
            )
            
            return str(video.id)
        except Exception as e:
            print(f"⚠️  Error in _async_log_video_start: {e}")
            return None
    
    def log_video_complete(
        self,
        file_path: str,
        original_filename: str,
        duration_seconds: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
        codec: Optional[str] = None,
        has_audio: bool = True,
        **metadata
    ) -> Optional[str]:
        """
        Log when video processing completes
        
        Returns:
            video_id (str) or None if database disabled
        """
        if not self.enabled:
            return None
        
        try:
            return asyncio.run(self._async_log_video_complete(
                file_path, original_filename, duration_seconds, width, height,
                fps, codec, has_audio, **metadata
            ))
        except Exception as e:
            print(f"⚠️  Failed to log video complete: {e}")
            return None
    
    async def _async_log_video_complete(
        self, file_path, original_filename, duration_seconds, width, height,
        fps, codec, has_audio, **metadata
    ):
        """Async implementation of log_video_complete"""
        from database.crud import create_video, get_video_by_path
        
        try:
            session = await self.get_session()
            if not session:
                return None
            
            # Check if video already exists
            existing = await get_video_by_path(session, file_path)
            if existing:
                return str(existing.id)
            
            # Get file info
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
            
            # Create video record
            video = await create_video(
                db=session,
                original_filename=original_filename,
                file_path=file_path,
                file_size_bytes=file_size,
                duration_seconds=duration_seconds,
                width=width,
                height=height,
                fps=fps,
                codec=codec,
                has_audio=has_audio,
                video_metadata=metadata
            )
            
            return str(video.id)
        except Exception as e:
            print(f"⚠️  Error in _async_log_video_complete: {e}")
            return None
    
    def log_processing(
        self,
        job_id: Optional[str],
        input_video_id: Optional[str],
        output_video_id: Optional[str],
        processing_type: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Log processing history
        
        Returns:
            history_id (str) or None if database disabled
        """
        if not self.enabled:
            return None
        
        try:
            return asyncio.run(self._async_log_processing(
                job_id, input_video_id, output_video_id, processing_type, parameters
            ))
        except Exception as e:
            print(f"⚠️  Failed to log processing: {e}")
            return None
    
    async def _async_log_processing(
        self, job_id, input_video_id, output_video_id, processing_type, parameters
    ):
        """Async implementation of log_processing"""
        from database.crud import create_processing_history
        from uuid import UUID
        
        try:
            session = await self.get_session()
            if not session:
                return None
            
            # Convert string IDs to UUIDs
            job_uuid = UUID(job_id) if job_id else None
            input_uuid = UUID(input_video_id) if input_video_id else None
            output_uuid = UUID(output_video_id) if output_video_id else None
            
            # Create processing history
            history = await create_processing_history(
                db=session,
                job_id=job_uuid,
                input_video_id=input_uuid,
                output_video_id=output_uuid,
                processing_type=processing_type,
                parameters_used=parameters
            )
            
            return str(history.id)
        except Exception as e:
            print(f"⚠️  Error in _async_log_processing: {e}")
            return None
    
    def log_asset(
        self,
        asset_type: str,
        name: str,
        file_path: str,
        duration_seconds: Optional[float] = None,
        tags: Optional[list] = None,
        is_public: bool = False,
        **metadata
    ) -> Optional[str]:
        """
        Log asset (footage, music, watermark, etc.)
        
        Returns:
            asset_id (str) or None if database disabled
        """
        if not self.enabled:
            return None
        
        try:
            return asyncio.run(self._async_log_asset(
                asset_type, name, file_path, duration_seconds, tags, is_public, **metadata
            ))
        except Exception as e:
            print(f"⚠️  Failed to log asset: {e}")
            return None
    
    async def _async_log_asset(
        self, asset_type, name, file_path, duration_seconds, tags, is_public, **metadata
    ):
        """Async implementation of log_asset"""
        from database.crud import create_asset
        
        try:
            session = await self.get_session()
            if not session:
                return None
            
            # Get file info
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
            
            # Create asset record
            asset = await create_asset(
                db=session,
                asset_type=asset_type,
                name=name,
                file_path=file_path,
                file_size_bytes=file_size,
                duration_seconds=duration_seconds,
                tags=tags,
                is_public=is_public,
                asset_metadata=metadata
            )
            
            return str(asset.id)
        except Exception as e:
            print(f"⚠️  Error in _async_log_asset: {e}")
            return None
    
    def __del__(self):
        """Cleanup on deletion"""
        if self._session:
            try:
                asyncio.run(self.close_session())
            except:
                pass


# Simple sync wrapper for easier use in scripts
def log_video_processing(
    input_path: str,
    output_path: str,
    processing_type: str,
    parameters: Optional[Dict[str, Any]] = None,
    job_id: Optional[str] = None
) -> Dict[str, Optional[str]]:
    """
    Simple function to log video processing (sync wrapper)
    
    Args:
        input_path: Path to input video
        output_path: Path to output video
        processing_type: Type of processing (e.g., 'footages_add', 'music_add')
        parameters: Processing parameters
        job_id: Optional job ID if running as part of a job
    
    Returns:
        Dict with input_video_id, output_video_id, history_id
    """
    logger = StepDatabaseLogger()
    
    if not logger.enabled:
        return {"input_video_id": None, "output_video_id": None, "history_id": None}
    
    try:
        # Log input video
        input_video_id = logger.log_video_start(
            input_path,
            os.path.basename(input_path)
        )
        
        # Log output video
        output_video_id = logger.log_video_complete(
            output_path,
            os.path.basename(output_path)
        )
        
        # Log processing
        history_id = logger.log_processing(
            job_id=job_id,
            input_video_id=input_video_id,
            output_video_id=output_video_id,
            processing_type=processing_type,
            parameters=parameters
        )
        
        if input_video_id or output_video_id or history_id:
            print(f"✅ Logged to database: {processing_type}")
        
        return {
            "input_video_id": input_video_id,
            "output_video_id": output_video_id,
            "history_id": history_id
        }
    except Exception as e:
        print(f"⚠️  Database logging failed: {e}")
        return {"input_video_id": None, "output_video_id": None, "history_id": None}

