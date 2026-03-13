# Career AI — Startup Guide

## Requirements
- Docker + Docker Compose installed
- `backend/.env` file configured (copy from `.env.example` and fill in keys)

---

## Mode 1 — Development (hot reload)

Use this every day for local development. Code changes apply instantly without rebuilding.

```bash
docker compose up --build
```

After first build, just:
```bash
docker compose up
```

**URLs:**
| Service | URL |
|---|---|
| Frontend | http://localhost:3001 |
| Backend API | http://localhost:8010/api/ |
| Django Admin | http://localhost:8010/admin/ |

---

## Mode 2 — Local Production Simulation (built, gunicorn)

Use this to test exactly how the app behaves in production before deploying.
Runs gunicorn + built Next.js instead of dev servers. Slower to start but matches production behaviour.

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.local-prod.yml up --build
```

**Same URLs as dev mode** — `http://localhost:3001` and `http://localhost:8010/api/`

Stop:
```bash
docker compose -f docker-compose.prod.yml -f docker-compose.local-prod.yml down
```

---

## Mode 3 — Production (on the server)

Run on the production server only. Uses gunicorn + built Next.js + nginx reverse proxy.

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

**Do not run this locally** — the frontend build uses empty API URLs and relies on nginx.

---

## Useful Commands

```bash
# View logs (dev mode)
docker compose logs -f
docker compose logs -f backend
docker compose logs -f celery_worker

# Stop everything
docker compose down

# Stop and delete all data (volumes) — WARNING: deletes database!
docker compose down -v

# Django management
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py makemigrations
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
| `backend` | Django — port 8000 internally, 8010 on host |
| `celery_worker` | Celery background task worker |
| `celery_beat` | Celery scheduled task scheduler |
| `frontend` | Next.js — port 3001 |

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
| `OPENAI_API_KEY` | OpenAI key (Whisper STT / TTS) |
| `MPESA_*` | M-Pesa Daraja credentials |
| `PESAPAL_*` | PesaPal card payment credentials |
