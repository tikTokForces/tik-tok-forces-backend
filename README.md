# TikTok Forces Backend API

FastAPI-based backend for TikTok video processing system.

## Features

- RESTful API endpoints
- PostgreSQL database with async SQLAlchemy
- Alembic migrations
- User and proxy management
- Job processing

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
```

## Environment Variables

See `.env.example` for required variables.

## API Documentation

Once running, visit: http://localhost:8000/docs
# CI/CD Test
