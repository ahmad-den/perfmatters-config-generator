#!/bin/bash

# Production deployment script for Perfmatters API
# Run as root: sudo bash deploy/setup.sh

set -e

echo "🚀 Setting up Perfmatters API for production..."

# Variables
DOMAIN="perfmatters.checkmysite.app"
APP_DIR="/var/www/perfmatters-api"
NGINX_CONF="/etc/nginx/sites-available/$DOMAIN"
NGINX_ENABLED="/etc/nginx/sites-enabled/$DOMAIN"

# Create application directory
echo "📁 Creating application directory..."
mkdir -p $APP_DIR
mkdir -p $APP_DIR/logs
mkdir -p $APP_DIR/config
mkdir -p $APP_DIR/templates

# Copy application files
echo "📋 Copying application files..."
cp -r . $APP_DIR/
cd $APP_DIR

# Set up Python virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Set proper permissions
echo "🔐 Setting permissions..."
chown -R www-data:www-data $APP_DIR
chmod -R 755 $APP_DIR
chmod -R 644 $APP_DIR/logs

# Install and configure Nginx
echo "🌐 Configuring Nginx..."
cp nginx/perfmatters.checkmysite.app.conf $NGINX_CONF
ln -sf $NGINX_CONF $NGINX_ENABLED

# Test Nginx configuration
nginx -t

# Install systemd service
echo "⚙️  Installing systemd service..."
cp deploy/systemd/perfmatters-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable perfmatters-api

# Start services
echo "🚀 Starting services..."
systemctl start perfmatters-api
systemctl reload nginx

# Install SSL certificate with Certbot
echo "🔒 Installing SSL certificate..."
if command -v certbot &> /dev/null; then
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@checkmysite.app
else
    echo "⚠️  Certbot not found. Please install certbot and run:"
    echo "   sudo certbot --nginx -d $DOMAIN"
fi

# Show status
echo "✅ Deployment complete!"
echo ""
echo "🔍 Service status:"
systemctl status perfmatters-api --no-pager -l

echo ""
echo "🌐 Nginx status:"
systemctl status nginx --no-pager -l

echo ""
echo "🎯 API should be available at: https://$DOMAIN"
echo ""
echo "📊 Test the API:"
echo "curl -X GET https://$DOMAIN/health"
echo ""
echo "📝 View logs:"
echo "sudo journalctl -u perfmatters-api -f"
echo "sudo tail -f $APP_DIR/logs/access.log"