from app.helpers.config import get_settings
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from typing import Type, Optional, List, Any, Dict, TypeVar, Generic, Tuple
from pymongo import InsertOne, UpdateOne, DeleteOne, ReplaceOne

T = TypeVar('T', bound=BaseModel)

class BaseDataModel(Generic[T]):
    
    def __init__(self, db_client: AsyncIOMotorDatabase, collection_name: Optional[str] = None):
        self.db_client = db_client
        self.app_settings = get_settings()
        if collection_name:
            self.collection = self.db_client[collection_name]
        
    @classmethod
    async def create_instance(cls, db_client: AsyncIOMotorDatabase, collection_name: Optional[str] = None, schema_model: Optional[Type[BaseModel]] = None):
        """
        Create an instance of the model and initialize its collection.
        
        Args:
            db_client: The database client
            collection_name: The name of the collection (optional if provided in subclass)
            schema_model: The Pydantic model that defines the schema (optional if provided in subclass)
            
        Returns:
            An initialized instance of the model
        """
        instance = cls(db_client, collection_name)
        await instance.init_collection(collection_name, schema_model)
        return instance

    async def init_collection(self, collection_name: Optional[str] = None, schema_model: Optional[Type[BaseModel]] = None):
        """
        Initialize the collection, creating it and its indexes if it doesn't exist.
        
        Args:
            collection_name: The name of the collection
            schema_model: The Pydantic model that defines the schema and indexes
        """
        # Allow subclasses to override these parameters
        collection_name = getattr(self, 'get_collection_name', lambda: collection_name)()
        schema_model = getattr(self, 'get_schema_model', lambda: schema_model)()
        
        if not collection_name or not schema_model:
            raise ValueError("Collection name and schema model must be provided either as parameters or by overriding methods")
            
        all_collections = await self.db_client.list_collection_names()
        if collection_name not in all_collections:
            self.collection = self.db_client[collection_name]
            # Get indexes from the schema model
            indexes_method = getattr(schema_model, 'get_indexes', None)
    
            if indexes_method:
                indexes = indexes_method()
                for index in indexes:
                    await self.collection.create_index(
                        index["key"],
                        name=index["name"],
                        unique=index["unique"]
                    )
        else:
            # Ensure collection is set even if it already exists
            self.collection = self.db_client[collection_name]
    
    # Standard CRUD operations
    async def create(self, model_instance: T) -> T:
        """
        Create a new document in the collection.
        
        Args:
            model_instance: The model instance to create
            
        Returns:
            The created model instance with ID populated
        """
        result = await self.collection.insert_one(
            model_instance.model_dump(by_alias=True, exclude_unset=True)
        )
        model_instance.id = result.inserted_id
        return model_instance
    
    async def find_one(self, filter_dict: Dict[str, Any]) -> Optional[T]:
        """
        Find a single document in the collection.
        
        Args:
            filter_dict: The filter to apply
            
        Returns:
            The found model instance or None
        """
        schema_model = self.get_schema_model()
        result = await self.collection.find_one(filter_dict)
        if result is None:
            return None
        return schema_model(**result)
    
    async def find_many(self, 
                       filter_dict: Dict[str, Any], 
                       skip: int = 0, 
                       limit: int = 0, 
                       sort: Optional[List[tuple]] = None) -> List[T]:
        """
        Find multiple documents in the collection.
        
        Args:
            filter_dict: The filter to apply
            skip: Number of documents to skip
            limit: Maximum number of documents to return (0 for no limit)
            sort: List of (field, direction) tuples for sorting
            
        Returns:
            List of model instances
        """
        schema_model = self.get_schema_model()
        cursor = self.collection.find(filter_dict)
        
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        if sort:
            cursor = cursor.sort(sort)
            
        results = []
        async for document in cursor:
            results.append(schema_model(**document))
            
        return results
    
    async def update_one(self, filter_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> bool:
        """
        Update a single document in the collection.
        
        Args:
            filter_dict: The filter to apply
            update_dict: The update to apply
            
        Returns:
            True if a document was updated, False otherwise
        """
        result = await self.collection.update_one(
            filter_dict,
            {"$set": update_dict}
        )
        return result.modified_count > 0
    
    async def delete_one(self, filter_dict: Dict[str, Any]) -> bool:
        """
        Delete a single document from the collection.
        
        Args:
            filter_dict: The filter to apply
            
        Returns:
            True if a document was deleted, False otherwise
        """
        result = await self.collection.delete_one(filter_dict)
        return result.deleted_count > 0
    
    async def delete_many(self, filter_dict: Dict[str, Any]) -> int:
        """
        Delete multiple documents from the collection.
        
        Args:
            filter_dict: The filter to apply
            
        Returns:
            Number of documents deleted
        """
        result = await self.collection.delete_many(filter_dict)
        return result.deleted_count
    
    async def count_documents(self, filter_dict: Dict[str, Any]) -> int:
        """
        Count documents in the collection.
        
        Args:
            filter_dict: The filter to apply
            
        Returns:
            Number of matching documents
        """
        return await self.collection.count_documents(filter_dict)
        
    async def paginate(self, 
                      filter_dict: Dict[str, Any], 
                      page: int = 1, 
                      page_size: int = 10,
                      sort: Optional[List[tuple]] = None) -> Tuple[List[T], int, int]:
        """
        Get paginated results from the collection.
        
        Args:
            filter_dict: The filter to apply
            page: Page number (1-based)
            page_size: Number of items per page
            sort: List of (field, direction) tuples for sorting
            
        Returns:
            Tuple of (items, total_pages, total_items)
        """
        # Ensure page is at least 1
        page = max(1, page)
        
        # Calculate skip value
        skip = (page - 1) * page_size
        
        # Count total documents for pagination
        total_documents = await self.count_documents(filter_dict)
        
        # Calculate total pages
        total_pages = (total_documents + page_size - 1) // page_size if total_documents > 0 else 0
        
        # Get items for the current page
        items = await self.find_many(filter_dict, skip=skip, limit=page_size, sort=sort)
        
        return items, total_pages, total_documents
    
    # Bulk operations
    async def create_many(self, model_instances: List[T], batch_size: int = 100) -> int:
        """
        Create multiple documents in the collection.
        
        Args:
            model_instances: List of model instances to create
            batch_size: Number of documents to insert in each batch
            
        Returns:
            Number of documents created
        """
        total_created = 0
        
        for i in range(0, len(model_instances), batch_size):
            batch = model_instances[i:i+batch_size]
            
            operations = [
                InsertOne(model.model_dump(by_alias=True, exclude_unset=True))
                for model in batch
            ]
            
            result = await self.collection.bulk_write(operations)
            total_created += result.inserted_count
            
        return total_created
    
    async def bulk_write(self, operations: List[Any], ordered: bool = True) -> Any:
        """
        Perform a bulk write operation.
        
        Args:
            operations: List of pymongo operations (InsertOne, UpdateOne, etc.)
            ordered: Whether the operations should be executed in order
            
        Returns:
            The result of the bulk write operation
        """
        return await self.collection.bulk_write(operations, ordered=ordered)
    
    def prepare_bulk_operations(self, models: List[T], operation_type: str = 'insert') -> List[Any]:
        """
        Prepare bulk operations for the given models.
        
        Args:
            models: List of model instances
            operation_type: Type of operation ('insert', 'update', 'replace', 'delete')
            
        Returns:
            List of pymongo operations
        """
        operations = []
        
        for model in models:
            model_dict = model.model_dump(by_alias=True, exclude_unset=True)
            model_id = model_dict.get('_id')
            
            if operation_type == 'insert':
                operations.append(InsertOne(model_dict))
            elif operation_type == 'update':
                if model_id:
                    operations.append(UpdateOne({'_id': model_id}, {'$set': model_dict}))
            elif operation_type == 'replace':
                if model_id:
                    operations.append(ReplaceOne({'_id': model_id}, model_dict))
            elif operation_type == 'delete':
                if model_id:
                    operations.append(DeleteOne({'_id': model_id}))
                    
        return operations