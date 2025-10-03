# CV Evaluator Backend

AI-powered CV and Project Evaluation System using FastAPI, PostgreSQL, and LLM.

## Features

- 📄 Upload CV and Project Report (PDF)
- 🤖 AI-powered evaluation using OpenAI GPT
- 🔍 RAG (Retrieval-Augmented Generation) with ChromaDB
- ⚡ Async processing with Celery + Redis
- 📊 Structured scoring based on predefined rubrics
- 🔄 Retry mechanism with exponential backoff
- 🛡️ Error handling and validation

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy
- **Package Manager**: UV
- **Task Queue**: Celery + Redis
- **LLM**: OpenAI GPT-4
- **Vector DB**: ChromaDB
- **PDF Parsing**: PyPDF2

## Project Structure

```
app/
├── core/          # Auth, security, dependencies, exceptions
├── database/      # Database configuration and session
├── models/        # SQLAlchemy models
├── schemas/       # Pydantic schemas
├── repositories/  # Data access layer
├── routes/        # API endpoints
├── services/      # Business logic (LLM, RAG, evaluation)
├── workers/       # Celery workers
└── utils/         # Helper functions (file handling, PDF parsing, retry)
```

## Setup

### 1. Install UV

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and Install Dependencies

```bash
git clone <your-repo>
cd cv-evaluator-backend
uv sync
```

### 3. Setup Environment Variables

```bash
cp .env.example .env
# Edit .env with your configurations
```

### 4. Setup PostgreSQL

```bash
# Using Docker
docker run --name cv-eval-postgres \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=cv_evaluator \
  -p 5432:5432 -d postgres:15
```

### 5. Setup Redis

```bash
# Using Docker
docker run --name cv-eval-redis \
  -p 6379:6379 -d redis:7
```

### 6. Run Migrations (Optional: using Alembic)

```bash
uv run alembic upgrade head
```

### 7. Ingest Reference Documents

```bash
uv run python scripts/ingest_reference_docs.py
```

## Running the Application

### Start FastAPI Server

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Celery Worker

```bash
uv run celery -A app.workers.evaluation_worker worker --loglevel=info
```

## API Endpoints

### 1. Upload Documents

```bash
POST /upload
Content-Type: multipart/form-data

Form data:
- cv: <CV PDF file>
- project_report: <Project Report PDF file>

Response:
{
  "cv_document": {"id": 1, "filename": "...", ...},
  "project_document": {"id": 2, "filename": "...", ...}
}
```

### 2. Trigger Evaluation

```bash
POST /evaluate
Content-Type: application/json

{
  "job_title": "Backend Developer",
  "cv_document_id": 1,
  "project_document_id": 2
}

Response:
{
  "id": 123,
  "status": "queued"
}
```

### 3. Get Evaluation Result

```bash
GET /result/{id}

Response (queued/processing):
{
  "id": 123,
  "status": "processing"
}

Response (completed):
{
  "id": 123,
  "status": "completed",
  "result": {
    "cv_match_rate": 0.82,
    "cv_feedback": "Strong backend skills...",
    "project_score": 4.5,
    "project_feedback": "Good implementation...",
    "overall_summary": "Recommended candidate...",
    "cv_detailed_scores": {...},
    "project_detailed_scores": {...}
  }
}
```

## Architecture

### Data Flow

1. **Upload** → Store CV & Project Report → Return Document IDs
2. **Evaluate** → Create evaluation record → Queue Celery task → Return Job ID
3. **Process** (Background):
   - Extract text from PDFs
   - Retrieve context from vector DB (RAG)
   - LLM Chain: CV Eval → Project Eval → Summary
   - Save results to database
4. **Result** → Poll endpoint → Get evaluation status/results

### LLM Chain

```
CV Text + Job Description (RAG) → LLM → CV Scores & Feedback
                                     ↓
Project Text + Case Study (RAG) → LLM → Project Scores & Feedback
                                     ↓
                              Final LLM → Overall Summary
```

## Error Handling

- **File Upload**: Size limit, type validation
- **LLM API**: Retry with exponential backoff (3 attempts)
- **Task Failure**: Celery retry mechanism
- **Database**: Transaction rollback on error

## Testing

```bash
uv run pytest tests/ -v --cov=app
```

## Development

```bash
# Format code
uv run black app/

# Lint
uv run flake8 app/

# Type check
uv run mypy app/
```
