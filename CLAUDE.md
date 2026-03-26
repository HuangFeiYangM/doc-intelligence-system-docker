# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Document Intelligence System Backend** - A FastAPI-based service for document understanding and data extraction using LLM (DeepSeek API).

System extracts structured data from documents (PDF, Word, Excel) and fills them into Excel templates.

## Architecture

### Docker Services
- **FastAPI Backend**: Core API server (port 8001)
- **MySQL 8.0**: Primary database (port 3306)
- **Redis 7.0**: Cache and task queue (port 6379)
- **Celery Worker**: Background task processing (optional)

### Technology Stack
| Component | Technology |
|-----------|------------|
| Web Framework | FastAPI 0.104+ |
| Database | MySQL 8.0 + SQLAlchemy 2.0 |
| Cache | Redis 7.0 |
| ORM | SQLAlchemy 2.0 + asyncmy |
| Task Queue | Celery 5.3+ |
| LLM | DeepSeek API |
| Document Parsing | pdfplumber, python-docx, pandas, openpyxl |

## Project Structure

```
doc-intelligence-system-docker/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   │   ├── documents.py # Upload endpoints
│   │   │   ├── tasks.py     # Task management
│   │   │   ├── templates.py # Template management
│   │   │   └── download.py  # File download
│   │   ├── core/            # Celery config
│   │   ├── models/          # SQLAlchemy models (Task, Document, Template)
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   │   ├── document_parser.py  # Parse PDF/Word/Excel
│   │   │   ├── llm_service.py      # DeepSeek API integration
│   │   │   ├── table_generator.py  # Excel generation
│   │   │   └── task_service.py     # Task orchestration
│   │   ├── repositories/    # Data access layer
│   │   ├── utils/           # Utility functions
│   │   ├── tests/           # Test files
│   │   ├── main.py          # FastAPI entry
│   │   ├── config.py        # Settings
│   │   └── database.py      # DB connection
│   ├── uploads/             # Uploaded files
│   ├── templates/           # Excel templates
│   ├── outputs/             # Generated files
│   ├── alembic/             # DB migrations
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── start_app.py
└── CLAUDE.md
```

## Common Commands

### Docker
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Rebuild after changes
docker-compose up -d --build
```

### Development (without Docker)
```bash
cd backend
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your settings

# Run the app
python start_app.py
# OR
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Database
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

### Testing
```bash
# Run all tests
pytest app/tests/

# Run specific test file
pytest app/tests/test_document_parser.py
pytest app/tests/test_llm_service.py
pytest app/tests/test_table_generator.py
pytest app/tests/test_api.py
pytest app/tests/test_models.py
pytest app/tests/test_task_service.py

# Run specific test
pytest app/tests/test_document_parser.py::TestDocumentParser::test_parse_word

# Run with coverage
pytest --cov=app app/tests/

# Run only DeepSeek API tests (requires API key)
pytest app/tests/test_llm_service.py -v

# Skip API tests (fast)
pytest app/tests/ -k "not deepseek" --ignore=app/tests/test_llm_service.py
```

### Celery (optional)
```bash
# Start worker
 celery -A app.core.celery_app worker --loglevel=info

# Start beat (for scheduled tasks)
celery -A app.core.celery_app beat --loglevel=info
```

## API Endpoints

### Documents
- `POST /api/v1/documents/upload` - Upload document (PDF/DOCX/XLSX)
  - Form data: `file` (required), `template_id` (optional)

### Tasks
- `GET /api/v1/tasks/{task_id}/status` - Get task status
- `GET /api/v1/tasks/{task_id}/result` - Get extracted data
- `GET /api/v1/tasks` - List all tasks
- `POST /api/v1/tasks/{task_id}/cancel` - Cancel pending task

### Templates
- `GET /api/v1/templates` - List templates
- `POST /api/v1/templates` - Create template
  - Form data: `name`, `description`, `field_mapping` (JSON), `file` (optional)
- `GET /api/v1/templates/{template_id}` - Get template
- `DELETE /api/v1/templates/{template_id}` - Delete template

### Download
- `GET /api/v1/download/{task_id}` - Download generated Excel file

## Core Modules

### DocumentParser (`app/services/document_parser.py`)
```python
from app.services import DocumentParser

# Extract text from any supported document
text = DocumentParser.extract_text("/path/to/file.pdf")

# Get document type
doc_type = DocumentParser.get_document_type("file.docx")  # DocumentType.WORD

# Parse specific types
text = DocumentParser.parse_pdf("file.pdf")
text = DocumentParser.parse_word("file.docx")
text = DocumentParser.parse_excel("file.xlsx")
```

### LLMService (`app/services/llm_service.py`)
Uses DeepSeek API (configured in `.env`).

```python
from app.services import LLMService

service = LLMService()

# Extract fields from text
fields = ["合同编号", "甲方", "金额"]
result = await service.extract_fields(text, fields)
# Returns: {"合同编号": "HT-001", "甲方": "ABC公司", "金额": "10000"}
```

### TableGenerator (`app/services/table_generator.py`)
```python
from app.services import TableGenerator

# Generate from template
generator = TableGenerator()
output_path = generator.generate_from_template(
    template_path="template.xlsx",
    data={"字段1": "值1", "字段2": "值2"},
    field_mapping={"字段1": "B2", "字段2": "B3"},
    output_path="output.xlsx"
)

# Create new template
TableGenerator.create_template(
    "new_template.xlsx",
    headers=["字段1", "字段2"],
    field_mapping={"字段1": "A2", "字段2": "B2"}
)
```

## Environment Variables

Key settings in `backend/.env`:

```bash
# DeepSeek LLM API (required for LLM features)
DEEPSEEK_API_KEY=sk-e6d10d4113d7447e9eb5c111ab0d1a0f
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# Database
DATABASE_URL=mysql+asyncmy://user:password@localhost:3306/doc_intel

# Redis
REDIS_URL=redis://localhost:6379/0

# File Upload
MAX_UPLOAD_SIZE=52428800  # 50MB
ALLOWED_EXTENSIONS=[".pdf", ".docx", ".doc", ".xlsx", ".xls"]
```

## Data Models

### Task
- `id`: UUID
- `status`: pending/processing/completed/failed
- `progress`: 0-100
- `document_id`: Reference to uploaded document
- `template_id`: Reference to template (optional)
- `extracted_data`: JSON result from LLM
- `output_file_path`: Generated Excel file path

### Document
- `id`: UUID
- `filename`: Stored filename
- `original_filename`: Original upload name
- `file_path`: Full path
- `doc_type`: pdf/word/excel
- `extracted_text`: Cached text content

### Template
- `id`: UUID
- `name`: Template name
- `file_path`: Template file path
- `field_mapping`: JSON mapping field names to cell addresses

## Testing Notes

- DeepSeek API tests are skipped if API key is not available
- API integration tests use SQLite in-memory database
- Document parser tests create temporary files
- Run tests without API calls: `pytest app/tests/ -k "not deepseek and not api"`
