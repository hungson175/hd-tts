# VietVoice-TTS API Server Design

## Overview

A production-ready TTS API server using Redis queue for job management and multiple worker processes for concurrent synthesis. Designed for small-scale deployment (~10 users) with room to scale.

---

## Architecture

```
                                         ┌─────────────────────┐
                                         │     Worker 1        │
                                         │   ┌─────────────┐   │
┌──────────────┐                         │   │  TTS Model  │   │
│   Client 1   │──┐                      │   │  (ONNX)     │   │
└──────────────┘  │                      │   └─────────────┘   │
                  │   ┌─────────────┐    │   VRAM: ~3-4GB      │
┌──────────────┐  │   │             │    └──────────▲──────────┘
│   Client 2   │──┼──▶│   FastAPI   │               │
└──────────────┘  │   │   Gateway   │    ┌─────────────────────┐
                  │   │             │    │     Worker 2        │
┌──────────────┐  │   │  - Validate │    │   ┌─────────────┐   │
│   Client 3   │──┘   │  - Enqueue  │───▶│   │  TTS Model  │   │
└──────────────┘      │  - Wait     │    │   │  (ONNX)     │   │
                      └──────┬──────┘    │   └─────────────┘   │
                             │           │   VRAM: ~3-4GB      │
                             ▼           └──────────▲──────────┘
                      ┌─────────────┐               │
                      │    Redis    │───────────────┘
                      │             │
                      │  - tts:jobs │    ┌─────────────────────┐
                      │  - results  │    │     Worker 3        │
                      │             │    │   (optional)        │
                      └─────────────┘    │   VRAM: ~3-4GB      │
                                         └─────────────────────┘

                                         Total: ~10-12GB VRAM
                                         (3090 Ti: 24GB available)
```

---

## Components

### 1. FastAPI Gateway

**Responsibilities:**
- Accept HTTP requests from clients
- Validate input (text length, parameters)
- Create jobs and push to Redis queue
- Wait for results (blocking)
- Return audio response to client

**Key Characteristics:**
- Stateless (no TTS model loaded)
- Lightweight, can handle many connections
- Single instance sufficient for <100 concurrent users

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/synthesize` | Submit text, receive WAV audio |
| POST | `/synthesize/async` | Submit text, receive job_id |
| GET | `/job/{job_id}` | Poll job status/result |
| GET | `/health` | Health check with queue stats |
| GET | `/voices` | List available voice options |

---

### 2. Redis

**Purpose:** Message broker and result storage

**Data Structures:**

| Key | Type | Description | TTL |
|-----|------|-------------|-----|
| `tts:jobs` | List | Job queue (FIFO) | - |
| `tts:result:{job_id}` | String | Synthesis result (audio bytes) | 300s |
| `tts:error:{job_id}` | String | Error message if failed | 300s |
| `tts:status:{job_id}` | String | Job status (pending/processing/done/error) | 300s |
| `tts:worker:{worker_id}` | String | Worker heartbeat timestamp | 60s |
| `tts:metrics` | Hash | Counters (jobs_total, jobs_failed, etc.) | - |

**Configuration:**
```
Host: localhost (or redis container)
Port: 6379
DB: 0
Max Memory: 512MB (sufficient for job data)
```

---

### 3. Workers

**Responsibilities:**
- Load TTS model at startup (once)
- Poll Redis queue for jobs
- Execute synthesis
- Store results back to Redis

**Key Characteristics:**
- Each worker = 1 process = 1 model instance
- Runs independently (crash isolation)
- GPU-bound (one synthesis at a time per worker)

**Scaling:**

| Workers | VRAM | Throughput | Use Case |
|---------|------|------------|----------|
| 1 | ~4GB | ~1 req/2s | Development |
| 2 | ~8GB | ~1 req/s | Your use case |
| 3 | ~12GB | ~1.5 req/s | Growth |

---

## Data Flow

### Synchronous Request Flow

```
┌────────┐         ┌─────────┐         ┌───────┐         ┌────────┐
│ Client │         │ Gateway │         │ Redis │         │ Worker │
└───┬────┘         └────┬────┘         └───┬───┘         └───┬────┘
    │                   │                  │                 │
    │ POST /synthesize  │                  │                 │
    │ {text, gender}    │                  │                 │
    │──────────────────▶│                  │                 │
    │                   │                  │                 │
    │                   │ LPUSH tts:jobs   │                 │
    │                   │ {job_id, text}   │                 │
    │                   │─────────────────▶│                 │
    │                   │                  │                 │
    │                   │ BLPOP result     │ BRPOP tts:jobs  │
    │                   │ (blocking wait)  │◀────────────────│
    │                   │─────────────────▶│                 │
    │                   │                  │ job data        │
    │                   │                  │────────────────▶│
    │                   │                  │                 │
    │                   │                  │    [Synthesize] │
    │                   │                  │                 │
    │                   │                  │ SET result      │
    │                   │                  │◀────────────────│
    │                   │                  │                 │
    │                   │ result (audio)   │                 │
    │                   │◀─────────────────│                 │
    │                   │                  │                 │
    │ 200 OK (WAV)      │                  │                 │
    │◀──────────────────│                  │                 │
    │                   │                  │                 │
```

### Asynchronous Request Flow

```
Client                    Gateway                   Redis                    Worker
   │                         │                        │                        │
   │ POST /synthesize/async  │                        │                        │
   │────────────────────────▶│                        │                        │
   │                         │ LPUSH job              │                        │
   │                         │───────────────────────▶│                        │
   │ 202 {job_id}            │                        │                        │
   │◀────────────────────────│                        │                        │
   │                         │                        │                        │
   │         [Client can do other work]               │                        │
   │                         │                        │ BRPOP                  │
   │                         │                        │◀───────────────────────│
   │                         │                        │ [Synthesize...]        │
   │                         │                        │                        │
   │ GET /job/{job_id}       │                        │ SET result             │
   │────────────────────────▶│                        │◀───────────────────────│
   │                         │ GET status, result     │                        │
   │                         │───────────────────────▶│                        │
   │ 200 {status, audio_url} │                        │                        │
   │◀────────────────────────│                        │                        │
```

---

## Schemas

### Job Schema (Redis Queue)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "text": "Xin chào các bạn!",
  "gender": "female",
  "area": "northern",
  "emotion": "neutral",
  "speed": 1.0,
  "reference_audio": null,
  "reference_text": null,
  "created_at": 1704326400.123,
  "timeout": 120
}
```

### Result Schema

**Success:**
```json
{
  "status": "completed",
  "audio": "<base64 encoded WAV bytes>",
  "generation_time": 2.34,
  "audio_duration": 3.5,
  "completed_at": 1704326402.456
}
```

**Error:**
```json
{
  "status": "error",
  "error": "Text too long for synthesis",
  "error_code": "TEXT_TOO_LONG",
  "completed_at": 1704326402.456
}
```

### API Request/Response

**POST /synthesize**

Request:
```json
{
  "text": "Xin chào các bạn!",
  "gender": "female",
  "area": "northern",
  "emotion": "neutral",
  "speed": 1.0
}
```

Response: `audio/wav` binary with headers:
```
Content-Type: audio/wav
X-Job-Id: 550e8400-e29b-41d4-a716-446655440000
X-Generation-Time: 2.34
X-Audio-Duration: 3.5
X-Queue-Wait-Time: 0.12
```

**POST /synthesize/async**

Request: Same as above

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "queue_position": 2,
  "estimated_wait": 4.5
}
```

**GET /job/{job_id}**

Response (pending):
```json
{
  "job_id": "550e8400-...",
  "status": "pending",
  "queue_position": 1
}
```

Response (completed):
```json
{
  "job_id": "550e8400-...",
  "status": "completed",
  "audio_url": "/job/550e8400-.../audio",
  "generation_time": 2.34
}
```

**GET /health**

Response:
```json
{
  "status": "healthy",
  "queue_size": 3,
  "workers": {
    "active": 2,
    "total": 2
  },
  "metrics": {
    "jobs_completed": 1523,
    "jobs_failed": 12,
    "avg_generation_time": 2.1
  }
}
```

---

## Worker Implementation

### Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                     Worker Process                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    STARTUP                           │   │
│  │  1. Generate worker_id (uuid)                        │   │
│  │  2. Connect to Redis                                 │   │
│  │  3. Load TTS model (TTSApi)                          │   │
│  │  4. Register heartbeat                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   MAIN LOOP                          │   │
│  │                                                      │   │
│  │  while running:                                      │   │
│  │    1. Update heartbeat                               │   │
│  │    2. BRPOP tts:jobs (timeout=5s)                    │   │
│  │    3. If job received:                               │   │
│  │       a. SET status = "processing"                   │   │
│  │       b. Parse job JSON                              │   │
│  │       c. Call tts_api.synthesize_to_bytes()          │   │
│  │       d. SET result (base64 audio)                   │   │
│  │       e. SET status = "completed"                    │   │
│  │       f. Update metrics                              │   │
│  │    4. On error:                                      │   │
│  │       a. SET error message                           │   │
│  │       b. SET status = "error"                        │   │
│  │       c. Log error                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   SHUTDOWN                           │   │
│  │  1. Stop accepting new jobs                          │   │
│  │  2. Finish current job (if any)                      │   │
│  │  3. Remove heartbeat key                             │   │
│  │  4. Close Redis connection                           │   │
│  │  5. Exit                                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Heartbeat Mechanism

Workers publish heartbeats to detect failures:

```
Worker: SET tts:worker:{worker_id} {timestamp} EX 60
        (every 30 seconds)

Gateway: SCAN tts:worker:* → count active workers
         (for health endpoint)
```

If a worker crashes, its heartbeat key expires in 60s.

---

## Error Handling

### Client Errors (4xx)

| Error | Code | Response |
|-------|------|----------|
| Empty text | 400 | `{"error": "Text cannot be empty"}` |
| Text too long | 400 | `{"error": "Text exceeds 5000 characters"}` |
| Invalid voice option | 400 | `{"error": "Invalid gender: 'unknown'"}` |
| Job not found | 404 | `{"error": "Job not found"}` |
| Timeout waiting | 408 | `{"error": "Synthesis timeout"}` |

### Server Errors (5xx)

| Error | Code | Response |
|-------|------|----------|
| Redis unavailable | 503 | `{"error": "Service temporarily unavailable"}` |
| All workers down | 503 | `{"error": "No workers available"}` |
| Synthesis failed | 500 | `{"error": "Synthesis failed: {details}"}` |

### Worker Failure Scenarios

| Scenario | Behavior | Recovery |
|----------|----------|----------|
| Worker crashes mid-job | Job lost | Client times out, can retry |
| Worker hangs | Job stuck | Timeout at gateway, client retries |
| Redis connection lost | Worker reconnects | Exponential backoff (1s, 2s, 4s...) |
| OOM during synthesis | Worker process killed | Supervisor restarts worker |

### Retry Strategy (Client Side)

```python
# Recommended client retry logic
max_retries = 3
for attempt in range(max_retries):
    try:
        response = requests.post(url, json=data, timeout=120)
        if response.status_code == 200:
            return response.content
        elif response.status_code in [408, 503]:
            time.sleep(2 ** attempt)  # Exponential backoff
            continue
        else:
            raise APIError(response.json())
    except requests.Timeout:
        time.sleep(2 ** attempt)
        continue
raise MaxRetriesExceeded()
```

---

## Configuration

### Environment Variables

```bash
# Gateway
REDIS_URL=redis://localhost:6379/0
API_HOST=0.0.0.0
API_PORT=8000
JOB_TIMEOUT=120
MAX_TEXT_LENGTH=5000

# Worker
REDIS_URL=redis://localhost:6379/0
WORKER_ID=worker-1           # Optional, auto-generated if not set
NFE_STEPS=32                  # Quality: 32=high, 16=fast
HEARTBEAT_INTERVAL=30
LOG_LEVEL=INFO
```

### Recommended Settings by Scale

| Users | Workers | NFE Steps | Max Queue | Timeout |
|-------|---------|-----------|-----------|---------|
| 1-5 | 1 | 32 | 10 | 60s |
| 5-15 | 2 | 32 | 20 | 90s |
| 15-30 | 3 | 24 | 30 | 120s |

---

## Deployment

### Directory Structure

```
vietvoice-tts-server/
├── gateway/
│   ├── main.py              # FastAPI app
│   ├── schemas.py           # Pydantic models
│   ├── redis_client.py      # Redis operations
│   └── requirements.txt
├── worker/
│   ├── main.py              # Worker loop
│   ├── redis_client.py      # Redis operations
│   └── requirements.txt
├── docker-compose.yml
├── Dockerfile.gateway
├── Dockerfile.worker
└── .env
```

### Docker Compose

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru

  gateway:
    build:
      context: .
      dockerfile: Dockerfile.gateway
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

  worker-1:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - REDIS_URL=redis://redis:6379/0
      - WORKER_ID=worker-1
    depends_on:
      - redis
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  worker-2:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - REDIS_URL=redis://redis:6379/0
      - WORKER_ID=worker-2
    depends_on:
      - redis
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  redis_data:
```

### Systemd (Alternative to Docker)

```ini
# /etc/systemd/system/tts-gateway.service
[Unit]
Description=VietVoice TTS Gateway
After=network.target redis.service

[Service]
Type=simple
User=tts
WorkingDirectory=/opt/vietvoice-tts
ExecStart=/opt/vietvoice-tts/venv/bin/uvicorn gateway.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/tts-worker@.service
[Unit]
Description=VietVoice TTS Worker %i
After=network.target redis.service

[Service]
Type=simple
User=tts
WorkingDirectory=/opt/vietvoice-tts
Environment=WORKER_ID=worker-%i
ExecStart=/opt/vietvoice-tts/venv/bin/python -m worker.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Start 2 workers
sudo systemctl enable --now tts-worker@1
sudo systemctl enable --now tts-worker@2
sudo systemctl enable --now tts-gateway
```

---

## Monitoring

### Key Metrics

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Queue size | `LLEN tts:jobs` | > 20 |
| Active workers | Count of heartbeat keys | < 1 |
| Avg generation time | `tts:metrics` hash | > 10s |
| Error rate | `jobs_failed / jobs_total` | > 5% |
| Gateway latency | FastAPI middleware | p99 > 5s |

### Simple Monitoring Script

```python
#!/usr/bin/env python3
# monitor.py
import redis
import time

r = redis.Redis()

while True:
    queue_size = r.llen("tts:jobs")
    workers = len(list(r.scan_iter("tts:worker:*")))
    metrics = r.hgetall("tts:metrics")

    print(f"Queue: {queue_size} | Workers: {workers} | Metrics: {metrics}")
    time.sleep(5)
```

### Log Format

```
# Gateway
2024-01-04 10:30:00 INFO  [gateway] POST /synthesize job_id=550e8400 text_len=50
2024-01-04 10:30:02 INFO  [gateway] Completed job_id=550e8400 wait=0.1s total=2.3s

# Worker
2024-01-04 10:30:00 INFO  [worker-1] Received job_id=550e8400 text_len=50
2024-01-04 10:30:02 INFO  [worker-1] Completed job_id=550e8400 gen_time=2.1s
```

---

## Security Considerations

### Input Validation

- Max text length: 5000 characters
- Sanitize text (no control characters)
- Validate voice parameters against whitelist
- Rate limiting: 10 requests/minute per IP (optional)

### Network

- Redis: Bind to localhost or use authentication
- Gateway: Behind reverse proxy (nginx) in production
- HTTPS: Terminate at reverse proxy

### Resource Limits

- Max queue size: Reject new jobs if queue > 100
- Worker timeout: Kill synthesis if > 120s
- Memory limits: Docker/systemd resource constraints

---

## Future Improvements

1. **Priority Queue**: Premium users get faster processing
2. **Caching**: Cache identical text+voice combinations
3. **Streaming**: Return audio chunks as they're generated
4. **WebSocket**: Real-time progress updates
5. **Batch API**: Submit multiple texts in one request
6. **Voice Cloning Queue**: Separate queue for longer voice cloning jobs

---

## Quick Start

```bash
# 1. Start Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 2. Start Gateway
cd gateway && pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# 3. Start Workers (in separate terminals)
cd worker && pip install -r requirements.txt
WORKER_ID=worker-1 python main.py
WORKER_ID=worker-2 python main.py

# 4. Test
curl -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Xin chào các bạn!"}' \
  --output test.wav
```
