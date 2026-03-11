# Port Configuration - Career AI System

## Port Status Summary

### ✅ Currently Running

| Service | Port | Status | Notes |
|----------|-------|---------|---------|
| **Frontend (Next.js)** | 3001 | ✅ Running | Frontend dev server is running |
| **Backend (Django)** | 8000 | ✅ Running | Django dev server is running |
| **Ollama (AI)** | 11434 | ✅ Available | Will be used by Ollama API |
| **PostgreSQL** | 5432 | ✅ Running | Database is ready to use |

### ⚠️ Already in Use by Other Applications

| Service | Port | Used By |
|----------|-------|----------|
| MySQL | 3306 | MySQL database |
| Redis | 6379 | Redis cache |
| Cups (Printing) | 631 | Print services |
| Other Apps | 7880, 7881 | Various services |

## Startup Commands

### Backend (Django) - Port 8000
```bash
cd backend
source venv/bin/activate
python manage.py runserver 8000
```
Runs at: `http://localhost:8000`

### Frontend (Next.js) - Port 3001
```bash
cd frontend
npm run dev
```
Runs at: `http://localhost:3001`

### Ollama (AI) - Port 11434
```bash
ollama serve
```
Runs at: `http://localhost:11434`

### PostgreSQL Database - Port 5432
Already running! No action needed.

## API Endpoints

All API endpoints use port 8000:
- `http://localhost:8000/api/auth/login/`
- `http://localhost:8000/api/auth/register/`
- `http://localhost:8000/api/sys-mgmt-8832/` (Admin Panel)

## Frontend Access

Frontend runs on port 3001:
- `http://localhost:3001` - Main application
- `http://localhost:3001/dashboard` - User dashboard

## Complete Startup Sequence

Open 3 separate terminals:

**Terminal 1 - Ollama:**
```bash
ollama serve
```

**Terminal 2 - Backend:**
```bash
cd /home/ben/career\ AI\ system/backend
source venv/bin/activate
python manage.py runserver 8000
```

**Terminal 3 - Frontend:**
```bash
cd /home/ben/career\ AI\ system/frontend
npm run dev
```

## Port Conflicts

If you encounter port conflicts, you can change ports:

### Change Backend Port (8000)
```bash
python manage.py runserver 8080  # or any other available port
```

### Change Frontend Port (3001)
To use a different port, modify the startup command:
```bash
PORT=3002 npm run dev  # or any other available port
```

### Change Ollama Port (11434)
```bash
OLLAMA_HOST=http://localhost:11435  # Update in backend/.env
```

## Testing Port Availability

To check if a port is available:
```bash
# Check if port is in use
netstat -tuln | grep PORT_NUMBER

# Example: Check port 8000
netstat -tuln | grep 8000
```

If nothing is returned, port is available.

## Current Process IDs

- Backend PID: 144917 (port 8000)
- Frontend PID: 150233 (port 3001)

## Log Files

- Backend log: `/tmp/backend.log`
- Frontend log: `/tmp/frontend.log`

## Notes

- PostgreSQL is already configured and running on port 5432
- Frontend is running on port 3001
- Backend is running on port 8000
- PostgreSQL database `career_ai_db` is created and ready
- pgvector extension is enabled in the database