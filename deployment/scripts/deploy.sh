#!/bin/bash

# Bridge-X-RAG Deployment Script
# This script helps deploy the application in development or production mode

# Set default environment
ENV=${1:-dev}

# Display banner
echo "====================================="
echo "  Bridge-X-RAG Deployment Script"
echo "====================================="
echo "Environment: $ENV"
echo

# Check if environment files exist, if not create from examples
if [ ! -f "src/.env" ]; then
    echo "Creating src/.env file from src/.env.example..."
    cp src/.env.example src/.env
    echo "Please edit src/.env file with your configuration."
    MISSING_ENV=true
fi

if [ ! -f "deployment/mongodb/.env" ]; then
    echo "Creating MongoDB .env file from example..."
    cp deployment/mongodb/.env.example deployment/mongodb/.env
    echo "Please edit deployment/mongodb/.env file with your configuration."
    MISSING_ENV=true
fi

if [ "$ENV" = "prod" ] && [ ! -f "deployment/postgres/.env" ]; then
    echo "Creating PostgreSQL .env file from example..."
    cp deployment/postgres/.env.example deployment/postgres/.env
    echo "Please edit deployment/postgres/.env file with your configuration."
    MISSING_ENV=true
fi

if [ "$MISSING_ENV" = "true" ]; then
    echo "\nPlease edit the .env files with your configuration and run this script again."
    exit 0
fi

# Function to deploy development environment
deploy_dev() {
    echo "Deploying development environment..."
    docker-compose -f docker-compose.dev.yml down
    docker-compose -f docker-compose.dev.yml up -d
    echo "Development environment deployed successfully!"
}

# Function to deploy production environment
deploy_prod() {
    echo "Deploying production environment..."
    docker-compose -f docker-compose.prod.yml down
    docker-compose -f docker-compose.prod.yml up -d
    echo "Production environment deployed successfully!"
}

# Deploy based on environment
case $ENV in
    dev)
        deploy_dev
        ;;
    prod)
        deploy_prod
        ;;
    *)
        echo "Invalid environment. Use 'dev' or 'prod'."
        exit 1
        ;;
esac

# Display container status
echo
echo "Container status:"
docker-compose ps
