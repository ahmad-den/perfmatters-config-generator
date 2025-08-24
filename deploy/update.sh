#!/bin/bash

# Update script for Perfmatters API
# Run as root: sudo bash deploy/update.sh

set -e

APP_DIR="/var/www/perfmatters-api"

echo "🔄 Updating Perfmatters API..."

cd $APP_DIR

# Backup current version
echo "💾 Creating backup..."
cp -r . ../perfmatters-api-backup-$(date +%Y%m%d-%H%M%S)

# Pull latest changes (if using git)
# git pull origin main

# Update Python dependencies
echo "📦 Updating dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Restart service
echo "🔄 Restarting service..."
systemctl restart perfmatters-api

# Check status
echo "✅ Update complete!"
systemctl status perfmatters-api --no-pager -l