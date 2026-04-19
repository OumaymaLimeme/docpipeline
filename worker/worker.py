"""
Worker — consumes jobs from RabbitMQ, processes PDF/CSV files,
writes results to PostgreSQL, and exposes Prometheus metrics.

Scale horizontally:
  docker compose up --scale worker=4
"""

import json, os, time, logging, socket
from datetime import datetime

import pika
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] worker=%(worker_id)s %(message)s",
)

WORKER_ID = socket.gethostname()  # unique per container replica
logger = logging.LoggerAdapter(logging.getLogger(__name__), {"worker_id": WORKER_ID})

# ── Prometheus metrics (each worker exposes on a random port) ─────────────────
JOBS_PROCESSED = Counter("worker_jobs_processed_total",  "Jobs completed",       ["status"])
JOB_DURATION   = Histogram("worker_job_duration_seconds","Processing time (s)",  ["file_type"])
QUEUE_DEPTH    = Gauge("worker_queue_depth",             "Approx queue depth seen by this worker")

# Start metrics HTTP server on port 9100 (Prometheus will scrape each replica)
start_http_server(9100)

# ── DB setup ──────────────────────────────────────────────────────────────────
DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://pipeline:pipeline@localhost/pipeline")
engine = create_engine(DB_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine)

def update_job(job_id: str, status: str, result: str = None, error: str = None):
    with Session() as session:
        session.execute(
            text("""
                UPDATE jobs
                SET status     = :status,
                    result     = :result,
                    error      = :error,
                    updated_at = :now
                WHERE id = :id
            """),
            {"status": status, "result": result, "error": error, "now": datetime.utcnow(), "id": job_id},
        )
        session.commit()

# ── Processors ────────────────────────────────────────────────────────────────
def process_pdf(file_path: str) -> dict:
    import pdfplumber
    result = {"pages": 0, "word_count": 0, "tables": 0}
    with pdfplumber.open(file_path) as pdf:
        result["pages"] = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text() or ""
            result["word_count"] += len(text.split())
            result["tables"]     += len(page.extract_tables())
    return result

def process_csv(file_path: str) -> dict:
    import pandas as pd
    df = pd.read_csv(file_path)
    return {
        "rows":    len(df),
        "columns": len(df.columns),
        "headers": list(df.columns),
        "nulls":   int(df.isnull().sum().sum()),
    }

PROCESSORS = {"pdf": process_pdf, "csv": process_csv}

# ── Main consumer loop ────────────────────────────────────────────────────────
def on_message(channel, method, properties, body):
    payload = json.loads(body)
    job_id    = payload["job_id"]
    file_type = payload["file_type"]
    file_path = payload["file_path"]

    logger.info(f"Received job {job_id} ({file_type})")
    update_job(job_id, "processing")

    start = time.perf_counter()
    try:
        processor = PROCESSORS.get(file_type)
        if not processor:
            raise ValueError(f"Unsupported file type: {file_type}")

        result = processor(file_path)
        elapsed = time.perf_counter() - start

        update_job(job_id, "done", result=json.dumps(result))
        JOBS_PROCESSED.labels(status="done").inc()
        JOB_DURATION.labels(file_type=file_type).observe(elapsed)
        logger.info(f"Job {job_id} DONE in {elapsed:.2f}s → {result}")

    except Exception as exc:
        elapsed = time.perf_counter() - start
        update_job(job_id, "failed", error=str(exc))
        JOBS_PROCESSED.labels(status="failed").inc()
        JOB_DURATION.labels(file_type=file_type).observe(elapsed)
        logger.error(f"Job {job_id} FAILED: {exc}")

    channel.basic_ack(delivery_tag=method.delivery_tag)

def main():
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://pipeline:pipeline@localhost/")
    logger.info("Connecting to RabbitMQ…")

    # Retry until RabbitMQ is ready
    while True:
        try:
            params = pika.URLParameters(rabbitmq_url)
            conn   = pika.BlockingConnection(params)
            break
        except Exception:
            logger.info("RabbitMQ not ready, retrying in 3s…")
            time.sleep(3)

    channel = conn.channel()
    channel.queue_declare(queue="jobs", durable=True)
    channel.basic_qos(prefetch_count=1)   # one job at a time per worker
    channel.basic_consume(queue="jobs", on_message_callback=on_message)

    logger.info("Worker ready. Waiting for jobs…")
    channel.start_consuming()

if __name__ == "__main__":
    main()
