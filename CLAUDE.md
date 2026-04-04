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

# Setup environment (from project root)
cp ../.env.example ../.env
# Edit ../.env with your settings

# Run the app
python start_app.py
# OR
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

**Alternative**: Set up environment from project root:
```bash
# From project root directory
cp .env.example .env
# Edit .env with your settings

cd backend
pip install -r requirements.txt
python start_app.py
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

**IMPORTANT**: Configuration has been standardized. All settings can now be configured via environment variables in the `.env` file at the project root (same level as `docker-compose.yml`).

### Quick Start
1. Copy the example file: `cp .env.example .env`
2. Edit `.env` and fill in your values (especially `DEEPSEEK_API_KEY`)
3. For Docker deployment, update URLs to use service names:
   - `DATABASE_URL=mysql+asyncmy://user:password@mysql:3306/doc_intel`
   - `REDIS_URL=redis://redis:6379/0`

### Complete Environment Variables

#### Required Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `DEEPSEEK_API_KEY` | DeepSeek API key (get from [platform.deepseek.com](https://platform.deepseek.com/)) | *None* |

#### Core Application
| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | `"Doc Intelligence System"` |
| `APP_VERSION` | Application version | `"1.0.0"` |
| `DEBUG` | Debug mode | `false` |
| `HOST` | Server host | `"0.0.0.0"` |
| `PORT` | Server port | `8001` |
| `APP_ENV` | Environment (development/production/test) | `"development"` |
| `LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | `"INFO"` |

#### Database (MySQL)
| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection URL | `mysql+asyncmy://user:password@localhost:3306/doc_intel` |
| `DATABASE_POOL_SIZE` | Connection pool size | `20` |
| `DATABASE_MAX_OVERFLOW` | Max overflow connections | `10` |

#### Redis
| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `REDIS_PASSWORD` | Redis password (optional) | *None* |

#### Celery (Optional)
| Variable | Description | Default |
|----------|-------------|---------|
| `CELERY_BROKER_URL` | Celery broker URL | `redis://localhost:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery result backend | `redis://localhost:6379/2` |

#### DeepSeek LLM API
| Variable | Description | Default |
|----------|-------------|---------|
| `DEEPSEEK_API_BASE` | API base URL | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | Model name | `"deepseek-chat"` |
| `DEEPSEEK_MAX_TOKENS` | Max tokens in response | `4096` |
| `DEEPSEEK_TEMPERATURE` | Temperature (0.0-2.0) | `0.7` |
| `DEEPSEEK_TIMEOUT` | API timeout (seconds) | `90` |

#### File Upload
| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_UPLOAD_SIZE` | Max upload size (bytes) | `52428800` (50MB) |
| `ALLOWED_EXTENSIONS` | Allowed file extensions | `[".pdf", ".docx", ".doc", ".xlsx", ".xls"]` |

#### File Paths
| Variable | Description | Default |
|----------|-------------|---------|
| `UPLOAD_DIR` | Upload directory | `./backend/uploads` |
| `TEMPLATE_DIR` | Template directory | `./backend/templates` |
| `OUTPUT_DIR` | Output directory | `./backend/outputs` |
| `LOG_DIR` | Log directory | `./backend/logs` |

#### Task Processing
| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_CONCURRENT_TASKS` | Max concurrent tasks | `5` |
| `TASK_TIMEOUT` | Task timeout (seconds) | `300` |

#### MySQL Container (Docker Compose)
| Variable | Description | Default |
|----------|-------------|---------|
| `MYSQL_ROOT_PASSWORD` | MySQL root password | `password` |
| `MYSQL_DATABASE` | Database name | `doc_intel` |
| `MYSQL_USER` | Database user | `user` |
| `MYSQL_PASSWORD` | Database user password | `password` |

#### Testing
| Variable | Description | Default |
|----------|-------------|---------|
| `TEST_DATABASE_URL` | Test database URL | `mysql+asyncmy://root:password@localhost:3306/doc_intel_test` |
| `TEST_DEEPSEEK_API_KEY` | Test API key | `sk-test-key-for-testing-only` |

### Configuration Validation
Run the validation script to check your configuration:
```bash
python validate_config.py
```

## Migration Guide (From Previous Version)

### Changes in Configuration Structure
1. **.env file location moved**: From `backend/.env` to project root directory (same level as `docker-compose.yml`)
2. **Enhanced configuration**: All settings can now be configured via environment variables
3. **Test environment**: Separate `.env.test` file for testing

### Migration Steps
1. **Backup existing configuration**:
   ```bash
   cp backend/.env backend/.env.backup
   ```

2. **Create new .env file**:
   ```bash
   cp .env.example .env
   ```

3. **Transfer values from old .env**:
   - Copy `DEEPSEEK_API_KEY`, `DATABASE_URL`, `REDIS_URL`, and other custom values
   - Update URLs for Docker: use `mysql` and `redis` as hostnames when using Docker Compose

4. **Test configuration**:
   ```bash
   python validate_config.py
   ```

5. **Update Docker Compose** (if using Docker):
   - The updated `docker-compose.yml` automatically uses the new `.env` location
   - No manual changes needed

6. **Test the application**:
   ```bash
   docker-compose up -d  # or run locally
   curl http://localhost:8001/health
   ```

### Backward Compatibility
- Old `backend/.env` file will still work (config.py looks in multiple locations)
- Existing environment variables remain compatible
- Test configuration is now separate (`.env.test`)

### Security Notes
- **API Key Exposure**: The previous version had API keys committed to git history
  - Recommended: Revoke exposed keys and generate new ones
  - Update `.env` with new keys
- **Git Ignore**: Updated `.gitignore` now excludes `.env` files and sensitive directories
  - Ensure no sensitive data is committed going forward

### Troubleshooting
- **Configuration not loading**: Run `validate_config.py` to see which .env files are found
- **Docker containers can't connect**: Ensure `DATABASE_URL` uses `mysql` hostname, not `localhost`
- **Tests failing**: Use `pytest --env-file .env.test` to load test environment

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

### Configuration
- Tests use environment variables from `.env.test` (root directory)
- Test database is separate: `doc_intel_test`
- Test API key: `sk-test-key-for-testing-only` (for skipping real API calls)

### Running Tests
```bash
# Load test environment variables
export $(grep -v '^#' .env.test | xargs)

# Run all tests
pytest

# Skip API tests (fast)
pytest -k "not deepseek"

# Run only unit tests
pytest -m unit

# Run with coverage
pytest --cov=app app/tests/
```

**Alternative**: Use `dotenv` or `python-dotenv` to load environment variables automatically.

### Test Environment Variables
- `TEST_DATABASE_URL`: Test database URL
- `TEST_DEEPSEEK_API_KEY`: Test API key
- `TEST_UPLOAD_DIR`, `TEST_OUTPUT_DIR`: Test file directories

### Notes
- DeepSeek API tests are skipped if `DEEPSEEK_API_KEY` is not available or starts with "sk-test-"
- Test directories are cleaned up automatically
- Use `pytest.ini` for default configuration
