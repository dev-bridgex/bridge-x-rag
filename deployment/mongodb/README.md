# MongoDB Configuration for Bridge-X-RAG

This guide explains how to set up and configure MongoDB for the Bridge-X-RAG application using Docker Compose.

## Overview

The Bridge-X-RAG application uses MongoDB as its primary database for storing:

- Knowledge base metadata
- Asset information
- Document chunks for retrieval
- User data and authentication information

## Prerequisites

- Docker Engine (20.10.0+)
- Docker Compose (v2.0.0+)
- Basic terminal/command line knowledge

## Configuration

### Docker Compose Configuration

The following Docker Compose configuration is used for MongoDB:

```yaml
version: '3.7'
services:
  mongodb:
    image: bitnami/mongodb:8.0
    container_name: mongodb
    ports:
      - "27017:27017"
    volumes:
      - ./mongodb/initdb.d/init-mongo.js:/docker-entrypoint-initdb.d/mongo-init.js:ro
      - mongodb-data:/bitnami/mongodb
      - mongodb-log:/opt/bitnami/mongodb/logs
    networks:
      - bridgex-rag
    env_file:
      - ./.env
    environment:
      - MONGODB_ROOT_USER=${MONGODB_ROOT_USER}
      - MONGODB_ROOT_PASSWORD=${MONGODB_ROOT_PASSWORD}
      - MONGODB_USERNAME=${MONGODB_USERNAME}
      - MONGODB_PASSWORD=${MONGODB_PASSWORD}
      - MONGODB_DATABASE=${MONGODB_DATABASE}
      - MONGODB_EXTRA_FLAGS=--wiredTigerCacheSizeGB=2
    restart: always

networks:
  bridgex-rag:

volumes:
  mongodb-data:
    driver: local
  mongodb-log:
    driver: local
```

### Environment Variables

Create a `.env` file in the root directory with the following MongoDB configuration:

```
# MongoDB Configuration
MONGODB_ROOT_USER=admin
MONGODB_ROOT_PASSWORD=secure_admin_password
MONGODB_USERNAME=bridge_x_user
MONGODB_PASSWORD=secure_user_password
MONGODB_DATABASE=bridge_x_rag
```

### Database Initialization Script

Create an initialization script at `mongodb/initdb.d/init-mongo.js`:

```javascript
// Switch to admin database and authenticate
db = db.getSiblingDB("admin");
db.auth(process.env.MONGODB_ROOT_USER, process.env.MONGODB_ROOT_PASSWORD);

// Switch to application database
db = db.getSiblingDB(process.env.MONGODB_DATABASE);

// Create application user
db.createUser({
    user: process.env.MONGODB_USERNAME,
    pwd: process.env.MONGODB_PASSWORD,
    roles: [
      'readWrite'
    ]
});

// Create collections for the application
db.createCollection('knowledge_bases');
db.createCollection('assets');
db.createCollection('chunks');
```

## Setup Instructions

### 1. Start MongoDB Container

```bash
# Navigate to the directory containing docker-compose.yml
cd /path/to/bridge-x-rag

# Start the MongoDB container
docker-compose up -d mongodb
```

### 2. Verify MongoDB Connection

```bash
# Connect to the MongoDB container
docker exec -it mongodb bash

# Check MongoDB version
mongod --version

# Connect to MongoDB with authentication
mongosh admin -u $MONGODB_ROOT_USER -p $MONGODB_ROOT_PASSWORD

# Switch to application database
use bridge_x_rag

# List collections
show collections
```

## Database Backup and Restore

### Creating a Backup

```bash
# Create a backup of the entire database
docker exec -it mongodb mongodump --uri="mongodb://$MONGODB_USERNAME:$MONGODB_PASSWORD@localhost:27017/$MONGODB_DATABASE" --gzip --archive=/tmp/bridge_x_rag_backup.gz

# Copy the backup file to the host machine
docker cp mongodb:/tmp/bridge_x_rag_backup.gz ./backups/
```

### Restoring from a Backup

```bash
# Copy the backup file to the container
docker cp ./backups/bridge_x_rag_backup.gz mongodb:/tmp/

# Restore the database
docker exec -it mongodb mongorestore --uri="mongodb://$MONGODB_USERNAME:$MONGODB_PASSWORD@localhost:27017/$MONGODB_DATABASE" --gzip --archive=/tmp/bridge_x_rag_backup.gz --drop
```

## MongoDB Schema

The Bridge-X-RAG application uses the following collections:

1. **knowledge_bases**: Stores metadata about knowledge bases
2. **assets**: Stores information about uploaded documents
3. **chunks**: Stores text chunks extracted from documents

Each collection has indexes defined in the corresponding model files in the application code.

## Troubleshooting

### Connection Issues

If you encounter connection issues:

1. Verify the MongoDB container is running:
   ```bash
   docker ps | grep mongodb
   ```

2. Check MongoDB logs:
   ```bash
   docker logs mongodb
   ```

3. Verify environment variables are correctly set in the `.env` file

### Data Persistence

MongoDB data is persisted in a Docker volume. To reset the database completely:

```bash
docker-compose down -v
docker-compose up -d mongodb
```

## Integration with Bridge-X-RAG

The application connects to MongoDB using the configuration specified in the `.env` file. The connection is managed by the `db/mongodb.py` module, which establishes a connection pool and provides access to the database throughout the application.

The modular architecture uses MongoDB for all persistent storage needs, with each module (Knowledge Base, Asset, NLP) interacting with its respective collections through model classes that inherit from `BaseDataModel`.