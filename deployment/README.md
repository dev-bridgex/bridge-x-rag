# Bridge-X-RAG Deployment

This directory contains deployment configurations and scripts for the Bridge-X-RAG application.

## Directory Structure

- **certbot/**: Let's Encrypt SSL certificate configuration
  - **conf/**: Certificate storage
  - **www/**: ACME challenge files
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

# Start the services using the deployment script
./deployment/scripts/deploy.sh dev

# Or manually with Docker Compose
docker-compose -f docker-compose.dev.yml up -d
```

### Production Environment

To deploy in production with SSL:

```bash
# From the project root
# Set up application environment
cp src/.env.example src/.env
# Edit src/.env with your production configuration

# Set up MongoDB environment
cp deployment/mongodb/.env.example deployment/mongodb/.env
# Edit deployment/mongodb/.env with your MongoDB configuration

# Set up SSL certificates with Let's Encrypt
# First, edit the init-letsencrypt.sh script to update your domain names and email
nano init-letsencrypt.sh

# Make the script executable and run it
chmod +x init-letsencrypt.sh
./init-letsencrypt.sh

# Start the services using the deployment script
./deployment/scripts/deploy.sh prod

# Or manually with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

## Environment Variables

The application uses separate environment files for different components:

- **Application**: `src/.env.example` - Main application configuration
- **MongoDB**: `deployment/mongodb/.env.example` - MongoDB database configuration

This separation follows the principle of least privilege, giving each service access only to the environment variables it needs.

### MongoDB Environment Variables

Create a `.env` file in the `deployment/mongodb` directory with:

```
MONGODB_ROOT_USER=admin
MONGODB_ROOT_PASSWORD=secure_admin_password
MONGODB_USERNAME=bridge_x_user
MONGODB_PASSWORD=secure_user_password
MONGODB_DATABASE=bridge_x_rag
```

### Application Environment Variables

The main application environment variables should be set in `src/.env`:

```
APP_NAME=Bridge-X-RAG
APP_VERSION=0.1.0

# MongoDB Config
MONGODB_HOST=mongodb-bridgex
MONGODB_PORT=27017
MONGODB_USERNAME=bridge_x_user
MONGODB_PASSWORD=secure_user_password
MONGODB_DATABASE=bridge_x_rag

# LLM Providers Config
OPENAI_API_KEY=your_openai_api_key
COHERE_API_KEY=your_cohere_api_key
GEMINI_API_KEY=your_google_api_key

# Provider Selection
GENERATION_BACKEND=openai
EMBEDDING_BACKEND=openai

# Model Configuration
GENERATION_MODEL_ID=gpt-3.5-turbo
EMBEDDING_MODEL_ID=text-embedding-3-small
EMBEDDING_MODEL_SIZE=1536

# Vector DB Config
VECTOR_DB_BACKEND=qdrant
```

## SSL Configuration with Let's Encrypt

The production deployment includes automatic SSL certificate provisioning and renewal using Let's Encrypt and Certbot:

1. The `init-letsencrypt.sh` script in the project root initializes SSL certificates
2. Nginx is configured to use these certificates and handle HTTPS traffic
3. Certbot container automatically renews certificates before they expire

To set up SSL:

1. Edit the `init-letsencrypt.sh` script to update:
   - `domains`: Your domain names (e.g., "example.com www.example.com")
   - `email`: Your email address for Let's Encrypt notifications
   - `staging`: Set to 1 for testing, 0 for production certificates

2. Run the script:
   ```bash
   chmod +x init-letsencrypt.sh
   ./init-letsencrypt.sh
   ```

3. Deploy with the production configuration:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Database Initialization

MongoDB is automatically initialized with the script in `mongodb/initdb.d/init-mongo.js`, which:

1. Creates the application database
2. Sets up the required user with appropriate permissions
3. Creates the necessary collections

## Backup and Restore

The project includes a backup script in `deployment/scripts/backup.sh` that:

1. Creates a timestamped backup of the MongoDB database
2. Stores the backup in the `backups` directory

To create a backup:

```bash
./deployment/scripts/backup.sh
```

To restore from a backup, see the MongoDB README in `mongodb/README.md` for detailed instructions.

## Troubleshooting

### SSL Certificate Issues

If you encounter SSL certificate issues:

1. Check the Certbot logs:
   ```bash
   docker logs certbot
   ```

2. Verify the certificate files exist in `deployment/certbot/conf/`

3. Check Nginx configuration:
   ```bash
   docker exec -it nginx nginx -t
   ```

### MongoDB Connection Issues

If the application cannot connect to MongoDB:

1. Check MongoDB logs:
   ```bash
   docker logs mongodb-bridgex
   ```

2. Verify MongoDB environment variables in both `deployment/mongodb/.env` and `src/.env`

3. Check if MongoDB is running:
   ```bash
   docker ps | grep mongodb-bridgex
   ```

### Application Startup Issues

If the application fails to start:

1. Check application logs:
   ```bash
   docker logs bridgex-rag-api
   ```

2. Verify all required environment variables are set in `src/.env`

3. Check if MongoDB is properly initialized:
   ```bash
   docker exec -it mongodb-bridgex mongosh -u $MONGODB_USERNAME -p $MONGODB_PASSWORD $MONGODB_DATABASE
   ```
