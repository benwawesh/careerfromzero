# Career AI - Permanent Server Startup Guide

## Why Servers Keep Stopping

The servers were running in the background with a timeout, which caused them to stop. This guide provides a permanent solution using startup scripts that run in separate terminal windows.

## Quick Start (Permanent Solution)

### Step 1: Start Backend Server

Open a terminal and run:

```bash
./start-backend.sh
```

This will:
- Activate the Python virtual environment
- Install dependencies (if needed)
- Start the Django backend server on port 8000
- **Keep running until you press Ctrl+C**

### Step 2: Start Frontend Server

Open a **second terminal** and run:

```bash
./start-frontend.sh
```

This will:
- Install node_modules (if needed)
- Start the Next.js frontend server on port 3001
- **Keep running until you press Ctrl+C**

### Step 3: Access the Application

Open your browser and go to:

- **Frontend**: http://localhost:3001
- **Backend API**: http://localhost:8000

## Important Notes

### Why This Works Better

1. **Separate Terminals**: Each server runs in its own terminal window
2. **No Timeouts**: Servers don't have a timeout limit
3. **Control**: You can see logs and stop servers with Ctrl+C
4. **Auto-Install**: Scripts install dependencies automatically
5. **Persistent**: Servers run as long as you keep the terminals open

### Stopping the Servers

To stop the servers, press `Ctrl+C` in each terminal window where they're running.

### Restarting After Changes

If you make code changes:
- **Backend**: The Django dev server auto-reloads automatically
- **Frontend**: The Next.js dev server auto-reloads automatically

No need to restart manually!

## Troubleshooting

### Port Already in Use

If you see "Address already in use", kill the process:

**Backend (port 8000):**
```bash
lsof -ti:8000 | xargs kill -9
```

**Frontend (port 3001):**
```bash
lsof -ti:3001 | xargs kill -9
```

### Backend Won't Start

Make sure Python virtual environment exists:
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend Won't Start

Make sure Node.js is installed and run:
```bash
cd frontend
npm install
```

## Alternative: Using tmux/Screen (Advanced)

For a more robust solution, use `tmux` to keep servers running in detached sessions:

```bash
# Install tmux (if needed)
sudo apt-get install tmux

# Start backend in tmux
tmux new -s backend
./start-backend.sh
# Press Ctrl+B, then D to detach

# Start frontend in tmux
tmux new -s frontend
./start-frontend.sh
# Press Ctrl+B, then D to detach

# Reattach to view servers
tmux attach -t backend  # or frontend
```

## Project Structure

```
career AI system/
├── start-backend.sh      # Backend startup script
├── start-frontend.sh     # Frontend startup script
├── backend/             # Django backend (port 8000)
│   ├── manage.py
│   ├── venv/           # Python virtual environment
│   └── requirements.txt
└── frontend/           # Next.js frontend (port 3001)
    ├── package.json
    ├── node_modules/
    └── src/
```

## Phase 1 AI Curation Workflow

Once servers are running, access Phase 1 at:
**http://localhost:3001/jobs/ai-curate**

Features:
- Upload CV (PDF/Word)
- Use existing CV
- Enter CV details manually
- AI-powered job matching using Llama 3
- Match scores for all active jobs
- Skill analysis and recommendations

## Support

If you encounter issues:
1. Check the terminal logs for error messages
2. Ensure both servers are running
3. Verify ports 8000 and 3001 are not blocked
4. Make sure Python and Node.js are properly installed