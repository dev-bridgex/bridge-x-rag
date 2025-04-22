# Bridge-X-RAG

A modular Retrieval-Augmented Generation (RAG) backend for Bridge-X, a social and e-learning platform designed for Egyptian university student activity teams.

## Overview

Bridge-X-RAG provides a robust API for knowledge management, document processing, and AI-powered search and chat capabilities. The system allows users to create knowledge bases, upload and process various document types, and interact with the content through semantic search and conversational interfaces.

## Architecture

The application follows a modular, clean architecture with clear separation of concerns:

### Core Modules

- **Knowledge Base Module**: Manages collections of related documents and their metadata
- **Asset Module**: Handles document upload, storage, and processing
- **NLP Module**: Provides vector database operations and chatbot functionality

### Architectural Layers

- **Controllers**: Handle business logic and orchestrate operations
- **Models**: Define data structures and database interactions
- **Services**: Coordinate complex operations across multiple controllers and models
- **Routes**: Define API endpoints and handle HTTP requests/responses
- **Schemas**: Define request/response data validation and documentation

### Storage Providers

- **Vector Database**: Qdrant for semantic search capabilities
- **LLM Providers**: OpenAI and Cohere for text generation and embeddings
- **Document Storage**: File system for document storage
- **Database**: MongoDB for structured data storage

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
- OpenAI API key and/or Cohere API key

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

6. Configure environment variables (create a `.env` file in the `src` directory):
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

   # Provider Selection
   GENERATION_BACKEND=openai  # or cohere
   EMBEDDING_BACKEND=openai   # or cohere

   # Model Configuration
   GENERATION_MODEL_ID=gpt-3.5-turbo
   EMBEDDING_MODEL_ID=text-embedding-3-small
   EMBEDDING_MODEL_SIZE=1536

   # Vector DB Config
   VECTOR_DB_BACKEND=qdrant
   ```

7. Run the application (from the `src` directory):
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
