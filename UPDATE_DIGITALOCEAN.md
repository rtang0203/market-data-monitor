# Update Workflow for DigitalOcean

## Standard Update Process

### 1. SSH into your droplet
```bash
ssh root@YOUR_DROPLET_IP
```

### 2. Navigate to your project
```bash
cd market-data-monitor
```

### 3. Pull latest code
```bash
git pull
```

### 4. Rebuild and restart (ONLY the collector)
```bash
docker-compose up -d --build collector
```

This will:
- ✅ Rebuild the collector container with new code
- ✅ Restart only the collector
- ✅ Keep database running (no restart)
- ✅ Keep all data safe (database data persists)

---

## Will it affect the database data?

**NO!** Your data is 100% safe because:
- Database data lives in a Docker volume (separate from containers)
- Volumes persist even when containers are rebuilt/restarted
- You're only rebuilding the collector container, not the database

---

## Alternative: Rebuild Everything

If you want to be thorough:

```bash
docker-compose up -d --build
```

This rebuilds both containers, but **data still persists in the volume!**

---

## What Gets Updated vs. What Stays

### Updated:
- ✅ Collector code
- ✅ Container configuration

### Unchanged:
- ✅ All database data
- ✅ Database schema (unless you run migrations)
- ✅ Historical market data

---

## Quick Reference Card

```bash
# Standard update process
cd market-data-monitor
git pull
docker-compose up -d --build collector

# Check it worked
docker-compose ps
docker-compose logs -f collector
```

**Your data is completely safe!** The volume is independent of the containers.
