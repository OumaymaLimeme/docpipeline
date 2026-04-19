"""
Async Document Processing Pipeline — FastAPI entry point.

Endpoints:
  POST /upload          → accept PDF or CSV, queue a job, return job_id
  GET  /jobs/{job_id}   → get job status + result
  GET  /jobs            → list all jobs (paginated)
  GET  /metrics         → Prometheus metrics
  GET  /health          → liveness check
"""

import uuid, json, os
from contextlib import asynccontextmanager
from datetime import datetime

import aio_pika
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session, init_db
from models import Job, JobStatus
from schemas import JobOut, JobListOut

# ── Prometheus metrics ────────────────────────────────────────────────────────
UPLOADS_TOTAL   = Counter("pipeline_uploads_total",   "Total upload requests", ["file_type"])
JOBS_QUEUED     = Counter("pipeline_jobs_queued_total","Total jobs sent to queue")
REQUEST_LATENCY = Histogram("pipeline_request_duration_seconds", "Request latency", ["endpoint"])

# ── App lifecycle ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Ensure upload folder exists
    os.makedirs("uploads", exist_ok=True)
    yield

app = FastAPI(
    title="Async Document Processing Pipeline",
    description="Upload PDFs/CSVs → process async → query results",
    version="1.0.0",
    lifespan=lifespan,
)

# ── RabbitMQ helper ───────────────────────────────────────────────────────────
async def publish_job(job_id: str, file_type: str, file_path: str):
    connection = await aio_pika.connect_robust(os.getenv("RABBITMQ_URL"))
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("jobs", durable=True)
        message = aio_pika.Message(
            body=json.dumps({
                "job_id": job_id,
                "file_type": file_type,
                "file_path": file_path,
            }).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await channel.default_exchange.publish(message, routing_key="jobs")

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/upload", response_model=JobOut, status_code=202)
async def upload_file(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    # Validate file type
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("pdf", "csv"):
        raise HTTPException(status_code=400, detail="Only PDF and CSV files are accepted.")

    # Save file to disk
    job_id = str(uuid.uuid4())
    save_path = f"uploads/{job_id}.{ext}"
    contents = await file.read()
    with open(save_path, "wb") as f:
        f.write(contents)

    # Persist job in DB
    job = Job(id=job_id, filename=file.filename, file_type=ext, status=JobStatus.PENDING)
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Queue the job
    await publish_job(job_id, ext, save_path)

    UPLOADS_TOTAL.labels(file_type=ext).inc()
    JOBS_QUEUED.inc()

    return job


@app.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    from sqlalchemy import select
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/jobs", response_model=JobListOut)
async def list_jobs(
    page: int = 1,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select, func
    offset = (page - 1) * limit
    total_res = await session.execute(select(func.count()).select_from(Job))
    total = total_res.scalar()
    result = await session.execute(select(Job).offset(offset).limit(limit).order_by(Job.created_at.desc()))
    jobs = result.scalars().all()
    return {"total": total, "page": page, "limit": limit, "jobs": jobs}
