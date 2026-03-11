# Career AI System

A full-stack AI-driven Career Operating System for CV building, job applications, and interview preparation.

## Tech Stack

### Frontend
- Next.js 15 (React)
- TypeScript
- TailwindCSS

### Backend
- Django REST Framework
- PostgreSQL with pgvector extension
- JWT Authentication
- Custom Admin Panel (no Django admin)

### AI Infrastructure
- Ollama (Mistral 7B for development)
- CrewAI (Multi-agent orchestration)
- Open-source models (upgradeable to DeepSeek/LLaMA on GPU)
- Whisper (Speech-to-text)
- Coqui TTS (Text-to-speech)

## Project Structure

```
career AI system/
├── frontend/          # Next.js frontend
├── backend/           # Django REST backend
└── README.md
```

## Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 18+
- PostgreSQL 14+ with pgvector extension
- Ollama (for local LLM)

### 1. Database Setup (PostgreSQL + pgvector)

```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Install pgvector extension
# For Ubuntu/Debian:
sudo apt-get install postgresql-14-pgvector

# Or compile from source:
git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Start PostgreSQL
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql
```

In PostgreSQL shell:
```sql
-- Create database
CREATE DATABASE career_ai_db;

-- Create user
CREATE USER postgres WITH PASSWORD 'postgres';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE career_ai_db TO postgres;

-- Connect to database
\c career_ai_db

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Exit
\q
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

Backend will run at: http://localhost:8000

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will run at: http://localhost:3000

### 4. Ollama Setup (AI Models)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve

# Pull Mistral 7B (development model)
ollama pull mistral

# Test Ollama
ollama run mistral "Hello, how are you?"
```

Ollama API will be available at: http://localhost:11434

## Development Phases

### Phase 1: Infrastructure ✅
- [x] Next.js frontend
- [x] Django REST backend
- [ ] PostgreSQL + pgvector (setup instructions above)
- [ ] Ollama integration (setup instructions above)
- [x] CrewAI setup
- [x] Authentication system (JWT)
- [x] Custom admin panel (obscure URLs, unified login)
- [x] Basic dashboard UI

### Phase 2: CV Agent
- [ ] CV Builder & Optimization Agent

### Phase 3: Job System
- [ ] Job Discovery Agent
- [ ] Job Application Agent
- [ ] Career Guidance Agent

### Phase 4: Voice System
- [ ] Interview Simulation Agent
- [ ] Job Simulation Agent

### Phase 5: Intelligence
- [ ] AI memory system
- [ ] Personalization engine
- [ ] Analytics dashboard

## API Documentation

### Authentication Endpoints
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `GET /api/auth/profile/` - Get user profile
- `PUT /api/auth/profile/` - Update user profile

### Admin Panel Endpoints (Obfuscated)
**Admin URL path:** `/api/sys-mgmt-8832/` (configurable via `ADMIN_URL_PATH` env var)

Admin users login through the same `/api/auth/login/` endpoint as regular users. Admin access is determined by the `is_staff` flag on the user account.

- `GET /api/sys-mgmt-8832/` - Admin dashboard overview
- `GET /api/sys-mgmt-8832/users/` - List all users (admin only)
- `GET /api/sys-mgmt-8832/users/<id>/` - Get user details (admin only)
- `DELETE /api/sys-mgmt-8832/users/<id>/` - Delete user (admin only)

### Security Notes
- **No Django admin** - Custom admin panel implemented
- **Obscure admin URLs** - Admin endpoints use non-obvious paths
- **Unified authentication** - Admins use same login as regular users
- **JWT-based** - All authentication uses JWT tokens
- **Admin verification** - Admin status checked via `is_staff` flag

## Environment Variables

See `backend/.env.example` for all required environment variables.

Key variables:
- `ADMIN_URL_PATH` - Custom admin URL path (default: `sys-mgmt-8832`)
- `OLLAMA_HOST` - Ollama service URL (default: `http://localhost:11434`)
- `OLLAMA_MODEL` - AI model to use (default: `mistral`)

## License

MIT License