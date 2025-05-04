from app.models import KnowledgeBaseModel, AssetModel, ChunkModel
from app.models.db_schemas import KnowledgeBase, Asset, DataChunk
from app.controllers import KnowledgeBaseController, AssetController, ProcessingController, NLPController
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Tuple, Dict, Any, Optional
import os
from app.logging import get_logger
from fastapi import status, HTTPException
from app.exception_handlers import raise_http_exception, raise_knowledge_base_not_found, raise_asset_not_found, raise_file_type_not_supported, raise_file_size_exceeded, raise_processing_failed
from app.models.enums.ErrorTypes import ErrorType

logger = get_logger(__name__)

# Note: Custom exceptions have been removed as they are now handled by the exception handler

class AssetService:
    """Service class for complex asset operations that span multiple controllers and models"""

    def __init__(self, db: AsyncIOMotorDatabase, knowledge_base_model: KnowledgeBaseModel = None,
                 asset_model: AssetModel = None, chunk_model: ChunkModel = None,
                 knowledge_base_controller: KnowledgeBaseController = None,
                 asset_controller: AssetController = None,
                 processing_controller: ProcessingController = None,
                 nlp_controller: NLPController = None):
        self.db = db
        self.knowledge_base_model = knowledge_base_model
        self.asset_model = asset_model
        self.chunk_model = chunk_model

        self.knowledge_base_controller = knowledge_base_controller
        self.asset_controller = asset_controller
        self.processing_controller = processing_controller
        self.nlp_controller = nlp_controller

    async def _ensure_knowledge_base_model(self) -> None:
        """Ensure knowledge base model is initialized"""
        if not self.knowledge_base_model:
            self.knowledge_base_model = await KnowledgeBaseModel.create_instance(db_client=self.db)

    async def _ensure_asset_model(self) -> None:
        """Ensure asset model is initialized"""
        if not self.asset_model:
            self.asset_model = await AssetModel.create_instance(db_client=self.db)

    def _validate_file(self, file):
        """Validate the uploaded file

        Args:
            file: The uploaded file to validate

        Raises:
            HTTPException: With appropriate status code and signal for validation errors
        """
        try:
            # Use the controller to validate the file
            validation_result = self.asset_controller.validate_uploaded_file(file=file)
            if not validation_result:
                raise_http_exception(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_type=ErrorType.INVALID_REQUEST.value,
                    detail=f"File validation failed for {file.filename}"
                )
        except ValueError as validation_error:
            error_message = str(validation_error)
            logger.warning(f"File validation error: {error_message}")

            # Convert to specific exception types based on the error message
            if "File type" in error_message and "not supported" in error_message:
                file_type = file.content_type if hasattr(file, 'content_type') else 'unknown'
                raise_file_type_not_supported(file_type)
            elif "File size" in error_message and "exceeds maximum allowed size" in error_message:
                file_size = file.size if hasattr(file, 'size') else 0
                max_size = 10 * 1024 * 1024  # Default to 10MB if not specified in the error message
                raise_file_size_exceeded(file_size, max_size)
            else:
                # Generic validation error
                raise_http_exception(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_type=ErrorType.INVALID_REQUEST.value,
                    detail=error_message
                )

    async def _ensure_chunk_model(self) -> None:
        """Ensure chunk model is initialized"""
        if not self.chunk_model:
            self.chunk_model = await ChunkModel.create_instance(db_client=self.db)

    async def validate_knowledge_base(self, knowledge_base_id) -> KnowledgeBase:
        """Validate knowledge base exists and return it

        Args:
            knowledge_base_id: The ID of the knowledge base

        Returns:
            The knowledge base

        Raises:
            HTTPException: If the knowledge base is not found
        """
        await self._ensure_knowledge_base_model()

        knowledge_base = await self.knowledge_base_model.get_knowledge_base_by_id(knowledge_base_id=knowledge_base_id)

        if knowledge_base is None:
            raise_knowledge_base_not_found(knowledge_base_id)

        return knowledge_base

    async def validate_asset(self, asset_id, knowledge_base_id = None) -> Asset:
        """Validate asset exists and optionally belongs to knowledge base

        Args:
            asset_id: The ID of the asset
            knowledge_base_id: Optional ID of the knowledge base to check ownership

        Returns:
            The asset

        Raises:
            HTTPException: If the asset is not found or doesn't belong to the knowledge base
        """
        await self._ensure_asset_model()

        asset = await self.asset_model.get_asset_by_id(asset_id=asset_id)

        if asset is None:
            raise_asset_not_found(asset_id)

        if knowledge_base_id and str(asset.asset_knowledge_base_id) != str(knowledge_base_id):
            raise_http_exception(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_type=ErrorType.INVALID_REQUEST.value,
                detail=f"Asset with ID '{asset_id}' does not belong to knowledge base with ID '{knowledge_base_id}'"
            )

        return asset

    async def validate_knowledge_base_and_asset(self, knowledge_base_id, asset_id) -> Tuple[KnowledgeBase, Asset]:
        """Validate both knowledge base and asset exist and are related

        This is a convenience method that combines validate_knowledge_base and validate_asset
        to ensure both resources exist and are related.

        Args:
            knowledge_base_id: The ID of the knowledge base
            asset_id: The ID of the asset

        Returns:
            A tuple containing the knowledge base and asset objects

        Raises:
            KnowledgeBaseNotFoundError: If the knowledge base does not exist
            AssetNotFoundError: If the asset does not exist
            AssetServiceError: If the asset does not belong to the knowledge base
        """
        knowledge_base = await self.validate_knowledge_base(knowledge_base_id=knowledge_base_id)
        asset = await self.validate_asset(asset_id=asset_id, knowledge_base_id=knowledge_base_id)
        return knowledge_base, asset

    async def get_knowledge_base_assets(self, knowledge_base_id, asset_type: str = None,
                             page: int = 1, page_size: int = 10,
                             sort: List[tuple] = None) -> Tuple[List[Asset], int, int]:
        """Get all assets for a knowledge base, optionally filtered by asset type, with pagination

        Args:
            knowledge_base_id: The ID of the knowledge base
            asset_type: Optional filter for asset type
            page: Page number (1-based)
            page_size: Number of items per page
            sort: List of (field, direction) tuples for sorting

        Returns:
            Tuple of (assets, total_pages, total_items)
        """
        await self._ensure_asset_model()

        return await self.asset_model.get_all_knowledge_base_assets(
            knowledge_base_id=knowledge_base_id,
            asset_type=asset_type,
            page=page,
            page_size=page_size,
            sort=sort
        )

    async def upload_asset(self, knowledge_base_id, file, chunk_size: int) -> Tuple[Asset, KnowledgeBase]:
        """Upload a file as an asset to a knowledge base

        This method handles the complete asset upload process:
        1. Validates the file
        2. Validates the knowledge base
        3. Generates a file hash for deduplication
        4. Checks if the file already exists in the knowledge base
        5. If duplicate found, returns the existing asset
        6. Otherwise, creates a unique file path, saves the file, and creates a new asset record

        Args:
            knowledge_base_id: The ID of the knowledge base to upload the asset to
            file: The uploaded file object
            chunk_size: The chunk size to use when saving the file

        Returns:
            A tuple containing the created or existing asset record and the knowledge base

        Raises:
            KnowledgeBaseNotFoundError: If the knowledge base does not exist
            AssetUploadError: If the file validation fails or cannot be saved
        """
        try:
            # Validate the file
            self._validate_file(file)

            # Validate the knowledge base
            knowledge_base = await self.validate_knowledge_base(knowledge_base_id=knowledge_base_id)

            # Generate file hash for deduplication
            file_hash = await self.asset_controller.generate_file_hash(file)

            if file_hash:
                # Check if file with same hash already exists in this knowledge base
                await self._ensure_asset_model()
                existing_asset = await self.asset_model.find_asset_by_hash(
                    file_hash=file_hash,
                    knowledge_base_id=knowledge_base.id
                )

                if existing_asset:
                    logger.info(f"Duplicate file detected. Using existing asset: {existing_asset.asset_name} (ID: {existing_asset.id})")
                    return existing_asset, knowledge_base

            # Get knowledge base directory
            knowledge_base_dir_path = self.knowledge_base_controller.get_knowledge_base_path(knowledge_base_id=knowledge_base_id)

            # Generate unique file path
            file_path, file_name = self.asset_controller.generate_unique_filepath(
                knowledge_base_path=knowledge_base_dir_path,
                original_file_name=file.filename
            )

            # Save the file
            save_success = await self.asset_controller.save_uploaded_file(
                file=file,
                file_path=file_path,
                chunk_size=chunk_size
            )

            if not save_success:
                raise_http_exception(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    error_type=ErrorType.INVALID_REQUEST.value,
                    detail=f"Error uploading file {file.filename}"
                )

            # Create asset record
            await self._ensure_asset_model()

            asset_resource = Asset(
                asset_knowledge_base_id=knowledge_base.id,
                asset_path=file_path,
                asset_type=file.content_type,
                asset_name=file_name,
                asset_size=file.size,
                file_hash=file_hash  # Store the file hash for future deduplication
            )

            asset = await self.asset_model.create(asset_resource)

            # Return both the asset and knowledge base to avoid having to validate the knowledge base again
            return asset, knowledge_base

        except HTTPException:
            # Re-raise HTTP exceptions directly
            raise
        except Exception as e:
            # Log and wrap unexpected exceptions
            logger.error(f"Unexpected error during asset upload: {e}")
            raise_http_exception(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type=ErrorType.INVALID_REQUEST.value,
                detail=f"Failed to upload asset: {str(e)}"
            )

    async def delete_asset_with_resources(self, knowledge_base_id, asset_id) -> Dict[str, Any]:
        """Delete an asset and all its resources

        This method handles the complete asset deletion process:
        1. Validates the knowledge base and asset
        2. Deletes the asset file from disk
        3. Deletes the asset from vector database if it was indexed
        4. Deletes the asset and related chunks from the database

        Args:
            knowledge_base_id: The ID of the knowledge base the asset belongs to
            asset_id: The ID of the asset to delete

        Returns:
            A dictionary with information about the deleted asset

        Raises:
            KnowledgeBaseNotFoundError: If the knowledge base does not exist
            AssetNotFoundError: If the asset does not exist
            AssetDeleteError: If the asset cannot be deleted
        """
        try:
            # Validate knowledge base and asset
            knowledge_base, asset = await self.validate_knowledge_base_and_asset(knowledge_base_id=knowledge_base_id, asset_id=asset_id)

            # Delete the asset file
            file_deleted = self.asset_controller.delete_asset_file(file_path=asset.asset_path)

            # Delete from vector database if NLP controller is available
            vector_db_deleted = False
            if self.nlp_controller:
                # Try to delete from vector database - don't raise exception if it fails
                try:
                    vector_db_deleted = await self.nlp_controller.delete_asset_from_vector_db(
                        knowledge_base=knowledge_base, asset=asset
                    )
                except Exception as e:
                    logger.error(f"Error deleting asset from vector database: {e}")
                    # Continue with deletion even if vector DB deletion fails

            # Delete the asset and related chunks from the database
            await self._ensure_asset_model()
            asset_deleted, chunks_deleted = await self.asset_model.delete_asset_cascade(asset_id=asset_id)

            if not asset_deleted:
                raise_http_exception(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    error_type=ErrorType.INVALID_REQUEST.value,
                    detail=f"Failed to delete asset {asset_id} from database"
                )

            result = {
                "asset_id": asset_id,
                "asset_name": asset.asset_name,
                "knowledge_base_id": knowledge_base_id,
                "knowledge_base_name": knowledge_base.knowledge_base_name,
                "file_deleted": file_deleted,
                "chunks_deleted": chunks_deleted,
                "vector_db_deleted": vector_db_deleted
            }

            return result

        except HTTPException:
            # Re-raise HTTP exceptions directly
            raise
        except Exception as e:
            # Log and wrap unexpected exceptions
            logger.error(f"Unexpected error during asset deletion: {e}")
            raise_http_exception(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type=ErrorType.INVALID_REQUEST.value,
                detail=f"Failed to delete asset: {str(e)}"
            )

    async def _reset_vector_db_for_asset(self, knowledge_base: KnowledgeBase, asset: Asset) -> bool:
        """Reset vector database for a specific asset

        Args:
            knowledge_base: The knowledge base object
            asset: The asset object

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.nlp_controller:
            logger.warning("NLP controller not available for vector DB operations")
            return False

        try:
            # Delete from vector DB
            success = await self.nlp_controller.delete_asset_from_vector_db(knowledge_base, asset)
            if success:
                logger.info(f"Deleted asset {asset.id} from vector database")
            return success
        except Exception as e:
            logger.warning(f"Failed to delete asset {asset.id} from vector database: {e}")
            return False

    async def _reset_vector_db_for_knowledge_base(self, knowledge_base: KnowledgeBase) -> bool:
        """Reset vector database for an entire knowledge base

        Args:
            knowledge_base: The knowledge base object

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.nlp_controller:
            logger.warning("NLP controller not available for vector DB operations")
            return False

        try:
            # Create vector db collection for the knowledge base with reset=True
            await self.nlp_controller.create_vector_db_collection(knowledge_base=knowledge_base, do_reset=True)
            logger.info(f"Reset vector database collection for knowledge base {knowledge_base.id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to reset vector database for knowledge base {knowledge_base.id}: {e}")
            return False

    async def _check_asset_has_chunks(self, knowledge_base_id, asset_id) -> bool:
        """Check if an asset already has chunks

        Args:
            knowledge_base_id: The knowledge base ID
            asset_id: The asset ID

        Returns:
            bool: True if the asset has chunks, False otherwise
        """
        await self._ensure_chunk_model()

        # The model layer will handle ID conversion
        existing_chunks = await self.chunk_model.get_chunks_by_knowledge_base_and_asset_id(
            knowledge_base_id=knowledge_base_id,
            asset_id=asset_id
        )
        return bool(existing_chunks and len(existing_chunks) > 0)

    async def process_asset(self,
                           knowledge_base: KnowledgeBase,
                           asset: Asset,
                           chunk_size: int,
                           overlap_size: int = 50) -> int:
        """Process a single asset into chunks for RAG operations.

        This is an internal method used by process_single_asset and process_assets.
        It handles the actual processing of a file into chunks:
        1. Locates the file in the knowledge base directory
        2. Reads the file content
        3. Processes the content into chunks with the specified parameters
        4. Stores the chunks in the database

        Args:
            knowledge_base: The knowledge base object the asset belongs to
            asset: The asset object to process
            chunk_size: Size of text chunks in characters
            overlap_size: Overlap between chunks in characters

        Returns:
            int: Number of chunks inserted

        Raises:
            ProcessingError: If any step of the processing fails
        """
        # Get knowledge base path
        knowledge_base_path = self.knowledge_base_controller.find_knowledge_base_path(knowledge_base_id=str(knowledge_base.id))
        if knowledge_base_path is None:
            error_msg = f"Knowledge base path not found for knowledge base ID: {knowledge_base.id}"
            logger.error(error_msg)
            raise_processing_failed(error_msg)

        # Check file exists
        # file_path = self.processing_controller.get_file_path(
        #     file_name=asset.asset_name,
        #     knowledge_base_path=knowledge_base_path
        # )

        if not os.path.exists(asset.asset_path):
            error_msg = f"File not found: {asset.asset_name} in knowledge base: {knowledge_base.id}"
            logger.error(error_msg)
            raise_processing_failed(error_msg)

        # Get file content and process it into chunks
        file_chunks = await self.processing_controller.get_file_content(
            file_name=asset.asset_name,
            file_path=asset.asset_path,
            chunk_size=chunk_size
        )
        # Log the number of chunks
        logger.info(f"Processing file: {asset.asset_name} with {len(file_chunks)} chunks")

        if file_chunks is None:
            error_msg = f"Failed to get content for file: {asset.asset_name}"
            logger.error(error_msg)
            raise_processing_failed(error_msg)

        # Enhance chunks with additional metadata if needed
        file_chunks = self.processing_controller.enhance_file_chunks(
            file_chunks=file_chunks,
            file_name=asset.asset_name
        )

        if file_chunks is None or len(file_chunks) == 0:
            error_msg = f"Failed to process file content: {asset.asset_name}"
            logger.error(error_msg)
            raise_processing_failed(error_msg)

        # Create chunk records with enhanced metadata
        await self._ensure_chunk_model()

        file_chunks_records = []

        for idx, chunk in enumerate(file_chunks):
            # Use the metadata from the chunk (already cleaned by ProcessingController.enhance_file_chunks)
            metadata = chunk.metadata.copy()

            # Ensure document_name is in metadata if somehow missing
            if "document_name" not in metadata:
                metadata["document_name"] = asset.asset_name

            # Create the DataChunk record with the essential fields and metadata
            chunk_record = DataChunk(
                chunk_text=chunk.page_content,
                chunk_order=idx+1,
                chunk_knowledge_base_id=knowledge_base.id,
                chunk_asset_id=asset.id,
                metadata=metadata
            )

            file_chunks_records.append(chunk_record)

        # Insert chunks
        chunks_inserted = await self.chunk_model.insert_many_chunks(chunks=file_chunks_records)
        return chunks_inserted

    async def process_single_asset(self,
                                knowledge_base_id,
                                asset_id,
                                chunk_size: int = 600,
                                overlap_size: int = 100,
                                do_reset: bool = False,
                                reset_vector_db: Optional[bool] = None,
                                skip_duplicates: bool = True) -> Dict[str, Any]:
        """Process a single asset by ID

        This method handles the complete processing of a single asset:
        1. Validates the knowledge base and asset
        2. Optionally resets existing chunks and vector DB entries
        3. Processes the asset into chunks
        4. Stores the chunks in the database

        Args:
            knowledge_base_id: The ID of the knowledge base the asset belongs to
            asset_id: The ID of the asset to process
            chunk_size: Size of text chunks in characters
            overlap_size: Overlap between chunks in characters
            do_reset: Whether to reset existing chunks
            reset_vector_db: Whether to reset vector DB (defaults to do_reset value)
            skip_duplicates: Whether to skip assets that already have chunks

        Returns:
            A dictionary with information about the processed asset

        Raises:
            HTTPException: With appropriate status code and error type if processing fails
        """
        try:
            # Validate knowledge base and asset
            knowledge_base = await self.validate_knowledge_base(knowledge_base_id)
            asset = await self.validate_asset(asset_id=asset_id, knowledge_base_id=knowledge_base_id)

            # Check knowledge base path exists
            knowledge_base_path = self.knowledge_base_controller.find_knowledge_base_path(knowledge_base_id=knowledge_base_id)
            if knowledge_base_path is None:
                raise_processing_failed(f"Knowledge base directory for ID '{knowledge_base_id}' not found in the file storage")

            # If skip_duplicates is True and do_reset is False, check if asset already has chunks
            if skip_duplicates and not do_reset:
                has_chunks = await self._check_asset_has_chunks(knowledge_base.id, asset.id)
                if has_chunks:
                    logger.info(f"Skipping asset {asset_id} as it already has chunks")
                    return {
                        "processed_files": 0,
                        "inserted_chunks": 0
                    }

            # Determine if vector DB should be reset
            should_reset_vector_db = reset_vector_db if reset_vector_db is not None else do_reset

            # Reset chunks if requested
            if do_reset:
                # Delete chunks from MongoDB
                await self._ensure_chunk_model()
                await self.chunk_model.delete_chunks_by_knowledge_base_and_asset_id(
                    knowledge_base_id=knowledge_base.id,
                    asset_id=asset.id
                )

                # Also reset vector DB if needed
                if should_reset_vector_db:
                    await self._reset_vector_db_for_asset(knowledge_base, asset)

            # Process the asset
            try:
                chunks_inserted = await self.process_asset(
                    knowledge_base=knowledge_base,
                    asset=asset,
                    chunk_size=chunk_size,
                    overlap_size=overlap_size
                )

                return {
                    "processed_files": 1,
                    "inserted_chunks": chunks_inserted
                }
            except Exception as e:
                # Log and re-raise with appropriate error
                logger.error(f"Error processing asset {asset.asset_name}: {e}")
                raise_processing_failed(f"Failed to process asset: {asset.asset_name}. Error: {str(e)}")

        except HTTPException:
            # Re-raise HTTP exceptions directly
            raise
        except Exception as e:
            # Log and wrap unexpected exceptions
            logger.error(f"Unexpected error during asset processing: {e}")
            raise_http_exception(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type=ErrorType.PROCESSING_FAILED.value,
                detail=f"Failed to process asset: {str(e)}"
            )


    async def process_assets(self,
                            knowledge_base_id,
                            chunk_size: int = 500,
                            overlap_size: int = 50,
                            do_reset: bool = False,
                            reset_vector_db: Optional[bool] = None,
                            skip_duplicates: bool = True,
                            batch_size: int = 50) -> Dict[str, Any]:
        """Process assets in a knowledge base

        This method handles the processing of multiple assets in a knowledge base:
        1. processes all assets in the knowledge base in batches
        2. Optionally resets existing chunks and vector DB entries
        3. Processes each asset into chunks
        4. Stores the chunks in the database

        Args:
            knowledge_base_id: The ID of the knowledge base
            chunk_size: Size of text chunks in characters
            overlap_size: Overlap between chunks in characters
            do_reset: Whether to reset existing chunks
            reset_vector_db: Whether to reset vector DB (defaults to do_reset value)
            skip_duplicates: Whether to skip assets that already have chunks
            batch_size: Number of assets to process in each batch

        Returns:
            A dictionary with information about the processed assets

        Raises:
            HTTPException: With appropriate status code and error type if processing fails
        """

        try:
            # Validate knowledge base
            knowledge_base = await self.validate_knowledge_base(knowledge_base_id)

            # Check knowledge base path exists
            knowledge_base_path = self.knowledge_base_controller.find_knowledge_base_path(knowledge_base_id=knowledge_base_id)
            if knowledge_base_path is None:
                raise_processing_failed(f"Knowledge base directory for ID '{knowledge_base_id}' not found in the file storage")

            # Initialize models
            await self._ensure_asset_model()
            await self._ensure_chunk_model()

            # Determine if vector DB should be reset
            should_reset_vector_db = reset_vector_db if reset_vector_db is not None else do_reset

            # Reset all chunks if requested
            if do_reset:
                # Delete chunks from MongoDB
                await self.chunk_model.delete_chunks_by_knowledge_base_id(knowledge_base_id=knowledge_base.id)

                # Also reset vector DB if needed
                if should_reset_vector_db:
                    await self._reset_vector_db_for_knowledge_base(knowledge_base)

            # Get total count of assets for pagination
            # Use a more efficient approach by getting just the count
            total_assets = await self.asset_model.count_documents(
                filter_dict={"asset_knowledge_base_id": knowledge_base.id}
            )

            if total_assets == 0:
                raise_processing_failed("No assets found to process")

            # Process assets in batches
            total_chunks = 0
            processed_assets = 0
            total_pages = (total_assets + batch_size - 1) // batch_size

            logger.info(f"Processing {total_assets} assets in {total_pages} batches of {batch_size}")

            for page in range(1, total_pages + 1):
                logger.info(f"Processing batch {page}/{total_pages}")

                # Get assets for this batch
                assets, _, _ = await self.asset_model.get_all_knowledge_base_assets(
                    knowledge_base_id=knowledge_base.id,
                    page=page,
                    page_size=batch_size
                )

                # Process each asset in the batch
                for asset in assets:
                    # Skip if already has chunks and skip_duplicates is True
                    if skip_duplicates and not do_reset:
                        has_chunks = await self._check_asset_has_chunks(knowledge_base.id, asset.id)
                        if has_chunks:
                            logger.info(f"Skipping asset {asset.id} as it already has chunks")
                            continue

                    try:
                        # Process the asset
                        chunks_inserted = await self.process_asset(
                            knowledge_base=knowledge_base,
                            asset=asset,
                            chunk_size=chunk_size,
                            overlap_size=overlap_size
                        )

                        total_chunks += chunks_inserted
                        processed_assets += 1
                        logger.info(f"Processed asset {asset.id} ({asset.asset_name}): {chunks_inserted} chunks")

                    except Exception as e:
                        # Log error but continue with other assets
                        logger.error(f"Error processing asset {asset.id} ({asset.asset_name}): {str(e)}")
                        # Add more detailed logging for debugging
                        logger.debug(f"Asset processing error details: {e}", exc_info=True)

            return {
                "processed_files": processed_assets,
                "inserted_chunks": total_chunks,
                "total_assets": total_assets
            }

        except HTTPException:
            # Re-raise HTTP exceptions directly
            raise
        except Exception as e:
            # Log and wrap unexpected exceptions
            logger.error(f"Unexpected error during batch asset processing: {e}")
            raise_http_exception(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type=ErrorType.PROCESSING_FAILED.value,
                detail=f"Failed to process assets: {str(e)}"
            )
