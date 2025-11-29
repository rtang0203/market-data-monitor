#!/bin/bash
# Setup script for AWS Lightsail Ubuntu instance
# Run this after SSH'ing into your Lightsail instance

set -e

echo "================================"
echo "Market Data Collector - Lightsail Setup"
echo "================================"
echo ""

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# Add user to docker group
echo "👤 Adding user to docker group..."
sudo usermod -aG docker $USER

# Install Docker Compose
echo "📦 Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo apt-get install -y docker-compose
    echo "✅ Docker Compose installed"
else
    echo "✅ Docker Compose already installed"
fi

# Install git if not present
echo "📦 Installing Git..."
if ! command -v git &> /dev/null; then
    sudo apt-get install -y git
    echo "✅ Git installed"
else
    echo "✅ Git already installed"
fi

echo ""
echo "================================"
echo "✅ Setup Complete!"
echo "================================"
echo ""
echo "Docker version: $(docker --version)"
echo "Docker Compose version: $(docker-compose --version)"
echo ""
echo "⚠️  IMPORTANT: You must log out and back in for docker group changes to take effect!"
echo ""
echo "Next steps:"
echo "1. Exit this SSH session: exit"
echo "2. SSH back into the instance"
echo "3. Clone your repository or copy your code"
echo "4. Create .env file with production settings"
echo "5. Run: docker-compose up -d"
echo ""
