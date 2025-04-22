# Bridge-X-RAG Deployment

This directory contains deployment configurations and scripts for the Bridge-X-RAG application.

## Directory Structure

- **mongodb/**: MongoDB configuration files
  - **initdb.d/**: Database initialization scripts
- **nginx/**: Nginx configuration for production deployment
- **scripts/**: Utility scripts for deployment and maintenance

## Deployment Options

### Development Environment

To start the development environment:

```bash
# From the project root
# Set up application environment
cp src/.env.example src/.env
# Edit src/.env with your configuration

# Set up MongoDB environment
cp deployment/mongodb/.env.example deployment/mongodb/.env
# Edit deployment/mongodb/.env with your MongoDB configuration

# Start the services
docker-compose up -d
```

### Production Environment

To deploy in production:

```bash
# From the project root
# Set up application environment
cp src/.env.example src/.env
# Edit src/.env with your production configuration

# Set up MongoDB environment
cp deployment/mongodb/.env.example deployment/mongodb/.env
# Edit deployment/mongodb/.env with your MongoDB configuration

# Set up PostgreSQL environment
cp deployment/postgres/.env.example deployment/postgres/.env
# Edit deployment/postgres/.env with your PostgreSQL configuration

# Start the services
docker-compose -f docker-compose.prod.yml up -d
```

## Environment Variables

The application uses separate environment files for different components:

- **Application**: `src/.env.example` - Main application configuration
- **MongoDB**: `deployment/mongodb/.env.example` - MongoDB database configuration
- **PostgreSQL**: `deployment/postgres/.env.example` - PostgreSQL database configuration (production only)

This separation follows the principle of least privilege, giving each service access only to the environment variables it needs.

## Database Initialization

MongoDB is automatically initialized with the script in `mongodb/initdb.d/init-mongo.js`, which:

1. Creates the application database
2. Sets up the required user with appropriate permissions
3. Creates the necessary collections

## Backup and Restore

See the MongoDB README in `mongodb/README.md` for detailed instructions on backing up and restoring the database.
