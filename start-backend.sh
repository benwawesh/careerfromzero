#!/bin/bash

# Career AI - Backend Server Startup Script
# Run this in a terminal to start the backend server

echo "========================================="
echo "Career AI - Starting Backend Server"
echo "========================================="
echo ""

cd "$(dirname "$0")/backend"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found!"
    echo "Please create it first with: python -m venv venv"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if requirements are installed
if [ ! -f ".installed" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    touch .installed
fi

# Start the server
echo ""
echo "Starting Django backend server on port 8000..."
echo "Press Ctrl+C to stop the server"
echo ""

python manage.py runserver 8000