# Document Intelligence System - Backend

## Overview

Document Intelligence System backend built with FastAPI, using LLM (DeepSeek API) to extract structured data from documents (PDF, Word, Excel) and fill them into templates.

## Architecture

- **FastAPI**: Web framework
- **MySQL 8.0**: Primary database
- **Redis 7.0**: Cache and task queue
- **Celery**: Background task processing (optional)
- **DeepSeek API**: LLM for data extraction

## Quick Start

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

### Local Development

1. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

2. **Setup environment:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Run the application:**
```bash
python start_app.py
```

## API Endpoints

### Documents
- `POST /api/v1/documents/upload` - Upload document for processing

### Tasks
- `GET /api/v1/tasks/{task_id}/status` - Get task status
- `GET /api/v1/tasks/{task_id}/result` - Get task result
- `GET /api/v1/tasks` - List tasks
- `POST /api/v1/tasks/{task_id}/cancel` - Cancel task

### Templates
- `GET /api/v1/templates` - List templates
- `POST /api/v1/templates` - Create template
- `GET /api/v1/templates/{template_id}` - Get template
- `DELETE /api/v1/templates/{template_id}` - Delete template

### Download
- `GET /api/v1/download/{task_id}` - Download generated Excel file

## Configuration

Key environment variables:
- `DATABASE_URL`: MySQL connection string
- `REDIS_URL`: Redis connection string
- `DEEPSEEK_API_KEY`: DeepSeek API key for LLM
- `DEEPSEEK_MODEL`: Model to use (default: deepseek-chat)
- `MAX_UPLOAD_SIZE`: Maximum file upload size (default: 50MB)

## Testing

```bash
# Run all tests
pytest app/tests/

# Run with coverage
pytest --cov=app app/tests/
```

## License

MIT