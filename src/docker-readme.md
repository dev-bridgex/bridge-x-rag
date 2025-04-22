# Bridge-X-RAG Docker Image

A modular Retrieval-Augmented Generation (RAG) backend for Bridge-X, a social and e-learning platform designed for Egyptian university student activity teams.

## Quick Start

```bash
# Pull the image
docker pull devbridgex/bridge-x-rag:latest

# Run with basic configuration
docker run -p 8000:8000 \
  -e MONGODB_HOST=your-mongodb-host \
  -e MONGODB_PORT=27017 \
  -e MONGODB_USERNAME=your-username \
  -e MONGODB_PASSWORD=your-password \
  -e MONGODB_DATABASE=your-database \
  -e OPENAI_API_KEY=your-openai-key \
  devbridgex/bridge-x-rag:latest
```

## Environment Variables

The image accepts the following environment variables:

### Required

- `MONGODB_HOST`: MongoDB host
- `MONGODB_PORT`: MongoDB port
- `MONGODB_USERNAME`: MongoDB username
- `MONGODB_PASSWORD`: MongoDB password
- `MONGODB_DATABASE`: MongoDB database name
- `OPENAI_API_KEY` or `COHERE_API_KEY`: API key for the LLM provider

### Optional

- `GENERATION_BACKEND`: LLM provider for text generation (default: "openai")
- `EMBEDDING_BACKEND`: LLM provider for embeddings (default: "openai")
- `GENERATION_MODEL_ID`: Model ID for text generation (default: "gpt-3.5-turbo")
- `EMBEDDING_MODEL_ID`: Model ID for embeddings (default: "text-embedding-3-small")
- `EMBEDDING_MODEL_SIZE`: Size of embedding vectors (default: 1536)
- `VECTOR_DB_BACKEND`: Vector database backend (default: "qdrant")

## Volumes

You can mount the following volumes:

- `/app/assets/files`: For persistent storage of uploaded files
- `/app/assets/database`: For persistent storage of database files

Example:

```bash
docker run -p 8000:8000 \
  -v ./data/files:/app/assets/files \
  -v ./data/database:/app/assets/database \
  -e MONGODB_HOST=your-mongodb-host \
  # other environment variables...
  devbridgex/bridge-x-rag:latest
```

## Custom Entrypoint

You can override the default command with your own entrypoint script:

```bash
docker run -p 8000:8000 \
  # environment variables...
  --entrypoint /bin/bash \
  devbridgex/bridge-x-rag:latest \
  -c "your custom command"
```

## Docker Compose

For a complete setup with MongoDB, see the [GitHub repository](https://github.com/dev-bridgex/bridge-x-rag) for docker-compose examples.

## API Documentation

When the container is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

[MIT License](https://github.com/dev-bridgex/bridge-x-rag/blob/main/LICENSE)
