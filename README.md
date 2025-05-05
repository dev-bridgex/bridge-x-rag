# Bridge-X-RAG

A modular Retrieval-Augmented Generation (RAG) backend for Bridge-X, a social and e-learning platform designed for Egyptian university student activity teams.

## Overview

Bridge-X-RAG provides a robust API for knowledge management, document processing, and AI-powered search and chat capabilities. The system allows users to create knowledge bases, upload and process various document types, and interact with the content through semantic search and conversational interfaces.

## Architecture

The application follows a modular, clean architecture with clear separation of concerns:

### Core Modules

- **Knowledge Base Module**: Manages collections of related documents and their metadata
- **Asset Module**: Handles document upload, storage, and processing
- **NLP Module**: Provides vector database operations, hybrid search, and chatbot functionality

### Architectural Layers

- **Controllers**: Handle business logic and orchestrate operations
- **Models**: Define data structures and database interactions
- **Services**: Coordinate complex operations across multiple controllers and models
- **Routes**: Define API endpoints and handle HTTP requests/responses
- **Schemas**: Define request/response data validation and documentation

### Storage Providers

- **Vector Database**: Qdrant for semantic search capabilities
- **Document Database**: MongoDB for structured data storage and full-text search
- **LLM Providers**: OpenAI, Google Gemini, and Cohere for text generation and embeddings
- **Document Storage**: File system for document storage

## API Endpoints

The API is organized into the following groups:

- `/api/knowledge_bases`: Knowledge base management
- `/api/assets`: Asset (document) management and processing
- `/api/nlp`: Vector database operations and chatbot interactions
- `/api`: Base endpoints for health checks and application info

## Requirements

- Python 3.10 or later (required)
- uv 0.20 or later (recommended but not required)
- MongoDB
- OpenAI API key, Google API key, and/or Cohere API key
- spaCy with the en_core_web_sm model (for keyword extraction in hybrid search)

## Installation and Setup

### Using uv (Recommended)

1. Download and install uv from [here](https://docs.astral.sh/uv/getting-started/installation/)

2. Install Python 3.10 using uv:
   ```bash
   uv install python==3.10
   ```

3. Create a new virtual environment:
   ```bash
   uv venv .venv
   ```

4. Activate the virtual environment:
   ```bash
   source .venv/bin/activate  # On Unix/macOS
   .venv\Scripts\activate     # On Windows
   ```

5. Synchronize the project dependencies:
   ```bash
   uv sync
   ```

6. Install spaCy model for keyword extraction:
   ```bash
   python -m spacy download en_core_web_sm
   ```

7. Configure environment variables (create a `.env` file in the `src` directory):
   ```
   APP_NAME=Bridge-X-RAG
   APP_VERSION=0.1.0

   # MongoDB Config
   MONGODB_HOST=localhost
   MONGODB_PORT=27017
   MONGODB_USERNAME=admin
   MONGODB_PASSWORD=password
   MONGODB_DATABASE=bridge_x_rag

   # LLM Providers Config
   OPENAI_API_KEY=your_openai_api_key
   COHERE_API_KEY=your_cohere_api_key
   GEMINI_API_KEY=your_google_api_key

   # Provider Selection
   GENERATION_BACKEND=openai  # or cohere or google
   EMBEDDING_BACKEND=openai   # or cohere or google

   # Model Configuration
   GENERATION_MODEL_ID=gpt-3.5-turbo
   EMBEDDING_MODEL_ID=text-embedding-3-small
   EMBEDDING_MODEL_SIZE=1536

   # Vector DB Config
   VECTOR_DB_BACKEND=qdrant
   ```

8. Run the application (from the `src` directory):
   ```bash
   uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
   ```

### Using Docker

1. Build the Docker image:
   ```bash
   docker build -t bridge-x-rag .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 --env-file .env bridge-x-rag
   ```

## Deployment

The project includes comprehensive deployment configurations for both development and production environments.

### Development Deployment

For a quick development setup with Docker Compose:

1. Create environment files from examples:
   ```bash
   cp src/.env.example src/.env
   cp deployment/mongodb/.env.example deployment/mongodb/.env
   ```

2. Edit the environment files with your configuration

3. Run the deployment script:
   ```bash
   ./deployment/scripts/deploy.sh dev
   ```

   Or manually with Docker Compose:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

### Production Deployment

For a production deployment with SSL:

1. Create environment files from examples:
   ```bash
   cp src/.env.example src/.env
   cp deployment/mongodb/.env.example deployment/mongodb/.env
   ```

2. Edit the environment files with your configuration

3. Set up SSL certificates with Let's Encrypt:
   ```bash
   # Update domains in init-letsencrypt.sh
   chmod +x init-letsencrypt.sh
   ./init-letsencrypt.sh
   ```

4. Run the deployment script:
   ```bash
   ./deployment/scripts/deploy.sh prod
   ```

   Or manually with Docker Compose:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Backup and Restore

The project includes scripts for database backup:

```bash
# Create a backup
./deployment/scripts/backup.sh

# Backups are stored in the ./backups directory
```

For more detailed deployment instructions, see the [deployment README](deployment/README.md).

## Development

### Project Structure

```
src/
├── app/
│   ├── assets/           # Storage for uploaded files
│   ├── controllers/      # Business logic controllers
│   ├── db/               # Database connection and utilities
│   ├── helpers/          # Helper functions and utilities
│   ├── middleware/       # HTTP middleware
│   ├── models/           # Data models and schemas
│   │   ├── db_schemas/   # Pydantic models for database entities
│   │   └── enums/        # Enumeration types
│   ├── routes/           # API routes
│   │   ├── assets/       # Asset management routes
│   │   ├── knowledge_bases/ # Knowledge base management routes
│   │   ├── nlp/          # NLP and vector DB routes
│   │   └── schemas/      # Request/response schemas
│   ├── stores/           # External service integrations
│   │   ├── llm/          # LLM provider integrations
│   │   └── vectordb/     # Vector database integrations
│   └── utils/            # Utility functions
├── tests/                # Test suite
└── pyproject.toml        # Project dependencies
```

### Adding a New Feature

1. Identify the appropriate module (Knowledge Base, Asset, NLP)
2. Update or create models and schemas as needed
3. Implement business logic in controllers
4. Create service methods for complex operations
5. Define API routes and handlers
6. Update dependencies as needed
7. Write tests for the new functionality

## Hybrid Search

The system implements a hybrid search approach that combines:

1. **Semantic Search**: Uses vector embeddings stored in Qdrant to find semantically similar content
2. **Full-Text Search**: Uses MongoDB's text search capabilities to find keyword matches

The hybrid search normalizes and combines scores from both approaches, giving you the best of both worlds:
- Semantic understanding from vector search
- Keyword precision from full-text search

The text index is automatically created as part of the DataChunk schema, so no additional setup is required to use hybrid search.

To use hybrid search, set the `use_hybrid` parameter to `true` in your chat requests:

```json
{
  "query": "Your question here",
  "history": [],
  "use_rag": true,
  "use_hybrid": true,
  "limit": 5
}
```

## API Documentation

When the application is running, you can access the interactive API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### (Optional) Setup your command line interface for better readability

```bash
export PS1="\[\033[01;32m\]\u@\h:\w\n\[\033[00m\]\$ "
```

## License

[MIT License](LICENSE)
