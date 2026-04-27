# Async Document Processing Pipeline

This project is a scalable asynchronous document processing system designed to handle large volumes of PDF and CSV files efficiently.

It leverages a distributed architecture with message queues and background workers to ensure high performance and reliability.

## 🧩 Architecture

The system consists of:

FastAPI: Handles incoming requests and task creation
RabbitMQ: Message broker for task distribution
Workers: Background services that process documents
PostgreSQL: Stores processed data and metadata
Prometheus & Grafana: Monitoring and observability
Docker Compose: Containerized deployment and scaling

        ┌──────────────┐
        │   Client     │
        │ (Frontend)   │
        └──────┬───────┘
               │ HTTP Request (Upload File)
               ▼
        ┌──────────────┐
        │   FastAPI    │
        │   (API)      │
        └──────┬───────┘
               │ Send Task
               ▼
        ┌──────────────┐
        │  RabbitMQ    │
        │  (Queue)     │
        └──────┬───────┘
        ┌──────┴──────────────┐
        │                     │
        ▼                     ▼
 ┌──────────────┐     ┌──────────────┐
 │  Worker 1    │     │  Worker 2    │   ... (N workers)
 └──────┬───────┘     └──────┬───────┘
        │ Process File        │
        ▼                     ▼
        ┌────────────────────────┐
        │   PostgreSQL DB        │
        └────────────────────────┘

        ┌──────────────┐
        │ Prometheus   │
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │  Grafana     │
        └──────────────┘
        
## ⚙️ How It Works

A user uploads a document via the API
The API sends a processing task to RabbitMQ
Workers consume tasks from the queue
Documents are processed asynchronously
Results are stored in PostgreSQL
Metrics are collected and visualized in Grafana

## Stack

| Layer       | Technology                     |
|-------------|-------------------------------|
| API         | Python 3.12, FastAPI, Uvicorn |
| Queue       | RabbitMQ 3.13                 |
| Workers     | Python, pika, pdfplumber, pandas |
| Database    | PostgreSQL 16                 |
| Monitoring  | Prometheus + Grafana          |
| Container   | Docker Compose                |

##  💡 Why This Project?

This project demonstrates:

Distributed systems design
Asynchronous processing
Scalability and fault tolerance
DevOps and observability practices

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


Write a solid README (this file is your README) and add screenshots of the Grafana dashboard.
