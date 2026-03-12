# Career AI — Local Startup (Docker)

Same stack as production: PostgreSQL, Redis, Celery Worker, Celery Beat, Backend, Frontend.

## Requirements
- Docker + Docker Compose installed
- `backend/.env` file configured (copy from `.env.example` and fill in keys)

---

## Start Everything

```bash
docker compose up --build
```

First run takes a few minutes to build images. After that:

```bash
docker compose up
```

To run in background:
```bash
docker compose up -d
```

---

## URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:3001 |
| Backend API | http://localhost:8010/api/ |
| Django Admin | http://localhost:8010/admin/ |

---

## Useful Commands

```bash
# View logs
docker compose logs -f

# View logs for one service
docker compose logs -f backend
docker compose logs -f celery_worker

# Stop everything
docker compose down

# Stop and delete all data (volumes) — WARNING: deletes database!
docker compose down -v

# Run Django management commands
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py shell

# Rebuild after changing requirements.txt or package.json
docker compose up --build
```

---

## Services

| Service | Description |
|---|---|
| `db` | PostgreSQL 16 database |
| `redis` | Redis 7 (cache + Celery broker) |
| `backend` | Django on port 8000 (mapped to 8010 on host) |
| `celery_worker` | Celery background task worker |
| `celery_beat` | Celery scheduled task scheduler |
| `frontend` | Next.js dev server on port 3001 |

---

## Environment Variables

Edit `backend/.env`. Key values:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | PostgreSQL credentials |
| `DB_HOST` | Must be `db` (Docker service name) |
| `REDIS_URL` | Must be `redis://redis:6379/0` |
| `ANTHROPIC_API_KEY` | Claude AI key |
| `OPENAI_API_KEY` | OpenAI key (Whisper STT/TTS) |
| `MPESA_*` | M-Pesa Daraja credentials |
| `PESAPAL_*` | PesaPal card payment credentials |
