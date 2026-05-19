#!/bin/bash

# ==============================================================================
# Django Deployment Script for Invoice Generator
# ==============================================================================
# This script automates the deployment process on the production server.
# Run this script from the server to pull latest changes and restart the app.
# 
# Usage: ./deploy.sh
# ==============================================================================

# Exit immediately if a command exits with a non-zero status
set -e

# Define variables
PROJECT_DIR="/var/www/invoice"
VENV_DIR="$PROJECT_DIR/venv"
# Replace 'gunicorn' or 'apache2' with your actual service name
SERVICE_NAME="gunicorn" 

echo "🚀 Starting deployment process for Invoice Generator..."

# 1. Navigate to the project directory
echo "📁 Navigating to project directory: $PROJECT_DIR"
cd $PROJECT_DIR

# 2. Pull the latest code from the repository
echo "⬇️  Pulling latest changes from Git..."
git pull origin main  # Change 'main' to 'master' if necessary

# 3. Activate the virtual environment
echo "🐍 Activating virtual environment..."
source $VENV_DIR/bin/activate

# 4. Install any new dependencies
echo "📦 Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# 5. Apply database migrations
echo "🗄️  Applying database migrations..."
python manage.py migrate

# 6. Collect static files
echo "🎨 Collecting static files..."
python manage.py collectstatic --noinput

# 7. Restart the web server/application service
echo "🔄 Restarting application service ($SERVICE_NAME)..."
# Uncomment the line that matches your server setup:

# For Gunicorn/Systemd:
# sudo systemctl restart $SERVICE_NAME

# For Apache:
sudo systemctl restart apache2



echo "✅ Deployment completed successfully!"
