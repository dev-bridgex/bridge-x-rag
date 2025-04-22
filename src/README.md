# Bridge-X-RAG Source Code

This directory contains the source code for the Bridge-X-RAG application. This README provides technical details about the implementation, code organization, and development guidelines.

## Code Organization

### Modular Architecture

The application follows a modular architecture with the following key components:

#### Core Modules

- **Knowledge Base Module**: Replaces the previous Project concept with a more semantically appropriate Knowledge Base model
- **Asset Module**: Handles document management with improved processing capabilities
- **NLP Module**: Provides vector database operations and conversational AI features

#### Service Layer

Each module includes a service layer that orchestrates complex operations across multiple controllers and models:

- `KnowledgeBaseService`: Manages knowledge base lifecycle operations
- `AssetService`: Coordinates asset processing and management
- `NLPService`: Handles vector database and chatbot interactions

### Dependency Injection

The application uses FastAPI's dependency injection system to manage dependencies between components. The `dependencies.py` file centralizes all dependency providers:

```python
# Example from dependencies.py
async def get_knowledge_base_model(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Dependency for KnowledgeBaseModel"""
    return await KnowledgeBaseModel.create_instance(db_client=db)

def get_knowledge_base_controller():
    """Dependency for KnowledgeBaseController"""
    return KnowledgeBaseController()
```

### Error Handling

The application uses a standardized error handling approach with typed error responses:

- `ErrorType` enum defines specific error categories
- `ErrorResponse` schema provides consistent error reporting
- Helper functions in `exception_handlers.py` simplify raising common errors

## Development Guidelines

### Adding a New Endpoint

1. Identify the appropriate module (Knowledge Base, Asset, NLP)
2. Create or update schemas in the module's `schemas.py` file
3. Implement business logic in the appropriate controller
4. Add service methods for complex operations
5. Define the endpoint in the module's route file
6. Update dependencies as needed

### Model Relationships

The data models use lazy-loaded relationships to prevent circular imports:

```python
async def _init_related_models(self):
    """Initialize related models if they haven't been initialized yet"""
    if self.asset_model is None or self.chunk_model is None:
        from app.models import AssetModel, ChunkModel
        self.asset_model = await AssetModel.create_instance(db_client=self.db_client)
        self.chunk_model = await ChunkModel.create_instance(db_client=self.db_client)
```

### Vector Database Operations

Vector database operations are handled through the `NLPController` and abstracted by the `VectorDBProviderInterface`:

```python
async def index_asset_into_vector_db(self, knowledge_base, asset, chunks, chunks_ids, do_reset=False, skip_duplicates=True):
    # Implementation details...
```

### File Processing

Document processing is handled by the `AssetController` using LangChain document loaders:

```python
def get_file_loader(self, file_name: str, file_path: str):
    """Get the appropriate document loader for a file based on its extension"""
    file_extension = self.get_file_extension(file_name=file_name)

    if file_extension == FileTypesEnum.TXT.value:
        return TextLoader(file_path, encoding="utf-8")

    if file_extension == FileTypesEnum.PDF.value:
        return PyMuPDFLoader(file_path)

    return None
```

## Configuration

The application uses environment variables for configuration, loaded through Pydantic's `BaseSettings`:

```python
class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    # Other settings...

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

## Testing

Tests are located in the `tests` directory. The application is designed for testability with dependency injection making it easy to mock components.

## API Documentation

API documentation is automatically generated from the route definitions and schemas. The application uses Pydantic models with detailed field descriptions to provide comprehensive API documentation.

```python
class KnowledgeBaseResponse(KnowledgeBaseBase):
    """Schema for knowledge base response"""
    id: str
    knowledge_base_dir_path: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```
