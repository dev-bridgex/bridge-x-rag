import asyncio
from app.models import KnowledgeBaseModel, ChunkModel, AssetModel
from app.models.db_schemas import KnowledgeBase, Asset
from app.controllers import NLPController
from fastapi import Request, status, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Dict, Any, Tuple
from app.logging import get_logger
from tqdm.auto import tqdm
from app.exception_handlers import raise_http_exception, raise_knowledge_base_not_found, raise_asset_not_found, raise_vector_db_error, raise_search_error
from app.models.enums.ErrorTypes import ErrorType

logger = get_logger(__name__)

class NLPService:
    """Service class for NLP operations"""

    def __init__(self, db: AsyncIOMotorDatabase, request: Request, knowledge_base_model: KnowledgeBaseModel = None,
                 asset_model: AssetModel = None, chunk_model: ChunkModel = None, nlp_controller: NLPController = None):
        self.db = db
        self.request = request
        self.knowledge_base_model = knowledge_base_model
        self.asset_model = asset_model
        self.chunk_model = chunk_model
        self.nlp_controller = nlp_controller or NLPController(
            vectordb_client=request.app.vectordb_client,
            generation_client=request.app.generation_client,
            embedding_client=request.app.embedding_client
        )

    async def _ensure_knowledge_base_model(self) -> None:
        """Ensure knowledge base model is initialized"""
        if not self.knowledge_base_model:
            self.knowledge_base_model = await KnowledgeBaseModel.create_instance(db_client=self.db)

    async def _ensure_asset_model(self) -> None:
        """Ensure asset model is initialized"""
        if not self.asset_model:
            self.asset_model = await AssetModel.create_instance(db_client=self.db)

    async def _ensure_chunk_model(self) -> None:
        """Ensure chunk model is initialized"""
        if not self.chunk_model:
            self.chunk_model = await ChunkModel.create_instance(db_client=self.db)

    async def validate_knowledge_base(self, knowledge_base_id: str) -> KnowledgeBase:
        """Validate knowledge base exists and return it

        Args:
            knowledge_base_id: The ID of the knowledge base to validate

        Returns:
            The knowledge base object if found

        Raises:
            HTTPException: If the knowledge base is not found
        """
        await self._ensure_knowledge_base_model()

        knowledge_base = await self.knowledge_base_model.get_knowledge_base_by_id(knowledge_base_id=knowledge_base_id)

        if knowledge_base is None:
            raise_knowledge_base_not_found(knowledge_base_id)

        return knowledge_base

    async def validate_asset(self, asset_id: str, knowledge_base_id: str = None) -> Asset:
        """Validate asset exists and optionally belongs to knowledge base

        Args:
            asset_id: The ID of the asset to validate
            knowledge_base_id: Optional ID of the knowledge base to check ownership

        Returns:
            The asset object if found

        Raises:
            HTTPException: If the asset is not found or doesn't belong to the knowledge base
        """
        await self._ensure_asset_model()

        asset = await self.asset_model.get_asset_by_id(asset_id=asset_id)

        if asset is None:
            raise_asset_not_found(asset_id)

        if knowledge_base_id and str(asset.asset_knowledge_base_id) != knowledge_base_id:
            raise_http_exception(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_type=ErrorType.INVALID_REQUEST.value,
                detail=f"Asset with ID '{asset_id}' does not belong to knowledge base with ID '{knowledge_base_id}'"
            )

        return asset

    async def validate_knowledge_base_and_asset(self, knowledge_base_id: str, asset_id: str) -> Tuple[KnowledgeBase, Asset]:
        """Validate both knowledge base and asset exist and are related

        This is a convenience method that combines validate_knowledge_base and validate_asset
        to ensure both resources exist and are related.

        Args:
            knowledge_base_id: The ID of the knowledge base
            asset_id: The ID of the asset

        Returns:
            A tuple containing the knowledge base and asset objects

        Raises:
            HTTPException: If the knowledge base or asset is not found, or if they are not related
        """
        knowledge_base = await self.validate_knowledge_base(knowledge_base_id=knowledge_base_id)
        asset = await self.validate_asset(asset_id=asset_id, knowledge_base_id=knowledge_base_id)
        return knowledge_base, asset


    async def index_asset(self, knowledge_base_id: str, asset_id: str, do_reset: bool = False, skip_duplicates: bool = True) -> Dict[str, Any]:
        """Index a specific asset into the vector database

        Args:
            knowledge_base_id: The ID of the knowledge base
            asset_id: The ID of the asset to index
            do_reset: Whether to reset existing chunks for this asset
            skip_duplicates: Whether to skip duplicate chunks

        Returns:
            A dictionary with information about the indexing operation containing:
                - asset_id: The ID of the indexed asset
                - knowledge_base_id: The ID of the knowledge base
                - indexed_chunks_count: Number of chunks indexed
                - message: A success message with details

        Raises:
            HTTPException: If the knowledge base or asset is not found, or if indexing fails
        """
        try:
            # Ensure models are initialized
            await self._ensure_chunk_model()

            # Validate knowledge base and asset
            knowledge_base, asset = await self.validate_knowledge_base_and_asset(knowledge_base_id=knowledge_base_id, asset_id=asset_id)

            # Get chunks for this asset
            chunks = await self.chunk_model.get_chunks_by_knowledge_base_and_asset_id(knowledge_base_id=knowledge_base.id, asset_id=asset.id)

            if not chunks or len(chunks) == 0:
                raise_http_exception(
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_type=ErrorType.ASSET_NOT_FOUND.value,
                    detail=f"No chunks found for asset '{asset_id}'. Please process the asset first."
                )

            # Create vector db collection for the knowledge base if it doesn't exist
            # Always use do_reset=False here to avoid resetting the entire collection
            # The asset-specific reset is handled in index_asset_into_vector_db
            success, error_msg, _ = await self.nlp_controller.create_vector_db_collection(
                knowledge_base=knowledge_base, do_reset=False
            )

            if not success:
                raise_vector_db_error(error_msg or "Failed to create vector database collection")

            # Setup for indexing - use actual chunk IDs if available, otherwise use sequential numbers
            chunks_ids = [chunk.id for chunk in chunks] if all(chunk.id for chunk in chunks) else list(range(len(chunks)))

            # Index the asset
            success, error_msg = await self.nlp_controller.index_asset_into_vector_db(
                knowledge_base=knowledge_base,
                asset=asset,
                chunks=chunks,
                chunks_ids=chunks_ids,
                do_reset=do_reset,
                skip_duplicates=skip_duplicates
            )

            if not success:
                raise_vector_db_error(error_msg or f"Failed to index asset '{asset_id}' into vector database")

            return {
                "asset_id": asset_id,
                "knowledge_base_id": knowledge_base_id,
                "indexed_chunks_count": len(chunks),
                "message": f"Successfully indexed {len(chunks)} chunks for asset '{asset_id}'"
            }
        except HTTPException:
            # Re-raise HTTP exceptions directly
            raise
        except Exception as e:
            # Log and convert other exceptions to HTTP exceptions
            error_msg = f"Error indexing asset '{asset_id}': {str(e)}"
            logger.error(error_msg)
            raise_http_exception(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type=ErrorType.VECTOR_DB_ERROR.value,
                detail=error_msg
            )


    async def index_knowledge_base(self, knowledge_base_id: str, do_reset: bool = False, skip_duplicates: bool = True, batch_size: int = 100) -> Dict[str, Any]:
        """Index a knowledge base's chunks into vector database

        Args:
            knowledge_base_id: The ID of the knowledge base to index
            do_reset: Whether to reset the existing vector database collection
            skip_duplicates: Whether to skip duplicate chunks
            batch_size: Number of chunks to process in each batch (default: 100)

        Returns:
            A dictionary with information about the indexing operation containing:
                - inserted_items_count: Number of chunks inserted into the vector database
                - message: A success message with details

        Raises:
            HTTPException: If the knowledge base is not found or indexing fails
        """
        # Initialize variables
        pbar_initialized = False
        pbar = None

        try:
            # Ensure models are initialized
            await self._ensure_chunk_model()

            # Validate knowledge base
            knowledge_base = await self.validate_knowledge_base(knowledge_base_id)

            # Create vector db collection for the knowledge base
            success, error_msg, collection_name = await self.nlp_controller.create_vector_db_collection(
                knowledge_base=knowledge_base, do_reset=do_reset
            )

            if not success:
                raise_vector_db_error(error_msg or "Failed to create vector database collection")

            # Setup batching
            total_chunks_count = await self.chunk_model.get_chunks_count_by_knowledge_base_id(knowledge_base_id=knowledge_base.id)

            if total_chunks_count == 0:
                logger.info(f"No chunks found for knowledge base '{knowledge_base_id}'. Nothing to index.")
                return {"inserted_items_count": 0, "message": "No chunks found to index"}

            # Initialize progress bar
            pbar = tqdm(total=total_chunks_count, desc="Vector Indexing", position=0)
            pbar_initialized = True

            # Process chunks in batches with a semaphore to limit concurrent operations
            page_no = 1
            inserted_items_count = 0
            # batch_size is now a parameter

            # Use a lock to track indexing progress
            indexing_lock = asyncio.Lock()

            while True:
                page_chunks = await self.chunk_model.get_chunks_by_knowledge_base_id(
                    knowledge_base_id=knowledge_base.id,
                    page=page_no,
                    page_size=batch_size
                )

                # Break if no more chunks
                if not page_chunks:
                    break

                page_no += 1
                len_page_chunks = len(page_chunks)

                # Use actual chunk IDs if available, otherwise use sequential numbers
                chunks_ids = [chunk.id for chunk in page_chunks] if all(chunk.id for chunk in page_chunks) else list(range(inserted_items_count, inserted_items_count + len_page_chunks))

                # Index the batch with retry logic
                max_retries = 3
                retry_count = 0
                is_inserted = False

                while not is_inserted and retry_count < max_retries:
                    try:
                        async with indexing_lock:
                            is_inserted = await self.nlp_controller.index_into_vector_db(
                                collection_name=collection_name,
                                chunks=page_chunks,
                                chunks_ids=chunks_ids,
                                skip_duplicates=skip_duplicates
                            )

                        if not is_inserted:
                            retry_count += 1
                            if retry_count >= max_retries:
                                pbar.close()
                                raise_vector_db_error(f"Failed to insert chunks (batch {page_no-1}) into vector database after {max_retries} attempts")
                            logger.warning(f"Retry {retry_count}/{max_retries} for batch {page_no-1}")
                            await asyncio.sleep(1)  # Wait before retrying
                    except Exception as batch_error:
                        retry_count += 1
                        if retry_count >= max_retries:
                            pbar.close()
                            raise_vector_db_error(f"Error inserting batch {page_no-1}: {str(batch_error)}")
                        logger.warning(f"Error in batch {page_no-1}, retry {retry_count}/{max_retries}: {str(batch_error)}")
                        await asyncio.sleep(1)  # Wait before retrying

                pbar.update(len_page_chunks)
                inserted_items_count += len_page_chunks

            pbar.close()
            return {
                "inserted_items_count": inserted_items_count,
                "message": f"Successfully indexed {inserted_items_count} chunks"
            }
        except HTTPException:
            # Close progress bar if it was initialized
            if pbar_initialized and pbar:
                pbar.close()
            # Re-raise HTTP exceptions directly
            raise
        except Exception as e:
            # Close progress bar if it was initialized
            if pbar_initialized and pbar:
                pbar.close()
            logger.error(f"Error during knowledge base indexing: {str(e)}")
            raise_http_exception(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type=ErrorType.VECTOR_DB_ERROR.value,
                detail=f"Error during knowledge base indexing: {str(e)}"
            )

    async def get_collection_info(self, knowledge_base_id: str) -> Dict[str, Any]:
        """Get information about a knowledge base's vector database collection

        Args:
            knowledge_base_id: The ID of the knowledge base

        Returns:
            A dictionary containing information about the vector database collection:
                - index_collection_info: Details about the collection including count, dimensions, etc.

        Raises:
            HTTPException: If the knowledge base is not found or the collection doesn't exist"""
        try:
            # Validate knowledge base
            knowledge_base = await self.validate_knowledge_base(knowledge_base_id)

            # Get collection info
            index_collection_info = await self.nlp_controller.get_vector_db_collection_info(knowledge_base=knowledge_base)

            if not index_collection_info:
                raise_vector_db_error(f"Vector database collection for knowledge base '{knowledge_base_id}' not found. Please index the knowledge base first.", status_code=status.HTTP_404_NOT_FOUND)

            return {"index_collection_info": index_collection_info}
        except HTTPException:
            # Re-raise HTTP exceptions directly
            raise
        except Exception as e:
            # Log and convert other exceptions to HTTP exceptions
            error_msg = f"Error getting collection info for knowledge base '{knowledge_base_id}': {str(e)}"
            logger.error(error_msg)
            raise_http_exception(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type=ErrorType.VECTOR_DB_ERROR.value,
                detail=error_msg
            )


    async def delete_asset_from_index(self, knowledge_base_id: str, asset_id: str) -> Dict[str, Any]:
        """Delete a specific asset from the vector database

        Args:
            knowledge_base_id: The ID of the knowledge base
            asset_id: The ID of the asset to delete from the vector database

        Returns:
            A dictionary with information about the deletion operation

        Raises:
            HTTPException: If the knowledge base or asset is not found, or if deletion fails
        """
        try:
            # Validate knowledge base and asset
            knowledge_base, asset = await self.validate_knowledge_base_and_asset(knowledge_base_id=knowledge_base_id, asset_id=asset_id)

            # Check if collection exists
            collection_exists = await self.nlp_controller.is_collection_exists(knowledge_base=knowledge_base)

            if not collection_exists:
                # If collection doesn't exist, consider it a success (nothing to delete)
                return {
                    "asset_id": asset_id,
                    "knowledge_base_id": knowledge_base_id,
                    "deleted_from_vector_db": False,
                    "message": "Vector database collection does not exist"
                }

            # Delete asset from vector database
            deleted = await self.nlp_controller.delete_asset_from_vector_db(knowledge_base=knowledge_base, asset=asset)

            if not deleted:
                raise_vector_db_error(f"Failed to delete asset '{asset_id}' from vector database")

            return {
                "asset_id": asset_id,
                "knowledge_base_id": knowledge_base_id,
                "deleted_from_vector_db": True
            }
        except HTTPException:
            # Re-raise HTTP exceptions directly
            raise
        except Exception as e:
            # Log and convert other exceptions to HTTP exceptions
            error_msg = f"Error deleting asset '{asset_id}' from index: {str(e)}"
            logger.error(error_msg)
            raise_http_exception(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type=ErrorType.VECTOR_DB_ERROR.value,
                detail=error_msg
            )


    async def search_collection(self, knowledge_base_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search a knowledge base's vector database collection

        Args:
            knowledge_base_id: The ID of the knowledge base to search
            query: The search query text
            limit: Maximum number of results to return (default: 5)

        Returns:
            A list of search results, each containing the chunk text, metadata, and similarity score

        Raises:
            HTTPException: If the knowledge base is not found, the collection doesn't exist, or search fails"""
        try:
            # Validate knowledge base
            knowledge_base = await self.validate_knowledge_base(knowledge_base_id)

            # Check if collection exists
            collection_exists = await self.nlp_controller.is_collection_exists(knowledge_base=knowledge_base)

            if not collection_exists:
                raise_vector_db_error(f"Vector database collection for knowledge base '{knowledge_base_id}' not found. Please index the knowledge base first.", status_code=status.HTTP_404_NOT_FOUND)

            # Perform search
            results = await self.nlp_controller.search_vector_db(
                knowledge_base=knowledge_base,
                query=query,
                limit=limit
            )

            if not results:
                raise_search_error("Search failed or returned no results")

            return results
        except HTTPException:
            # Re-raise HTTP exceptions directly
            raise
        except Exception as e:
            # Log and convert other exceptions to HTTP exceptions
            error_msg = f"Error searching collection for knowledge base '{knowledge_base_id}': {str(e)}"
            logger.error(error_msg)
            raise_http_exception(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type=ErrorType.VECTOR_DB_SEARCH_ERROR.value,
                detail=error_msg
            )


    async def answer_rag_query(self, knowledge_base_id: str, query: str, limit: int = 5) -> Tuple[str, str, List[Dict[str, Any]]]:
        """
        Generate an answer to a question using RAG (Retrieval-Augmented Generation)

        Args:
            knowledge_base_id: The ID of the knowledge base to search in
            query: The user's question
            limit: Maximum number of chunks to retrieve

        Returns:
            Tuple containing:
                - answer: The generated answer text
                - full_prompt: The full prompt sent to the LLM
                - chat_history: The chat history including system and user messages

        Raises:
            HTTPException: If the knowledge base is not found, the collection doesn't exist, or search fails
        """
        try:
            # Validate knowledge base
            knowledge_base = await self.validate_knowledge_base(knowledge_base_id)

            # Check if collection exists
            collection_exists = await self.nlp_controller.is_collection_exists(knowledge_base=knowledge_base)

            if not collection_exists:
                raise_vector_db_error(f"Vector database collection for knowledge base '{knowledge_base_id}' not found. Please index the knowledge base first.", status_code=status.HTTP_404_NOT_FOUND)

            # Generate answer using RAG
            answer, full_prompt, chat_history = await self.nlp_controller.answer_rag_question(
                knowledge_base=knowledge_base,
                query=query,
                limit=limit
            )

            if not answer:
                raise_http_exception(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_type=ErrorType.VECTOR_DB_SEARCH_ERROR.value,
                    detail="Failed to generate an answer from the retrieved documents"
                )

            return answer, full_prompt, chat_history

        except HTTPException:
            # Re-raise HTTP exceptions directly
            raise
        except Exception as e:
            # Log and convert other exceptions to HTTP exceptions
            error_msg = f"Error generating RAG answer for knowledge base '{knowledge_base_id}': {str(e)}"
            logger.error(error_msg)
            raise_http_exception(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type=ErrorType.VECTOR_DB_SEARCH_ERROR.value,
                detail=error_msg
            )

    async def chat_with_knowledge_base(self, knowledge_base_id: str, query: str, history: List[Dict[str, str]] = None, use_rag: bool = True, limit: int = 5) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Chat with a knowledge base using RAG or direct LLM generation

        Args:
            knowledge_base_id: The ID of the knowledge base to search in
            query: The user's question
            history: Previous chat history (list of role/content dictionaries)
            use_rag: Whether to use RAG (retrieval) or just direct LLM generation
            limit: Maximum number of chunks to retrieve when using RAG

        Returns:
            Tuple containing:
                - response: The generated response text
                - sources: List of sources used to generate the response (empty if not using RAG)

        Raises:
            HTTPException: If the knowledge base is not found, the collection doesn't exist, or chat fails
        """
        try:
            # Validate knowledge base
            knowledge_base = await self.validate_knowledge_base(knowledge_base_id)

            # If using RAG, check if collection exists
            if use_rag:
                collection_exists = await self.nlp_controller.is_collection_exists(knowledge_base=knowledge_base)
                if not collection_exists:
                    raise_vector_db_error(
                        f"Vector database collection for knowledge base '{knowledge_base_id}' not found. Please index the knowledge base first.",
                        status_code=status.HTTP_404_NOT_FOUND
                    )

            # Generate chat response
            response, sources = await self.nlp_controller.chat_with_knowledge_base(
                knowledge_base=knowledge_base,
                query=query,
                history=history,
                use_rag=use_rag,
                limit=limit
            )

            if not response:
                raise_http_exception(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_type=ErrorType.VECTOR_DB_SEARCH_ERROR.value,
                    detail="Failed to generate a chat response"
                )

            return response, sources

        except HTTPException:
            # Re-raise HTTP exceptions directly
            raise
        except Exception as e:
            # Log and convert other exceptions to HTTP exceptions
            error_msg = f"Error generating chat response for knowledge base '{knowledge_base_id}': {str(e)}"
            logger.error(error_msg)
            raise_http_exception(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type=ErrorType.VECTOR_DB_SEARCH_ERROR.value,
                detail=error_msg
            )