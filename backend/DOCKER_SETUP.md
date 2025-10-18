# VoiceFlow AI Backend - Docker Setup

This document provides instructions for running the VoiceFlow AI backend using Docker.

## Prerequisites

- Docker and Docker Compose installed on your system
- Environment variables configured (see Configuration section)

## Quick Start

### 1. Clone and Navigate to Backend Directory

```bash
cd backend
```

### 2. Configure Environment Variables

Your `.env` file is already configured with the following services:
- **Supabase**: Database and authentication
- **ElevenLabs**: Voice synthesis and transcription
- **OpenAI**: AI response generation
- **Server**: Host and port configuration

The docker-compose.yml will automatically load all variables from your `.env` file.

### 3. Build and Run with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up --build -d
```

### 4. Verify the Setup

The API will be available at:
- **API Base URL**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Docker Commands

### Building the Image

```bash
# Build the Docker image
docker build -t voiceflow-backend .

# Build with specific tag
docker build -t voiceflow-backend:latest .
```

### Running the Container

```bash
# Run the container
docker run -p 8000:8000 --env-file .env voiceflow-backend

# Run in detached mode
docker run -d -p 8000:8000 --env-file .env --name voiceflow-backend voiceflow-backend
```

### Docker Compose Commands

```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f voiceflow-backend

# Restart services
docker-compose restart

# Rebuild and start
docker-compose up --build
```

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Your Supabase project URL | `https://your-project.supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `GROQ_API_KEY` | Groq API key | `gsk_...` |
| `ELEVENLABS_API_KEY` | ElevenLabs API key | `sk_...` |
| `JWT_SECRET_KEY` | JWT signing secret | `your-super-secret-key` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Application environment |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT token expiration |
| `MAX_FILE_SIZE_MB` | `50` | Maximum file upload size |

## Services

The Docker Compose setup includes:

### 1. VoiceFlow Backend (`voiceflow-backend`)
- **Port**: 8000
- **Image**: Built from local Dockerfile
- **Health Check**: `/health` endpoint
- **Dependencies**: Redis

### 2. Redis (`redis`)
- **Port**: 6379
- **Image**: `redis:7-alpine`
- **Purpose**: Background task queue and caching
- **Health Check**: Redis ping

## Development

### Local Development with Docker

```bash
# Start only the backend service
docker-compose up voiceflow-backend

# Start with live reload (mount source code)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Debugging

```bash
# View container logs
docker-compose logs -f voiceflow-backend

# Execute commands in running container
docker-compose exec voiceflow-backend bash

# Check container health
docker-compose ps
```

### Testing

```bash
# Run tests in container
docker-compose exec voiceflow-backend pytest

# Run tests with coverage
docker-compose exec voiceflow-backend pytest --cov=.
```

## Production Deployment

### Security Considerations

1. **Use strong JWT secrets** in production
2. **Restrict CORS origins** to your actual domains
3. **Use environment-specific** configuration files
4. **Enable HTTPS** with proper SSL certificates
5. **Use secrets management** for sensitive data

### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  voiceflow-backend:
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=WARNING
    restart: always
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
```

### Scaling

```bash
# Scale the backend service
docker-compose up --scale voiceflow-backend=3

# Use load balancer for multiple instances
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using port 8000
   lsof -i :8000
   
   # Kill the process or use different port
   docker-compose up -p 8001:8000
   ```

2. **Environment Variables Not Loading**
   ```bash
   # Check if .env file exists and has correct format
   cat .env
   
   # Verify environment variables in container
   docker-compose exec voiceflow-backend env
   ```

3. **Database Connection Issues**
   ```bash
   # Check database connectivity
   docker-compose exec voiceflow-backend python -c "from services.database_service import DatabaseService; print('DB OK')"
   ```

4. **Redis Connection Issues**
   ```bash
   # Check Redis connectivity
   docker-compose exec redis redis-cli ping
   ```

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check Redis health
docker-compose exec redis redis-cli ping

# Check all services
docker-compose ps
```

### Logs

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs voiceflow-backend

# Follow logs in real-time
docker-compose logs -f voiceflow-backend
```

## API Documentation

Once the service is running, you can access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Support

For issues or questions:

1. Check the logs: `docker-compose logs -f voiceflow-backend`
2. Verify environment variables: `docker-compose exec voiceflow-backend env`
3. Test health endpoint: `curl http://localhost:8000/health`
4. Check service status: `docker-compose ps`
