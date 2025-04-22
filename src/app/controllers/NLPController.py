from .BaseController import BaseController
from app.stores.vectordb import VectorDBProviderInterface
from app.stores.llm import LLMProviderInterface
from app.stores.llm.LLMEnums import DocumentTypeEnum
from app.models.db_schemas import KnowledgeBase, DataChunk, Asset
from typing import List, Optional
import json
from app.logging import get_logger

logger = get_logger(__name__)

class NLPController(BaseController):
    def __init__(self, vectordb_client: VectorDBProviderInterface,
                 generation_client: LLMProviderInterface,
                 embedding_client: LLMProviderInterface) -> None:
        super().__init__()

        self.vectordb_client: VectorDBProviderInterface = vectordb_client
        self.generation_client: LLMProviderInterface = generation_client
        self.embedding_client: LLMProviderInterface = embedding_client

    def create_collection_name(self, knowledge_base_id: str):
        """Create a collection name using knowledge base ID"""
        return f"kb_collection_{knowledge_base_id}".strip()

    async def list_vector_db_collections(self) -> List:
        return await self.vectordb_client.list_all_collections()

    async def is_collection_exists(self, knowledge_base: KnowledgeBase) -> bool:
        """Check if a vector database collection exists for a knowledge base"""
        collection_name = self.create_collection_name(knowledge_base_id=str(knowledge_base.id))
        return await self.vectordb_client.is_collection_exists(collection_name=collection_name)

    async def get_vector_db_collection_info(self, knowledge_base: KnowledgeBase):
        """Get information about a knowledge base's vector database collection"""
        collection_name = self.create_collection_name(knowledge_base_id=str(knowledge_base.id))
        collection_info = await self.vectordb_client.get_collection_info(collection_name=collection_name)

        if not collection_info:
            return None

        return json.loads(
            json.dumps(collection_info, default = lambda x: x.__dict__)
        )

    async def create_vector_db_collection(self, knowledge_base: KnowledgeBase, do_reset: bool = False) -> tuple[bool, str, str | None]:
        """Create a vector database collection for a knowledge base

        Args:
            knowledge_base: The knowledge base object
            do_reset: Whether to reset the collection if it already exists

        Returns:
            tuple: (success, error_message, collection_name)
                - success: True if operation was successful, False otherwise
                - error_message: Empty string if successful, error details if failed
                - collection_name: Name of the collection if successful, None otherwise
        """
        collection_name = self.create_collection_name(knowledge_base_id=str(knowledge_base.id))

        try:
            is_created = await self.vectordb_client.create_collection(
                collection_name = collection_name,
                embedding_size = self.embedding_client.embedding_size,
                do_reset = do_reset
            )

            if not is_created:
                return False, f"Failed to create vector database collection '{collection_name}'.", None

            return True, "", collection_name
        except Exception as e:
            logger.error(f"Error creating vector database collection: {str(e)}")
            return False, f"Error creating vector database collection: {str(e)}", None

    async def delete_vector_db_collection(self, knowledge_base: KnowledgeBase) -> bool:
        """Delete a vector database collection for a knowledge base"""
        collection_name = self.create_collection_name(knowledge_base_id=str(knowledge_base.id))
        return await self.vectordb_client.delete_collection(collection_name=collection_name)

    async def delete_asset_from_vector_db(self, knowledge_base: KnowledgeBase, asset: Asset) -> bool:
        """Delete a specific asset's data from the vector database

        Args:
            knowledge_base: The knowledge base object
            asset: The asset object to delete from the vector database

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        # Check if collection exists
        collection_name = self.create_collection_name(knowledge_base_id=str(knowledge_base.id))
        collection_exists = await self.vectordb_client.is_collection_exists(collection_name=collection_name)

        if not collection_exists:
            return False

        # Delete records with matching asset_id in metadata
        asset_id_str = str(asset.id)
        return await self.vectordb_client.delete_by_metadata(collection_name=collection_name, filter_dict={"asset_id": asset_id_str})

    async def index_into_vector_db(
        self,
        collection_name: str,
        chunks: List[DataChunk],
        chunks_ids: List[int],
        skip_duplicates: bool = False
        ) -> bool:
        """Index chunks into the vector database

        Args:
            collection_name: Name of the vector database collection
            chunks: List of data chunks to index
            chunks_ids: List of chunk IDs
            skip_duplicates: Whether to skip chunks that already exist in the vector database

        Returns:
            bool: True if indexing was successful, False otherwise
        """
        try:
            # Process data chunks and vectorize (create embeddings)
            texts = []
            metadatas = []
            filtered_chunks_ids = []
            skipped_count = 0

            # Prepare all chunks with their metadata
            all_chunks_with_metadata = []
            for i, chunk in enumerate(chunks):
                chunk_id = chunks_ids[i]
                metadata = chunk.chunk_metadata.copy() if chunk.chunk_metadata else {}
                # Add asset_id and knowledge_base_id to metadata if not already present
                metadata["asset_id"] = str(chunk.chunk_asset_id)
                metadata["knowledge_base_id"] = str(chunk.chunk_knowledge_base_id)
                metadata["chunk_order"] = chunk.chunk_order

                all_chunks_with_metadata.append((chunk, chunk_id, metadata))

            # If skip_duplicates, perform batch duplicate checking
            if skip_duplicates and all_chunks_with_metadata:
                # Prepare filter dictionaries for batch search
                filter_dicts = []
                for _, _, metadata in all_chunks_with_metadata:
                    filter_dicts.append({
                        "asset_id": metadata["asset_id"],
                        "chunk_order": metadata["chunk_order"]
                    })

                # Perform batch search for duplicates
                duplicate_results = await self.vectordb_client.batch_search_by_metadata(
                    collection_name=collection_name,
                    filter_dicts=filter_dicts
                )

                # Process each chunk based on duplicate check results
                for i, (chunk, chunk_id, metadata) in enumerate(all_chunks_with_metadata):
                    filter_key = f"asset_id:{metadata['asset_id']}_chunk_order:{metadata['chunk_order']}"

                    # Check if this chunk already exists
                    existing = duplicate_results.get(filter_key, [])
                    if existing and len(existing) > 0:
                        # Skip this chunk as it already exists
                        skipped_count += 1
                        continue

                    # If we get here, add the chunk to be processed
                    texts.append(chunk.chunk_text)
                    metadatas.append(metadata)
                    filtered_chunks_ids.append(chunk_id)
            else:
                # No duplicate checking, process all chunks
                for chunk, chunk_id, metadata in all_chunks_with_metadata:
                    texts.append(chunk.chunk_text)
                    metadatas.append(metadata)
                    filtered_chunks_ids.append(chunk_id)

            # If no chunks to process after filtering, return success
            if not texts:
                logger.info(f"No new chunks to index. Skipped {skipped_count} existing chunks.")
                return True

            # Generate embeddings for each text
            try:
                vectors = self.embedding_client.embed_text(
                    text=texts,
                    document_type=DocumentTypeEnum.DOCUMENT.value
                )
                # Check if embeddings were generated successfully
                if not vectors or len(vectors) == 0:
                    logger.error("Failed to generate embeddings for chunks")
                    return False

            except Exception as e:
                logger.error(f"Error generating embeddings: {str(e)}")
                return False

            # Insert data chunks into vector database
            is_inserted = await self.vectordb_client.insert_many(
                collection_name=collection_name,
                texts=texts,
                metadatas=metadatas,
                vectors=vectors,
                record_ids=filtered_chunks_ids
            )

            if not is_inserted:
                logger.error(f"Failed to insert chunks into vector database collection '{collection_name}'")
                return False

            logger.info(f"Successfully indexed {len(texts)} chunks into collection '{collection_name}'. Skipped {skipped_count} existing chunks.")
            return True

        except Exception as e:
            logger.error(f"Error indexing chunks into vector database: {str(e)}")
            return False

    async def index_asset_into_vector_db(self, knowledge_base: KnowledgeBase, asset: Asset, chunks: List[DataChunk], chunks_ids: List[int], do_reset: bool = True, skip_duplicates: bool = False) -> tuple[bool, str]:
        """Index a specific asset's chunks into the vector database

        Args:
            knowledge_base: The knowledge base object
            asset: The asset object being indexed
            chunks: List of data chunks to index
            chunks_ids: List of chunk IDs
            do_reset: Whether to reset existing chunks for this asset
            skip_duplicates: Whether to skip duplicate chunks

        Returns:
            tuple: (success, error_message)
                - success: True if indexing was successful, False otherwise
                - error_message: Empty string if successful, error details if failed
        """
        try:
            # Get or create collection
            collection_name = self.create_collection_name(knowledge_base_id=str(knowledge_base.id))
            collection_exists = await self.vectordb_client.is_collection_exists(collection_name=collection_name)

            if not collection_exists:
                # Create the collection if it doesn't exist
                success, error_msg, _ = await self.create_vector_db_collection(
                    knowledge_base=knowledge_base,
                    do_reset=False
                )

                if not success:
                    return False, f"Failed to create collection: {error_msg}"

                collection_name = self.create_collection_name(knowledge_base_id=str(knowledge_base.id))

            # Delete existing chunks for this asset if do_reset is True
            asset_id_str = str(asset.id)
            if do_reset:
                logger.info(f"Resetting asset {asset_id_str} in collection {collection_name} (deleting existing chunks only)")
                deleted = await self.vectordb_client.delete_by_metadata(
                    collection_name=collection_name,
                    filter_dict={"asset_id": asset_id_str}
                )
                if not deleted:
                    logger.warning(f"Failed to delete existing chunks for asset {asset_id_str} during reset")
                else:
                    logger.info(f"Successfully deleted existing chunks for asset {asset_id_str}")

            # Index the chunks
            if not chunks or len(chunks) == 0:
                return True, ""  # No chunks to index, consider it a success

            indexed = await self.index_into_vector_db(
                collection_name=collection_name,
                chunks=chunks,
                chunks_ids=chunks_ids,
                skip_duplicates=skip_duplicates
            )

            if not indexed:
                return False, f"Failed to index chunks for asset {asset_id_str}"

            return True, ""
        except Exception as e:
            error_msg = f"Error indexing asset {str(asset.id)}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    async def search_vector_db(
        self,
        knowledge_base: KnowledgeBase,
        query: str,
        limit: int = 10
        ):
        """Search a knowledge base's vector database collection"""
        # step1: get collection name
        query_vector = None
        collection_name = self.create_collection_name(knowledge_base_id=str(knowledge_base.id))

        # step2: generate text embedding vector
        vectors =  self.embedding_client.embed_text(text=query,
                                                   document_type=DocumentTypeEnum.DOCUMENT.value)

        if not vectors or len(vectors) == 0:
            return None
        
        if isinstance(vectors, list) and len(vectors) > 0:
            query_vector = vectors[0]

        if not query_vector:
            return False    


        # step3: do semantic search in the vector db and retrieve most similar texts
        retrieved_documents = await self.vectordb_client.search_by_vector(
            collection_name = collection_name,
            vector = query_vector,
            limit = limit
        )

        if not retrieved_documents:
            return None

        return retrieved_documents














