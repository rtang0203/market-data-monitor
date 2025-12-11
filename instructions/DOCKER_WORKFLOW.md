# Docker Workflow Guide

This guide covers how to build, test, and deploy the market data monitor Docker images.

## Architecture Overview

The project consists of four services:

| Service | Image | Description |
|---------|-------|-------------|
| `database` | `timescale/timescaledb:latest-pg15` | PostgreSQL with TimescaleDB (pulled from Docker Hub) |
| `collector` | `rtang0203/market-collector:latest` | Hyperliquid funding rate collector |
| `collector-lighter` | `rtang0203/lighter-collector:latest` | Lighter API funding rate collector |
| `dashboard` | `rtang0203/funding-dashboard:latest` | FastAPI dashboard server |

## Local Development

### Starting the Stack

```bash
cd ~/path/to/market-data-monitor
docker-compose up --build
```

This builds all images from source and starts the containers. Use `-d` to run in detached mode.

### Making Changes

1. Edit your Python files or Dockerfiles
2. Rebuild and restart:

```bash
docker-compose up --build
```

Or rebuild a specific service:

```bash
docker-compose up --build collector
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f collector
```

### Stopping the Stack

```bash
docker-compose down
```

To also remove the database volume (wipes all data):

```bash
docker-compose down -v
```

## Deploying to Droplet

The droplet has limited resources (1 CPU, 454MB RAM) and cannot build images efficiently. Instead, build locally and push to Docker Hub.

### Step 1: Build Images Locally

```bash
cd ~/path/to/market-data-monitor

docker build -t rtang0203/market-collector:latest .
docker build -t rtang0203/lighter-collector:latest -f Dockerfile.lighter .
docker build -t rtang0203/funding-dashboard:latest ./api
```

### Step 2: Push to Docker Hub

```bash
# Login if needed
docker login

# Push all images
docker push rtang0203/market-collector:latest
docker push rtang0203/lighter-collector:latest
docker push rtang0203/funding-dashboard:latest
```

### Step 3: Deploy on Droplet

SSH into your droplet and run:

```bash
cd ~/market-data-monitor
git pull                    # Get any code/config changes
docker-compose pull         # Pull new images from Docker Hub
docker-compose up -d        # Start containers in detached mode
```

### Verifying Deployment

```bash
# Check running containers
docker ps

# Check logs
docker-compose logs -f

# Check specific service
docker-compose logs -f collector
```

## Quick Reference

| Task | Command |
|------|---------|
| Start locally (with build) | `docker-compose up --build` |
| Start locally (detached) | `docker-compose up --build -d` |
| Stop stack | `docker-compose down` |
| View logs | `docker-compose logs -f` |
| Rebuild single service | `docker-compose up --build <service>` |
| Build for production | `docker build -t rtang0203/<image>:latest .` |
| Push to Docker Hub | `docker push rtang0203/<image>:latest` |
| Pull on droplet | `docker-compose pull` |
| Start on droplet | `docker-compose up -d` |

## Updating a Single Service

If you only changed one service (e.g., the collector):

**Locally:**

```bash
docker build -t rtang0203/market-collector:latest .
docker push rtang0203/market-collector:latest
```

**On droplet:**

```bash
docker-compose pull collector
docker-compose up -d collector
```

## Troubleshooting

### Container keeps restarting

```bash
docker-compose logs <service>
```

### Database connection issues

Ensure the database is healthy before other services start:

```bash
docker-compose ps
```

The `database` service should show as healthy.

### Clear everything and start fresh

```bash
docker-compose down -v
docker system prune -a
docker-compose up --build
```

### Check resource usage

```bash
docker stats
```