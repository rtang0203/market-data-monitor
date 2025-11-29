# AWS Lightsail Deployment Guide

## Step 1: Create Lightsail Instance

1. Go to [AWS Lightsail Console](https://lightsail.aws.amazon.com/)
2. Click **Create instance**
3. Select:
   - **Platform**: Linux/Unix
   - **Blueprint**: OS Only → **Ubuntu 22.04 LTS**
   - **Instance plan**: $5/month (1 GB RAM, 1 vCPU, 40 GB SSD)
   - **Instance name**: `market-data-collector` (or your preference)
4. Click **Create instance**
5. Wait for instance to be running (~2 minutes)

## Step 2: Configure SSH Access

### Option A: Use Lightsail browser SSH (easiest)
- Click on your instance → Click **Connect using SSH**

### Option B: Use local terminal (recommended)
1. Download SSH key from Lightsail console
2. Save as `~/.ssh/lightsail-key.pem`
3. Set permissions:
   ```bash
   chmod 400 ~/.ssh/lightsail-key.pem
   ```
4. Get your instance's public IP from Lightsail console
5. SSH into instance:
   ```bash
   ssh -i ~/.ssh/lightsail-key.pem ubuntu@YOUR_INSTANCE_IP
   ```

## Step 3: Install Docker & Docker Compose

SSH into your instance and run:

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add ubuntu user to docker group (no sudo needed)
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt-get install -y docker-compose

# Verify installation
docker --version
docker-compose --version

# Log out and back in for group changes to take effect
exit
```

SSH back in after logging out.

## Step 4: Deploy Your Application

### Option A: Using Git (recommended)

1. **On your local machine**, push code to GitHub:
   ```bash
   # Initialize git if not already done
   git init
   git add .
   git commit -m "Ready for deployment"

   # Create GitHub repo and push
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **On Lightsail instance**, clone the repo:
   ```bash
   git clone YOUR_GITHUB_REPO_URL
   cd market-data-monitor
   ```

### Option B: Using SCP (alternative)

From your local machine:
```bash
scp -i ~/.ssh/lightsail-key.pem -r \
  /Users/randytang/Documents/projects/market-data-monitor \
  ubuntu@YOUR_INSTANCE_IP:~/
```

## Step 5: Configure Environment Variables

On the Lightsail instance:

```bash
cd market-data-monitor

# Create production .env file
cat > .env << 'EOF'
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
EOF

# Replace with a secure password
nano .env  # or vim .env
```

**Important**: Replace `YOUR_SECURE_PASSWORD_HERE` with a strong password!

## Step 6: Start the Application

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
# Check if data is being collected
docker exec crypto_db psql -U postgres -d market_data -c "SELECT COUNT(*) FROM market_data;"

# View recent data
docker exec crypto_db psql -U postgres -d market_data -c "SELECT symbol, price, time FROM market_data ORDER BY time DESC LIMIT 10;"
```

## Updating Your Application

When you make changes to your code:

```bash
# SSH into instance
ssh -i ~/.ssh/lightsail-key.pem ubuntu@YOUR_INSTANCE_IP

# Navigate to project
cd market-data-monitor

# Pull latest changes (if using Git)
git pull

# Rebuild and restart only the collector
docker-compose up -d --build collector

# Or restart everything
docker-compose up -d --build
```

## Monitoring

```bash
# View logs
docker-compose logs -f

# View only collector logs
docker-compose logs -f collector

# Check container status
docker-compose ps

# Check resource usage
docker stats
```

## Backup Database

```bash
# Create backup
docker exec crypto_db pg_dump -U postgres market_data > backup_$(date +%Y%m%d).sql

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

## Security Recommendations

1. **Change default password** - Don't use `developmentPassword` in production
2. **Set up firewall** - Use Lightsail firewall to only allow necessary ports
3. **Regular backups** - Set up automated database backups
4. **Monitor logs** - Check logs regularly for errors
5. **Update regularly** - Keep Docker and system packages updated
