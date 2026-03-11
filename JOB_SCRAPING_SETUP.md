# Job Scraping Setup Guide

## Overview
The Career AI System automatically fetches jobs from multiple sources:
- **International:** Remotive (remote jobs), Adzuna (with API key)
- **Kenyan:** BrighterMonday, Fuzu, KenyaJob

## Manual Job Fetching

Run the fetch_jobs command manually:
```bash
cd backend
source venv/bin/activate
python manage.py fetch_jobs
```

### Options:
- `--limit`: Number of jobs per source (default: 20)
- `--query`: Search query (default: all jobs)
- `--location`: Location filter (default: all locations)

### Examples:
```bash
# Fetch 10 jobs per source
python manage.py fetch_jobs --limit 10

# Fetch software developer jobs
python manage.py fetch_jobs --query "software developer"

# Fetch jobs in Nairobi
python manage.py fetch_jobs --location "Nairobi"

# Combined filters
python manage.py fetch_jobs --query "python developer" --location "Nairobi" --limit 15
```

## Automatic Job Fetching (Scheduled)

### Option 1: Cron Job (Linux/Mac)

Add to crontab:
```bash
crontab -e
```

Add this line (fetches jobs every 6 hours):
```cron
0 */6 * * * cd /home/ben/career\ AI\ system/backend && source venv/bin/activate && python manage.py fetch_jobs >> logs/job_fetch.log 2>&1
```

### Option 2: Systemd Timer (Linux)

Create `/etc/systemd/system/career-ai-fetch.service`:
```ini
[Unit]
Description=Career AI Job Fetch
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/home/ben/career AI system/backend
ExecStart=/home/ben/career AI system/backend/venv/bin/python manage.py fetch_jobs
User=ben
```

Create `/etc/systemd/system/career-ai-fetch.timer`:
```ini
[Unit]
Description=Run Career AI job fetch every 6 hours

[Timer]
OnCalendar=*:0/6
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl enable career-ai-fetch.timer
sudo systemctl start career-ai-fetch.timer
```

### Option 3: Python Script (Any OS)

Create `run_job_fetcher.py`:
```python
import time
import subprocess
from datetime import datetime

def fetch_jobs():
    print(f"[{datetime.now()}] Fetching jobs...")
    subprocess.run(["python", "manage.py", "fetch_jobs"])

def run_scheduled():
    while True:
        fetch_jobs()
        print("Next fetch in 6 hours...")
        time.sleep(6 * 60 * 60)  # 6 hours

if __name__ == "__main__":
    run_scheduled()
```

Run in background:
```bash
nohup python run_job_fetcher.py > logs/job_fetch.log 2>&1 &
```

## Monitoring

Check logs:
```bash
tail -f logs/job_fetch.log
```

Check database stats:
```bash
cd backend
source venv/bin/activate
python manage.py shell -c "from job_system.models import Job; print(f'Total: {Job.objects.count()}, Active: {Job.objects.filter(is_active=True).count()}')"
```

## Troubleshooting

### If scrapers fail:
1. Check network connection
2. Verify job board URLs are accessible
3. Check logs for specific errors
4. Some sites may block scraping - use proxies if needed

### If jobs not updating:
1. Check if external_id conflicts exist
2. Verify database is not locked
3. Check disk space
4. Review error logs

## Adding New Job Sources

1. Create new scraper class in `job_scraper.py`
2. Add to `JobFetcher._init_scrapers()` method
3. Test with manual fetch command
4. Deploy

## API Keys Required

Some sources require API keys:
- **Adzuna:** Get free API key at https://developer.adzuna.com/
- **LinkedIn:** Premium API access required
- **Indeed:** API access required

Add to `.env`:
```
ADZUNA_APP_ID=your_app_id
ADZUNA_APP_KEY=your_app_key