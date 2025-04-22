from app.models import KnowledgeBaseModel
from app.models.db_schemas import KnowledgeBase
from app.controllers import KnowledgeBaseController, NLPController
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Tuple, Dict, Any, Optional
from app.logging import get_logger
from app.exception_handlers import raise_http_exception, raise_knowledge_base_not_found, raise_resource_conflict
from app.models.enums.ErrorTypes import ErrorType
# datetime and timezone are now handled in the model layer

logger = get_logger(__name__)

class KnowledgeBaseService:
    """Service class for complex knowledge base operations that span multiple controllers and models"""

    def __init__(self, db: AsyncIOMotorDatabase, knowledge_base_model: KnowledgeBaseModel,
                 knowledge_base_controller: KnowledgeBaseController = None, nlp_controller: NLPController = None):
        self.db = db
        self.knowledge_base_model = knowledge_base_model
        self.knowledge_base_controller = knowledge_base_controller or KnowledgeBaseController()
        self.nlp_controller = nlp_controller

    def _validate_knowledge_base_name(self, knowledge_base_name: str) -> Dict[str, Any]:
        """Validate a knowledge base name for invalid characters or other constraints

        Args:
            knowledge_base_name: The name to validate

        Returns:
            Dict with 'valid' (bool) and 'reason' (str) if invalid
        """
        # Check if name is None or empty
        if not knowledge_base_name:
            return {
                'valid': False,
                'reason': "Knowledge base name cannot be empty."
            }

        # Check if name is just whitespace
        if not knowledge_base_name.strip():
            return {
                'valid': False,
                'reason': "Knowledge base name cannot be just whitespace."
            }

        # Check for minimum length (business rule: at least 3 characters)
        if len(knowledge_base_name.strip()) < 3:
            return {
                'valid': False,
                'reason': f"Knowledge base name '{knowledge_base_name}' is too short. Name must be at least 3 characters."
            }

        # Check for invalid characters (common filesystem restrictions)
        # Only truly problematic filesystem characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in knowledge_base_name for char in invalid_chars):
            return {
                'valid': False,
                'reason': f"Knowledge base name '{knowledge_base_name}' contains invalid characters. The following characters are not allowed: {', '.join(invalid_chars)}"
            }

        # All checks passed
        return {'valid': True}

    async def create_knowledge_base(self, knowledge_base_name: str) -> KnowledgeBase:
        """Create a new knowledge base"""
        try:
            # Validate knowledge base name
            validation_result = self._validate_knowledge_base_name(knowledge_base_name)
            if not validation_result['valid']:
                raise_http_exception(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_type=ErrorType.INVALID_REQUEST.value,
                    detail=validation_result['reason']
                )

            # Check if knowledge base with this name already exists
            # The name will be standardized to lowercase by the validator
            existing_knowledge_base = await self.knowledge_base_model.get_knowledge_base_by_name(knowledge_base_name=knowledge_base_name.lower())
            if existing_knowledge_base is not None:
                raise_resource_conflict("knowledge base", knowledge_base_name)

            # Create knowledge base in database
            knowledge_base = KnowledgeBase(knowledge_base_name=knowledge_base_name)
            knowledge_base = await self.knowledge_base_model.create(knowledge_base)
            logger.info(f"Created knowledge base in database: {knowledge_base.id}")

            # Create knowledge base directory
            knowledge_base_dir_path = self.knowledge_base_controller.get_knowledge_base_path(knowledge_base_id=str(knowledge_base.id))
            logger.info(f"Created knowledge base directory: {knowledge_base_dir_path}")

            # Update knowledge base with directory path
            update_data = {
                "knowledge_base_dir_path": knowledge_base_dir_path
            }

            # Use the data-focused method in the model
            success, updated_knowledge_base = await self.knowledge_base_model.update_knowledge_base_data(
                knowledge_base_id=str(knowledge_base.id),
                update_data=update_data
            )

            if not success:
                raise_http_exception(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    error_type=ErrorType.DATABASE_ERROR.value,
                    detail="Failed to update knowledge base with directory path"
                )

            # Use the updated knowledge base
            knowledge_base = updated_knowledge_base
            return knowledge_base

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error creating knowledge base: {e}")
            raise_http_exception(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type=ErrorType.DATABASE_ERROR.value,
                detail=f"Failed to create knowledge base: {str(e)}"
            )

    async def get_knowledge_base_by_id(self, knowledge_base_id) -> KnowledgeBase:
        """Get a knowledge base by ID

        Args:
            knowledge_base_id: The ID of the knowledge base

        Returns:
            The knowledge base

        Raises:
            HTTPException: If the knowledge base is not found
        """
        knowledge_base = await self.knowledge_base_model.get_knowledge_base_by_id(knowledge_base_id=knowledge_base_id)
        if knowledge_base is None:
            raise_knowledge_base_not_found(knowledge_base_id)

        return knowledge_base

    async def get_all_knowledge_bases(self, page: int = 1, page_size: int = 10) -> Tuple[List[KnowledgeBase], int, int]:
        """Get all knowledge bases with pagination

        Args:
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Tuple of (knowledge_bases, total_pages, total_items)
        """
        return await self.knowledge_base_model.get_all_knowledge_bases(page=page, page_size=page_size)

    async def update_knowledge_base(self, knowledge_base_id, knowledge_base_name: Optional[str] = None) -> Tuple[KnowledgeBase, bool]:
        """Update a knowledge base and its resources

        Args:
            knowledge_base_id: The ID of the knowledge base to update
            knowledge_base_name: The new name for the knowledge base (optional)

        Returns:
            Tuple of (updated_knowledge_base, resources_updated)

        Raises:
            HTTPException: If the knowledge base is not found or update fails
        """
        # If knowledge_base_name is None, get the current name and return early
        if knowledge_base_name is None:
            # Get the current knowledge base
            knowledge_base = await self.knowledge_base_model.get_knowledge_base_by_id(knowledge_base_id=knowledge_base_id)
            if knowledge_base is None:
                raise_knowledge_base_not_found(knowledge_base_id)

            # No changes to make
            return knowledge_base, False

        # Validate knowledge base name
        validation_result = self._validate_knowledge_base_name(knowledge_base_name)
        if not validation_result['valid']:
            raise_http_exception(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_type=ErrorType.INVALID_REQUEST.value,
                detail=validation_result['reason']
            )

        # Standardize the name to lowercase for consistency
        knowledge_base_name = knowledge_base_name.lower()

        # Ensure NLP controller is available
        if not self.nlp_controller:
            raise ValueError("NLPController is required for updating a knowledge base")

        # Get the current knowledge base
        knowledge_base = await self.knowledge_base_model.get_knowledge_base_by_id(knowledge_base_id=knowledge_base_id)
        if knowledge_base is None:
            raise_knowledge_base_not_found(knowledge_base_id)

        # Check if new name is different from current name
        if knowledge_base_name == knowledge_base.knowledge_base_name:
            # No changes needed
            return knowledge_base, False

        # Check if knowledge base with the new name already exists
        existing_knowledge_base = await self.knowledge_base_model.get_knowledge_base_by_name(knowledge_base_name=knowledge_base_name)
        if existing_knowledge_base is not None:
            raise_resource_conflict("knowledge base", knowledge_base_name)

        # Update knowledge base in MongoDB
        update_data = {
            "knowledge_base_name": knowledge_base_name
        }

        success, updated_knowledge_base = await self.knowledge_base_model.update_knowledge_base_data(
            knowledge_base_id=knowledge_base_id,
            update_data=update_data
        )

        if not success:
            raise_http_exception(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type=ErrorType.DATABASE_ERROR.value,
                detail=f"Failed to update knowledge base with ID '{knowledge_base_id}' in database"
            )

        # Update knowledge base resources in vector database and file system
        resources_updated = await self.knowledge_base_controller.update_knowledge_base_resources(
            knowledge_base=updated_knowledge_base,
            new_knowledge_base_name=knowledge_base_name,
            nlp_controller=self.nlp_controller
        )

        return updated_knowledge_base, resources_updated

    async def delete_knowledge_base(self, knowledge_base_id) -> Dict[str, Any]:
        """Delete a knowledge base and all its resources

        Args:
            knowledge_base_id: The ID of the knowledge base to delete

        Returns:
            Dict: A dictionary with information about the deletion

        Raises:
            HTTPException: If the knowledge base is not found or deletion fails
        """
        try:
            # Ensure NLP controller is available
            if not self.nlp_controller:
                raise ValueError("NLPController is required for deleting a knowledge base")

            # Get knowledge base by ID
            knowledge_base = await self.knowledge_base_model.get_knowledge_base_by_id(knowledge_base_id=knowledge_base_id)
            if knowledge_base is None:
                raise_knowledge_base_not_found(knowledge_base_id)

            logger.info(f"Deleting knowledge base: {knowledge_base_id} ({knowledge_base.knowledge_base_name})")

            # Delete knowledge base resources (vector database collection and directory)
            resources_result = await self.knowledge_base_controller.delete_knowledge_base_resources(
                knowledge_base=knowledge_base,
                nlp_controller=self.nlp_controller
            )

            # Log resource deletion results
            logger.info(f"Resource deletion results for knowledge base {knowledge_base_id}:")
            logger.info(f"  Vector DB deleted: {resources_result['vector_db_deleted']}")
            logger.info(f"  Directory deleted: {resources_result['directory_deleted']}")

            # Delete knowledge base from database (this also deletes related assets and chunks)
            # This is a data-focused operation that handles database cascade deletion
            knowledge_base_deleted, assets_deleted, chunks_deleted = await self.knowledge_base_model.delete_knowledge_base_cascade(
                knowledge_base_id=knowledge_base_id
            )

            logger.info(f"Database deletion results for knowledge base {knowledge_base_id}:")
            logger.info(f"  Knowledge base deleted: {knowledge_base_deleted}")
            logger.info(f"  Assets deleted: {assets_deleted}")
            logger.info(f"  Chunks deleted: {chunks_deleted}")

            if not knowledge_base_deleted:
                raise_http_exception(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    error_type=ErrorType.DATABASE_ERROR.value,
                    detail=f"Failed to delete knowledge base with ID '{knowledge_base_id}' from database"
                )

            return {
                "knowledge_base_id": knowledge_base_id,
                "knowledge_base_name": knowledge_base.knowledge_base_name,
                "resources_deleted": resources_result["overall_success"],
                "vector_db_deleted": resources_result["vector_db_deleted"],
                "directory_deleted": resources_result["directory_deleted"],
                "assets_deleted": assets_deleted,
                "chunks_deleted": chunks_deleted
            }
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error deleting knowledge base: {e}")
            raise_http_exception(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type=ErrorType.DATABASE_ERROR.value,
                detail=f"Failed to delete knowledge base: {str(e)}"
            )
