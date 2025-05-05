#!/bin/bash
set -e

# Configuration
IMAGE_NAME="devbridgex/bridge-x-rag"
VERSION=$(grep -oP 'version="\K[^"]+' src/pyproject.toml || echo "0.1.0")
PLATFORMS="linux/amd64,linux/arm64"

# Display banner
echo "====================================="
echo "  Bridge-X-RAG Docker Publisher"
echo "====================================="
echo "Version: $VERSION"
echo "Platforms: $PLATFORMS"
echo

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running or not accessible"
  exit 1
fi

# Check if user is logged in to Docker Hub
if ! docker info | grep -q "Username"; then
  echo "You are not logged in to Docker Hub. Please login:"
  docker login
fi

# Build the image
echo "Building Docker image..."
docker build -t $IMAGE_NAME:$VERSION -t $IMAGE_NAME:latest -f src/Dockerfile src/

# Copy the Docker Hub README
echo "Preparing Docker Hub README..."
cp src/docker-readme.md README.docker.md

# Optional: Build multi-platform images
if command -v docker-buildx &> /dev/null; then
  read -p "Do you want to build multi-platform images? This may take longer. (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Building multi-platform images using buildx..."
    docker buildx create --use
    docker buildx build --platform $PLATFORMS -t $IMAGE_NAME:$VERSION -t $IMAGE_NAME:latest --push -f src/Dockerfile src/
    echo "Multi-platform images built and pushed successfully!"
    exit 0
  fi
fi

# Push the image
echo "Pushing Docker image to Docker Hub..."
docker push $IMAGE_NAME:$VERSION
docker push $IMAGE_NAME:latest

echo
echo "Docker image published successfully!"
echo "  Image: $IMAGE_NAME:$VERSION"
echo "  Image: $IMAGE_NAME:latest"
echo
echo "You can pull it with: docker pull $IMAGE_NAME:latest"
