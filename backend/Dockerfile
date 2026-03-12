FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create media and static directories
RUN mkdir -p media staticfiles logs

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8010

# Start Gunicorn
CMD ["gunicorn", "career_ai.wsgi:application", "--bind", "0.0.0.0:8010", "--workers", "3", "--timeout", "120"]
