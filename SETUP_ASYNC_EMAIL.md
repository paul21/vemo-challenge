# Async Email Service Setup

## Overview
The email service has been converted to use Redis for queueing and Celery for async processing.

## Prerequisites
1. Redis server running on localhost:6379
2. Install new dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration
Update your `.env` file with Redis configuration:
```env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Running the Service

### 1. Start Redis
```bash
redis-server
```

### 2. Start Celery Worker
```bash
celery -A celery_worker.celery worker --loglevel=info
```

### 3. Start Flask App
```bash
python app.py
```

## Usage
The EmailService now works asynchronously:

```python
from services.email_service import EmailService

# Legacy sync method (now queues for async processing)
EmailService.send_operation_confirmation(operation_data)

# Direct async method
service = EmailService()
await service.queue_email_confirmation(operation_data)
```

## Monitoring
- Check Redis queue: `redis-cli LLEN email_queue`
- Monitor Celery: `celery -A celery_worker.celery events`
