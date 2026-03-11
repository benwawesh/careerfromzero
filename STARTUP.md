# Career AI System — Startup Guide

## Prerequisites
- Ollama installed with Mistral pulled (`ollama pull mistral`)
- PostgreSQL running
- Python virtualenv set up in `backend/venv/`
- Node.js installed

---

## Start everything (3 terminals)

### Terminal 1 — Ollama
Ollama runs as a systemd service after install, so it starts automatically.
To check or start manually:
```bash
systemctl status ollama
# or start manually:
ollama serve
```

### Terminal 2 — Django Backend (port 8000)
```bash
cd "/home/ben/career AI system/backend"
source venv/bin/activate
python manage.py runserver 8000
```

### Terminal 3 — Next.js Frontend (port 3001)
```bash
cd "/home/ben/career AI system/frontend"
npm run dev -- --port 3001
```

---

## Verify everything is running
```bash
# Backend health
curl http://localhost:8000/api/health/

# Ollama + model
curl http://localhost:11434/api/tags

# Frontend
open http://localhost:3001
```

---

## Quick health check (run all at once)
```bash
curl -s http://localhost:8000/api/health/ && \
curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); print('Models:', [m['name'] for m in d.get('models',[])])" && \
curl -s http://localhost:3001 -o /dev/null -w "Frontend: %{http_code}\n"
```

---

## Notes
- AI analysis takes **3-5 minutes** on CPU (no GPU). The page will show progress and update automatically.
- If analysis fails, check Ollama is running: `systemctl status ollama`
- Logs: `backend/logs/` or run Django in a terminal to see live output
- Frontend env: `frontend/.env.local` must have `NEXT_PUBLIC_API_URL=http://localhost:8000`
