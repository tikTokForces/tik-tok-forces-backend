#!/usr/bin/env python3
"""
Database initialization script
Run this to set up the database tables
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database import init_db, close_db


async def main():
    """Initialize the database"""
    print("🔄 Initializing database...")
    try:
        await init_db()
        print("✅ Database initialized successfully!")
        print("\nTables created:")
        print("  - jobs")
        print("  - videos")
        print("  - processing_history")
        print("  - assets")
        print("  - processing_presets")
        print("  - api_logs")
        print("  - job_queue")
        print("\nYou can now start the API with: uvicorn main:app --reload")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())

