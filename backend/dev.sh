#!/bin/bash

# Development script for VoiceFlow Backend with hot reload

echo "🚀 Starting VoiceFlow Backend with Hot Reload..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found! Please create one with your environment variables."
    exit 1
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Build and start with hot reload
echo "🔨 Building and starting containers..."
docker-compose up --build

echo "✅ Backend is running with hot reload!"
echo "📝 Edit any Python file to see automatic reload"
echo "🌐 API available at: http://localhost:8000"
echo "📚 API docs at: http://localhost:8000/docs"
