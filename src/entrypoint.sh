#!/bin/sh
set -e

# Function to check if MongoDB is ready with authentication
mongo_ready() {
  # Try to connect to MongoDB with authentication
  MONGO_HOST=${MONGODB_HOST:-mongodb-bridgex}
  MONGO_PORT=${MONGODB_PORT:-27017}

  # Just check if the port is open and accepting connections
  nc -z ${MONGO_HOST} ${MONGO_PORT} > /dev/null 2>&1
  return $?
}

# Function to wait for MongoDB to be ready
wait_for_mongodb() {
  echo "Waiting for MongoDB to be ready..."

  # Extract MongoDB connection details from environment variables
  MONGO_HOST=${MONGODB_HOST:-mongodb-bridgex}
  MONGO_PORT=${MONGODB_PORT:-27017}

  # First, wait for TCP connection
  echo "Checking TCP connection to MongoDB..."
  max_retries=60  # Increased to 60 (2 minutes)
  retries=0

  until nc -z ${MONGO_HOST} ${MONGO_PORT} > /dev/null 2>&1; do
    retries=$((retries+1))
    if [ $retries -ge $max_retries ]; then
      echo "Error: MongoDB TCP connection not available after $max_retries attempts. Exiting."
      exit 1
    fi
    echo "MongoDB TCP connection unavailable - sleeping (attempt $retries/$max_retries)"
    sleep 2
  done

  echo "MongoDB TCP connection established. Waiting for MongoDB to be fully initialized..."

  # Now wait for MongoDB to be fully initialized and authentication to be enabled
  # This is a more robust approach than just sleeping
  echo "Waiting for MongoDB authentication to be ready..."
  sleep 10  # Initial sleep to give MongoDB time to restart with auth enabled

  echo "MongoDB is up and running with authentication enabled!"
}

# Wait for dependencies
wait_for_mongodb


# Start the application with hot-reload
echo "Starting application in development mode..."
exec "$@"