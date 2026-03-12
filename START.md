# Career AI — Local Startup (No Docker)

## Requirements
- Python 3.12+ with `venv` at `backend/venv/`
- Node.js 18+ with `node_modules` at `frontend/node_modules/`
- PostgreSQL running locally (`career_ai_db`, user: `postgres`, pass: `postgres`)
- Redis running locally (for Celery caching)

---

## 1. Start Backend (Django on port 8000)

```bash
cd backend
source venv/bin/activate
python manage.py migrate          # run once after pulling new changes
python manage.py runserver 8000
```

Or use the script from the project root:

```bash
./start-backend.sh
```

Backend will be at: **http://localhost:8000**

---

## 2. Start Frontend (Next.js on port 3001)

Open a second terminal:

```bash
cd frontend
npm run dev -- --port 3001
```

Or use the script from the project root:

```bash
./start-frontend.sh
```

Frontend will be at: **http://localhost:3001**

---

## 3. (Optional) Start Celery Worker

Celery handles background tasks (job scraping, email). In a third terminal:

```bash
cd backend
source venv/bin/activate
celery -A career_ai worker --loglevel=info
```

---

## First-Time Setup

### Python virtual environment

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Node dependencies

```bash
cd frontend
npm install
```

### Database

```bash
# Create DB in psql
createdb career_ai_db

# Apply migrations
cd backend
source venv/bin/activate
python manage.py migrate

# Create admin superuser
python manage.py createsuperuser
```

---

## Environment Variables

Copy and edit the `.env` file in `backend/`:

```
backend/.env
```

Key values to set:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | PostgreSQL credentials |
| `ANTHROPIC_API_KEY` | Claude AI key (primary AI) |
| `OPENAI_API_KEY` | OpenAI key (Whisper STT/TTS) |
| `MPESA_*` | M-Pesa Daraja credentials |
| `PESAPAL_*` | PesaPal card payment credentials |

---

## Running Servers (Background, with logs)

To run both servers in the background from one terminal:

```bash
# Backend
cd backend
source venv/bin/activate
python manage.py runserver 8000 > logs/django.log 2>&1 &
echo "Backend PID: $!"

# Frontend
cd ../frontend
npm run dev -- --port 3001 > /tmp/frontend.log 2>&1 &
echo "Frontend PID: $!"
```

Check logs:

```bash
tail -f backend/logs/django.log
tail -f /tmp/frontend.log
```

Stop servers:

```bash
kill <PID>
# or kill all node/python dev servers:
pkill -f "runserver 8000"
pkill -f "next dev"
```

---

## URLs Summary

| Service | URL |
|---|---|
| Frontend | http://localhost:3001 |
| Backend API | http://localhost:8000/api/ |
| Django Admin | http://localhost:8000/admin/ |
