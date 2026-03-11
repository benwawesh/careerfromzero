#!/bin/bash

# Career AI - Frontend Server Startup Script
# Run this in a terminal to start the frontend server

echo "========================================="
echo "Career AI - Starting Frontend Server"
echo "========================================="
echo ""

cd "$(dirname "$0")/frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start server
echo ""
echo "Starting Next.js frontend server on port 3001..."
echo "Press Ctrl+C to stop the server"
echo ""

npm run dev -- --port 3001