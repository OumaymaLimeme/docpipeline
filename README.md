# Async Document Processing Pipeline

A distributed system that accepts PDF/CSV uploads, processes them asynchronously via scalable Python workers, tracks job state in PostgreSQL, and provides full observability via Prometheus + Grafana.

## Architecture

```
Client → FastAPI (HTTP) → RabbitMQ → Worker(s) → PostgreSQL
                                          ↓
                              Prometheus ← metrics
                                   ↓
                               Grafana (dashboards)
```

## Stack

| Layer       | Technology                     |
|-------------|-------------------------------|
| API         | Python 3.12, FastAPI, Uvicorn |
| Queue       | RabbitMQ 3.13                 |
| Workers     | Python, pika, pdfplumber, pandas |
| Database    | PostgreSQL 16                 |
| Monitoring  | Prometheus + Grafana          |
| Container   | Docker Compose                |

## Quick Start

```bash
# 1. Clone and enter the project
git clone <your-repo>
cd docpipeline

# 2. Start everything
docker compose up --build

# 3. Scale workers (separate terminal)
docker compose up --scale worker=3
```

## Services & Ports

| Service             | URL                          |
|---------------------|------------------------------|
| FastAPI docs        | http://localhost:8000/docs   |
| RabbitMQ UI         | http://localhost:15672       |
| Prometheus          | http://localhost:9090        |
| Grafana             | http://localhost:3000        |

RabbitMQ credentials: `pipeline / pipeline`  
Grafana credentials: `admin / admin`

## API Usage

### Upload a file
```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf"
```

Response:
```json
{
  "id": "abc-123",
  "filename": "document.pdf",
  "file_type": "pdf",
  "status": "pending",
  "created_at": "2026-04-19T10:00:00"
}
```

### Poll job status
```bash
curl http://localhost:8000/jobs/abc-123
```

### List all jobs
```bash
curl "http://localhost:8000/jobs?page=1&limit=20"
```

## Scaling Workers

```bash
# Run 4 parallel workers
docker compose up --scale worker=4

# Watch them consume in RabbitMQ UI → http://localhost:15672
```

## What Workers Do

- **PDF**: extracts page count, word count, and number of tables
- **CSV**: extracts row count, column count, headers, and null count

Both results are stored as JSON in the `jobs.result` column.

## Project Structure

```
docpipeline/
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py        ← FastAPI app, routes, metrics
│   ├── db.py          ← SQLAlchemy async engine
│   ├── models.py      ← Job ORM model
│   └── schemas.py     ← Pydantic response schemas
├── worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── worker.py      ← RabbitMQ consumer + PDF/CSV processors
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
│       └── provisioning/
│           ├── datasources/prometheus.yml
│           └── dashboards/pipeline.json
└── docker-compose.yml
```

## Step-by-Step Development Guide

### Step 1 — Run it locally
```bash
docker compose up --build
# Open http://localhost:8000/docs and try the /upload endpoint
```

### Step 2 — Upload a test file
```bash
curl -X POST http://localhost:8000/upload -F "file=@yourfile.pdf"
# Copy the returned job id
curl http://localhost:8000/jobs/<job_id>
# Watch status go: pending → processing → done
```

### Step 3 — Scale workers
```bash
docker compose up --scale worker=3
# Upload several files and watch multiple workers consume them in RabbitMQ UI
```

### Step 4 — View Grafana
1. Open http://localhost:3000 (admin/admin)
2. Go to Dashboards → Pipeline → "Async Document Pipeline"
3. Upload files and watch metrics update in real time

### Step 5 — Add to GitHub
```bash
git init
git add .
git commit -m "feat: initial async document processing pipeline"
git remote add origin https://github.com/<you>/docpipeline.git
git push -u origin main
```

Write a solid README (this file is your README) and add screenshots of the Grafana dashboard.
