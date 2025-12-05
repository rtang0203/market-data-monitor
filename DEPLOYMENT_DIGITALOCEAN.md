# DigitalOcean Deployment Guide

## Step 1: Create DigitalOcean Account & Droplet

1. **Sign up** at [https://www.digitalocean.com/](https://www.digitalocean.com/)
   - New users often get **$200 credit for 60 days**!

2. **Create a Droplet** (their term for VM):
   - Click **Create** → **Droplets**
   - **Region**: Choose closest to you (e.g., New York, San Francisco, Amsterdam)
   - **Image**: Ubuntu 22.04 LTS
   - **Droplet Size**:
     - Basic plan
     - Regular (not Premium)
     - **$6/month: 1 GB RAM, 1 vCPU, 25 GB SSD** ← Choose this
   - **Authentication**:
     - Choose **SSH Key** (recommended) or **Password**
     - If SSH Key: Click "New SSH Key" and follow instructions
   - **Hostname**: `market-data-collector`
   - Click **Create Droplet**

3. **Wait** ~1 minute for droplet to be created

4. **Note your droplet's IP address** (shown in the dashboard)

## Step 2: SSH into Your Droplet

### If you used SSH key:
```bash
ssh root@YOUR_DROPLET_IP
```

### If you used password:
```bash
ssh root@YOUR_DROPLET_IP
# Enter the password sent to your email
```

## Step 3: Install Docker & Docker Compose

Once connected to your droplet:

```bash
# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt-get install -y docker-compose

# Install git
apt-get install -y git

# Verify installation
docker --version
docker-compose --version
git --version
```

## Step 4: Clone Your Repository

```bash
# Clone your repo
git clone https://github.com/rtang0203/market-data-monitor.git
cd market-data-monitor
```

## Step 5: Configure Environment Variables

Create a production `.env` file:

```bash
nano .env
```

Add this content (replace with your secure password):

```env
# Database Configuration
POSTGRES_DB=market_data
POSTGRES_USER=postgres
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD_HERE

# Collection Settings
COLLECTION_INTERVAL=1800

# Database Connection (used by collector)
DB_HOST=database
DB_PORT=5432
DB_NAME=market_data
DB_USER=postgres
DB_PASSWORD=YOUR_SECURE_PASSWORD_HERE
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

**Important**: Replace `YOUR_SECURE_PASSWORD_HERE` with a strong password!

## Step 6: Start Your Application

```bash
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f collector
```

## Step 7: Verify It's Working

```bash
# Check if containers are running
docker-compose ps

# Check if data is being collected
docker exec crypto_db psql -U postgres -d market_data -c "SELECT COUNT(*) FROM market_data;"

# View recent data
docker exec crypto_db psql -U postgres -d market_data -c "SELECT symbol, price, time FROM market_data ORDER BY time DESC LIMIT 10;"
```

## Updating Your Application

When you make changes to your code:

```bash
# SSH into droplet
ssh root@YOUR_DROPLET_IP

# Navigate to project
cd market-data-monitor

# Pull latest changes
git pull

# Rebuild and restart only the collector
docker-compose up -d --build collector

# Or restart everything
docker-compose up -d --build
```

## Monitoring

```bash
# View all logs
docker-compose logs -f

# View only collector logs
docker-compose logs -f collector

# Check container status
docker-compose ps

# Check resource usage
docker stats

# Check disk usage
df -h
```

## Backup Database

```bash
# Create backup
docker exec crypto_db pg_dump -U postgres market_data > backup_$(date +%Y%m%d).sql

# Download backup to local machine (run from your local terminal)
scp root@YOUR_DROPLET_IP:~/market-data-monitor/backup_YYYYMMDD.sql ~/backups/

# Restore from backup
docker exec -i crypto_db psql -U postgres -d market_data < backup_YYYYMMDD.sql
```

## Troubleshooting

### Containers not starting
```bash
docker-compose logs
docker-compose ps
```

### Database connection issues
```bash
# Check if database is healthy
docker exec crypto_db pg_isready -U postgres

# Check environment variables
docker exec market_data_collector env | grep DB_
```

### Out of disk space
```bash
# Check disk usage
df -h

# Clean up Docker
docker system prune -a
```

### View collector errors
```bash
# Recent logs
docker-compose logs --tail=100 collector

# Follow logs in real-time
docker-compose logs -f collector
```

## Security Recommendations

1. **Use SSH keys** instead of password authentication
2. **Change default password** - Use a strong, unique password in `.env`
3. **Set up firewall** - DigitalOcean Cloud Firewall or `ufw`:
   ```bash
   # Basic firewall setup
   ufw allow OpenSSH
   ufw enable
   ```
4. **Regular backups** - Set up automated database backups
5. **Monitor logs** - Check logs regularly for errors
6. **Update regularly** - Keep Docker and system packages updated:
   ```bash
   apt-get update && apt-get upgrade -y
   ```

## Stopping the Application

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data!)
docker-compose down -v
```
