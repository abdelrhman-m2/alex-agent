# Alex Agent — Production Deployment Guide

## 🚀 Phase 5: HITL + Deployment Complete

This guide covers deploying Alex Agent as a production-grade REST API with Human-in-the-Loop approval system.

---

## 📋 Architecture Overview

```
User Request
    ↓
FastAPI Backend
    ├── Task Creation
    ├── HITL Approval Gate
    ├── Task Queue Management
    └── Monitoring & Logging
    ↓
Background Execution
    ├── Multi-Agent System
    ├── RAG Retrieval
    ├── Memory Management
    └── Result Storage
    ↓
REST API Response
```

---

## 🏗️ Quick Start (Local)

### 1. Clone/Setup

```bash
cd alex_agent
pip install -r requirements.txt
```

### 2. Run API

```bash
python fastapi_backend.py
```

Visit: `http://localhost:8000`
- 📖 API Docs: `http://localhost:8000/docs`
- 🔍 OpenAPI Schema: `http://localhost:8000/openapi.json`

---

## 🐳 Docker Deployment

### 1. Build Image

```bash
docker build -t alex-agent:latest .
```

### 2. Run Container

```bash
docker run -p 8000:8000 \
  -e GOOGLE_API_KEY=your_key_here \
  alex-agent:latest
```

### 3. Docker Compose (Optional)

```yaml
version: '3.8'
services:
  alex-agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_API_KEY=your_key_here
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Run: `docker-compose up`

---

## 🔄 API Workflows

### Workflow 1: With Human Approval

```
POST /execute
  ↓ (require_approval=true)
  ↓
Task Status: WAITING_APPROVAL
  ↓
GET /approvals/pending  (reviewer checks)
  ↓
POST /approvals/{task_id}  (reviewer decides)
  ↓
Task Status: APPROVED → EXECUTING → COMPLETED
```

### Workflow 2: Automatic Execution

```
POST /execute
  ↓ (require_approval=false)
  ↓
Task Status: PENDING → EXECUTING → COMPLETED
```

---

## 📡 API Endpoints

### Execute Goal

```bash
POST /execute
Content-Type: application/json

{
  "goal": "Analyze AI impact on healthcare",
  "priority": "high",
  "require_approval": true
}

Response:
{
  "task_id": "abc12345",
  "status": "waiting_approval",
  "goal": "Analyze AI impact on healthcare",
  "requires_approval": true,
  "message": "Task queued"
}
```

### Check Task Status

```bash
GET /tasks/{task_id}

Response:
{
  "task_id": "abc12345",
  "goal": "Analyze AI impact on healthcare",
  "status": "executing",
  "result": null,
  "confidence": 0.0,
  "created_at": "2026-09-26T10:30:00",
  "started_at": "2026-09-26T10:30:30",
  "approval_status": "approved"
}
```

### Get Pending Approvals

```bash
GET /approvals/pending

Response:
{
  "pending_count": 2,
  "tasks": [
    {
      "task_id": "abc12345",
      "goal": "Analyze AI impact...",
      "priority": "high",
      "status": "waiting_approval"
    },
    ...
  ]
}
```

### Approve Task

```bash
POST /approvals/{task_id}
Content-Type: application/json

{
  "decision": "approved",
  "feedback": "Looks good, proceed",
  "reviewer_id": "reviewer_001"
}

Response:
{
  "task_id": "abc12345",
  "decision": "approved",
  "message": "Task approved and executing"
}
```

### System Health

```bash
GET /health

Response:
{
  "status": "healthy",
  "tasks_total": 10,
  "tasks_pending": 2,
  "tasks_executing": 1,
  "tasks_completed": 7,
  "approvals_pending": 2
}
```

### Metrics

```bash
GET /metrics

Response:
{
  "total_tasks": 10,
  "completed_tasks": 7,
  "failed_tasks": 1,
  "success_rate": 0.7,
  "avg_confidence": 0.85,
  "pending_approvals": 2
}
```

---

## 🔐 Environment Variables

```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key

# Optional
LOG_LEVEL=INFO
API_PORT=8000
API_HOST=0.0.0.0
```

---

## 📊 Monitoring

### Logging

All operations logged to console and file:
```
2026-09-26 10:30:00 - alex_agent - INFO - Task abc12345 created
2026-09-26 10:30:05 - alex_agent - INFO - Task abc12345 approved by reviewer_001
2026-09-26 10:30:30 - alex_agent - INFO - Task abc12345 execution started
2026-09-26 10:32:45 - alex_agent - INFO - Task abc12345 completed
```

### Health Checks

- `/health` - Basic health status
- Docker health check: Built-in (30s intervals)
- Metrics: `/metrics` endpoint

### Performance Metrics

- Task success rate
- Average confidence scores
- Execution time
- Approval rate

---

## 🚀 Cloud Deployment

### AWS ECS

```bash
# Build and push image
docker build -t alex-agent:latest .
aws ecr get-login-password | docker login --username AWS --password-stdin <ECR_URI>
docker tag alex-agent:latest <ECR_URI>/alex-agent:latest
docker push <ECR_URI>/alex-agent:latest

# Launch in ECS
aws ecs run-task --cluster production --task-definition alex-agent
```

### Google Cloud Run

```bash
gcloud run deploy alex-agent \
  --image gcr.io/PROJECT_ID/alex-agent:latest \
  --platform managed \
  --region us-central1 \
  --set-env-vars GOOGLE_API_KEY=your_key
```

### Heroku

```bash
heroku create alex-agent
heroku container:push web
heroku container:release web
heroku config:set GOOGLE_API_KEY=your_key
```

---

## 🔧 Development

### Local Testing

```bash
# Install dev dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/

# Test endpoints
pytest tests/test_api.py
```

### Example Test

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from fastapi_backend import app

client = TestClient(app)

def test_execute():
    response = client.post("/execute", json={
        "goal": "Test goal",
        "require_approval": False
    })
    assert response.status_code == 200
    assert "task_id" in response.json()

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

---

## 📈 Scaling Considerations

### Single Instance
- Good for: Development, testing
- Limitation: Single async worker

### Multiple Instances
```yaml
# Use load balancer
Load Balancer (nginx/traefik)
  ├── Alex Agent Instance 1
  ├── Alex Agent Instance 2
  └── Alex Agent Instance 3
```

### With Message Queue
```
Request → API → Queue (Redis/RabbitMQ) → Workers
```

For high throughput, add:
- Redis for task queue
- Celery for background tasks
- PostgreSQL for persistence

---

## 🔐 Security Checklist

- [ ] API key stored in environment variable
- [ ] HTTPS enabled in production
- [ ] CORS configured appropriately
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] Logging doesn't expose sensitive data
- [ ] Database credentials secured
- [ ] Regular security updates

---

## 📊 Monitoring Stack (Optional)

```
Application
  ↓
Prometheus (metrics collection)
  ↓
Grafana (visualization)
  ↓
AlertManager (alerts)
```

---

## 🆘 Troubleshooting

### Task Stuck in "EXECUTING"

```bash
# Check logs
docker logs alex-agent

# If stuck, restart worker
docker restart alex-agent
```

### High Memory Usage

```bash
# Check task queue
curl http://localhost:8000/metrics

# Clean old tasks (implement cleanup endpoint)
```

### API Timeout

- Increase timeout in FastAPI config
- Use async task execution (already implemented)
- Add caching layer (Redis)

---

## 📚 Next Steps

After Phase 5 deployment:

1. **Monitoring & Alerts** — Set up Prometheus/Grafana
2. **Database** — Add PostgreSQL for task persistence
3. **Queue** — Add Redis for distributed execution
4. **Advanced HITL** — Build dashboard for approvers
5. **Analytics** — Track execution patterns

---

## 🎯 Production Checklist

- [ ] All endpoints tested
- [ ] Error handling implemented
- [ ] Logging configured
- [ ] Health checks passing
- [ ] API documentation complete
- [ ] Docker image built and tested
- [ ] Environment variables configured
- [ ] SSL/TLS certificate installed
- [ ] Monitoring setup
- [ ] Backup strategy defined
- [ ] Incident response plan ready

---

## 📞 Support

For issues or questions:
1. Check logs: `docker logs alex-agent`
2. Review this guide
3. Check API docs: `http://localhost:8000/docs`
4. Open issue on GitHub

---

**🚀 Alex Agent is production-ready!**

Congratulations on completing all 5 phases!
