from .BaseController import BaseController
from app.stores.vectordb import VectorDBProviderInterface
from app.stores.llm import LLMProviderInterface
from app.stores.llm.LLMEnums import DocumentTypeEnum
from app.models import ChunkModel
from app.models.db_schemas import KnowledgeBase, DataChunk, Asset
from app.models.db_schemas.data_chunk import RetrievedDocument
from typing import List, Tuple, Dict, Any
import json
import asyncio
import re
from app.logging import get_logger
from app.stores.llm.templates.template_parser import TemplateParser
from app.utils.query_rewriter import QueryRewriter
from app.utils.nltk_processor import extract_keywords, enhance_query, is_arabic_text

logger = get_logger(__name__)

class NLPController(BaseController):
    def __init__(self, vectordb_client: VectorDBProviderInterface,
                 generation_client: LLMProviderInterface,
                 embedding_client: LLMProviderInterface,
                 template_parser: TemplateParser = None,
                 chunk_model: ChunkModel = None,
                 nlp_client = None) -> None:
        super().__init__()

        self.vectordb_client: VectorDBProviderInterface = vectordb_client
        self.generation_client: LLMProviderInterface = generation_client
        self.embedding_client: LLMProviderInterface = embedding_client

        # Store a reference to the template parser
        # Each request will have its own instance
        self.template_parser = template_parser or TemplateParser()

        self.chunk_model = chunk_model
        self.nlp = nlp_client  # Injected NLTK client

        # Initialize query rewriter with its own template parser instance
        # This ensures language changes in the controller don't affect the rewriter
        self.query_rewriter = QueryRewriter(
            llm_client=self.generation_client,
            template_parser=self.template_parser
        )

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
                # Use the metadata field from the new schema
                metadata = chunk.metadata.copy() if hasattr(chunk, 'metadata') and chunk.metadata else {}
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
                vectors = await self.embedding_client.embed_text(
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
        ) -> List[RetrievedDocument] | None:
        """
        Search a knowledge base's vector database collection using semantic search

        Args:
            knowledge_base: The knowledge base to search in
            query: The user's question
            limit: Maximum number of chunks to retrieve

        Returns:
            List of RetrievedDocument objects or None if search fails
        """
        # step1: get collection name
        query_vector = None
        collection_name = self.create_collection_name(knowledge_base_id=str(knowledge_base.id))

        # step2: generate text embedding vector
        vectors =  await self.embedding_client.embed_text(text=query,
                                                   document_type=DocumentTypeEnum.QUERY.value)

        if not vectors or len(vectors) == 0:
            return None

        if isinstance(vectors, list) and len(vectors) > 0:
            query_vector = vectors[0]

        if not query_vector:
            return None


        # step3: do semantic search in the vector db and retrieve most similar texts
        retrieved_documents = await self.vectordb_client.search_by_vector(
            collection_name = collection_name,
            vector = query_vector,
            limit = limit
        )

        if not retrieved_documents:
            return None

        return retrieved_documents


    async def rewrite_query(self, query: str, knowledge_base: KnowledgeBase = None, is_cross_language: bool = None) -> str:
        """
        Rewrite a query using LLM to improve retrieval performance

        Args:
            query: The original user query
            knowledge_base: Optional knowledge base for context
            is_cross_language: Whether this is a cross-language search (e.g., Arabic query for English content)

        Returns:
            Rewritten query or original query if rewriting fails
        """
        try:
            # Detect if query is in Arabic
            is_arabic = is_arabic_text(query)

            # Auto-detect cross-language search if not explicitly specified
            if is_cross_language is None and is_arabic:
                is_cross_language = True
                logger.info("Auto-detected cross-language search (Arabic query for English content)")

            kb_name = knowledge_base.knowledge_base_name if knowledge_base else None

            # Rewrite the query
            result = await self.query_rewriter.rewrite_query(
                original_query=query,
                knowledge_base_name=kb_name,
                is_cross_language=is_cross_language
            )

            if result["success"]:
                logger.info(f"Query rewritten: '{query}' → '{result['rewritten_query']}'")
                return result["rewritten_query"]
            else:
                logger.warning(f"Query rewriting failed: {result.get('error', 'Unknown error')}")
                return query

        except Exception as e:
            logger.error(f"Error rewriting query: {str(e)}")
            return query

    async def extract_keywords(self, query: str) -> str:
        """
        Extract meaningful keywords from the query using NLTK

        Args:
            query: The user's question

        Returns:
            String of extracted keywords or original query if NLP is not available
        """
        # Detect language
        language = 'ar' if is_arabic_text(query) else 'en'

        # Extract keywords using NLTK processor
        keywords = extract_keywords(query, self.nlp, language)

        # Join keywords into a string
        keyword_string = " ".join(keywords)

        # If no keywords found, return the cleaned query
        if not keyword_string or len(keywords) < 1:
            # Clean the query based on language
            clean_query = query.replace("\n", " ").strip()
            if language == 'ar':
                clean_query = clean_query.replace("؟", " ").replace("،", " ")
            else:
                clean_query = clean_query.replace("?", " ").replace(".", " ").replace(",", " ")

            clean_query = re.sub(r'\s+', ' ', clean_query).strip()

            logger.debug(f"Too few keywords extracted, using cleaned query: {clean_query}")
            return clean_query

        logger.debug(f"Extracted keywords: {keyword_string}")
        return keyword_string


    async def enhance_query(self, query: str) -> dict:
        """
        Enhance a user query with NLP techniques for better search results

        Args:
            query: The user's original question

        Returns:
            Dictionary containing enhanced query information
        """
        # Detect language
        language = 'ar' if is_arabic_text(query) else 'en'

        # Use the NLTK processor to enhance the query
        result = enhance_query(query, self.nlp, language)

        # Log the enhancement
        logger.debug(f"Query enhancement: Original: '{query}' → Enhanced: '{result['enhanced_query']}'")

        return result


    async def perform_semantic_search(self, knowledge_base: KnowledgeBase, query: str, limit: int = 10) -> List[RetrievedDocument]:
        """
        Perform semantic search using vector database (Qdrant)

        Args:
            knowledge_base: The knowledge base to search in
            query: The user's question
            limit: Maximum number of chunks to retrieve

        Returns:
            List of RetrievedDocument objects
        """
        # This is essentially the existing search_vector_db method
        results = await self.search_vector_db(
            knowledge_base=knowledge_base,
            query=query.replace("\n", " ").strip(),
            limit=limit
        )

        return results if results else []


    async def perform_full_text_search(self, knowledge_base: KnowledgeBase, query: str, limit: int = 10) -> List[RetrievedDocument]:
        """
        Perform full-text search using MongoDB

        Args:
            knowledge_base: The knowledge base to search in
            query: The user's question
            limit: Maximum number of chunks to retrieve

        Returns:
            List of RetrievedDocument objects
        """
        # Check if chunk model is available
        if not self.chunk_model:
            logger.error("Chunk model not available for full-text search")
            return []

        # Extract keywords for better text search
        keywords = await self.extract_keywords(query)
        logger.info(f"Performing BM25 search with keywords: '{keywords}'")

        # Perform the search with the extracted keywords
        results = await self.chunk_model.search_text(
            knowledge_base_id=str(knowledge_base.id),
            query=keywords,
            limit=limit
        )

        # Log the results
        if results:
            logger.info(f"BM25 search found {len(results)} results")
        else:
            logger.warning(f"BM25 search found no results for query: '{query}' with keywords: '{keywords}'")

        return results


    async def perform_hybrid_search(self, knowledge_base: KnowledgeBase, query: str, limit: int = 10, alpha: float = 0.8) -> List[RetrievedDocument]:
        """
        Perform hybrid search combining semantic search and full-text search

        This method merges results from vector search (Qdrant) and full-text search (MongoDB).
        Documents are matched by their ID when available, or by a content hash as a fallback.
        The IDs from Qdrant are converted back to MongoDB ObjectId format before merging.

        Args:
            knowledge_base: The knowledge base to search in
            query: The user's question
            limit: Maximum number of chunks to retrieve
            alpha: Weight for semantic search results (0-1), where (1-alpha) is the weight for text search

        Returns:
            List of RetrievedDocument objects sorted by combined score
        """
        # Run both searches in parallel
        semantic_task = asyncio.create_task(self.perform_semantic_search(
            knowledge_base=knowledge_base,
            query=query,
            limit=limit * 2  # Get more results to allow for merging
        ))

        text_task = asyncio.create_task(self.perform_full_text_search(
            knowledge_base=knowledge_base,
            query=query,
            limit=limit * 2  # Get more results to allow for merging
        ))

        # Wait for both searches to complete
        semantic_results, bm25_results = await asyncio.gather(semantic_task, text_task)

        # If either search failed, use results from the other
        if not semantic_results:
            logger.warning("Semantic search returned no results, using only text search results")
            return bm25_results[:limit] if bm25_results else []

        if not bm25_results:
            logger.warning("Text search returned no results, using only semantic search results")
            return semantic_results[:limit] if semantic_results else []

        # Normalize and merge results
        semantic_max = max(doc.score for doc in semantic_results) if semantic_results else 1.0
        bm25_max = max(doc.score for doc in bm25_results) if bm25_results else 1.0

        def normalize(score, max_score):
            return score / max_score if max_score > 0 else 0

        # Create a dictionary to merge results by document ID
        merged = {}

        # Add semantic search results
        for doc in semantic_results:
            # Use content hash as fallback instead of memory address for more consistent identification
            doc_content = doc.text[:100]  # Use first 100 chars to avoid performance issues with large texts
            doc_id = doc.metadata.get("id", f"content_hash_{hash(doc_content)}")
            merged[doc_id] = {
                "score": normalize(doc.score, semantic_max) * alpha,
                "doc": doc
            }

        # Add or update with text search results
        for doc in bm25_results:
            # Use content hash as fallback instead of memory address for more consistent identification
            doc_content = doc.text[:100]  # Use first 100 chars to avoid performance issues with large texts
            doc_id = doc.metadata.get("id", f"content_hash_{hash(doc_content)}")
            if doc_id in merged:
                # Document exists in both results, combine scores
                merged[doc_id]["score"] += normalize(doc.score, bm25_max) * (1 - alpha)
            else:
                # Document only in text results
                merged[doc_id] = {
                    "score": normalize(doc.score, bm25_max) * (1 - alpha),
                    "doc": doc
                }

        # Sort by combined score
        results = sorted(merged.values(), key=lambda x: x["score"], reverse=True)

        # Create final list of documents with updated scores
        final_results = []
        for item in results[:limit]:
            doc = item["doc"]
            # Create a new RetrievedDocument with the combined score
            final_results.append(RetrievedDocument(
                text=doc.text,
                metadata=doc.metadata,
                score=item["score"]
            ))

        return final_results


    async def search_knowledge_base(self, knowledge_base: KnowledgeBase, query: str,
                            limit: int = 10, use_semantic: bool = True,
                            use_bm25: bool = False, use_hybrid: bool = False,
                            use_query_rewriting: bool = True) -> List[RetrievedDocument]:
        """
        Search a knowledge base using different search strategies with optional query rewriting

        Args:
            knowledge_base: The knowledge base to search in
            query: The user's question
            limit: Maximum number of chunks to retrieve
            use_semantic: Whether to use semantic search (vector search)
            use_bm25: Whether to use BM25 search (full-text search)
            use_hybrid: Whether to use hybrid search (combines semantic and BM25)
            use_query_rewriting: Whether to rewrite the query for better retrieval

        Returns:
            List of RetrievedDocument objects
        """
        # Clean the query
        clean_query = query.replace("\n", " ").strip()

        # Check if query is in Arabic
        is_arabic = is_arabic_text(clean_query)
        if is_arabic:
            logger.info(f"Detected Arabic query: '{clean_query}'")

        # Rewrite the query if requested
        search_query = clean_query
        if use_query_rewriting:
            # Use LLM to rewrite the query for better retrieval
            # For Arabic queries, explicitly set cross-language search
            if is_arabic:
                rewritten_query = await self.rewrite_query(
                    query=clean_query,
                    knowledge_base=knowledge_base,
                    is_cross_language=True
                )
            else:
                rewritten_query = await self.rewrite_query(
                    query=clean_query,
                    knowledge_base=knowledge_base
                )

            if rewritten_query and rewritten_query != clean_query:
                logger.info(f"Using rewritten query for retrieval: '{clean_query}' → '{rewritten_query}'")
                search_query = rewritten_query

            # Note: Special handling for Arabic queries is now done in the rewrite_query method
            # The rewritten query already includes both Arabic and English terms

        # Determine which search method to use
        results = None

        if use_hybrid:
            # Hybrid search (combines semantic and BM25)
            results = await self.perform_hybrid_search(
                knowledge_base=knowledge_base,
                query=search_query,
                limit=limit
            )
        elif use_bm25:
            # BM25 search (full-text search)
            results = await self.perform_full_text_search(
                knowledge_base=knowledge_base,
                query=search_query,
                limit=limit
            )
        else:
            # Default to semantic search (vector search)
            results = await self.perform_semantic_search(
                knowledge_base=knowledge_base,
                query=search_query,
                limit=limit
            )

        return results if results else []


    async def chat_with_knowledge_base(self, knowledge_base: KnowledgeBase, query: str, history: List[Dict[str, str]] = None,
                               use_rag: bool = True, use_hybrid: bool = True, limit: int = 10,
                               use_query_rewriting: bool = True) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Chat with a knowledge base using RAG or direct LLM generation

        Args:
            knowledge_base: The knowledge base to search in
            query: The user's question
            history: Previous chat history (list of role/content dictionaries)
            use_rag: Whether to use RAG (retrieval) or just direct LLM generation
            use_hybrid: Whether to use hybrid search (vector + text) or just vector search
            limit: Maximum number of chunks to retrieve when using RAG
            use_query_rewriting: Whether to rewrite the query for better retrieval

        Returns:
            Tuple containing:
                - response: The generated response text
                - sources: List of sources used to generate the response (empty if not using RAG)
        """
        # Initialize chat history if not provided
        if history is None:
            history = []

        # Create a working copy of the history to avoid modifying the original
        chat_history = history.copy()

        # Initialize system prompt if not present
        if not any(msg.get("role") == "system" for msg in chat_history):
            # Get the appropriate system prompt template based on whether we're using RAG
            system_prompt_key = "system_prompt_rag" if use_rag else "system_prompt_basic"
            system_prompt = self.template_parser.get_template("chat", system_prompt_key, {}) or "You are a skilled technical assistant. Provide accurate and helpful responses based on the available information."

            # Add the system prompt to the beginning of chat history
            chat_history.insert(0, self.generation_client.construct_prompt(
                prompt=system_prompt,
                role=self.generation_client.enums.SYSTEM.value
            ))

        # Extract system messages for chat_history
        filtered_chat_history = [msg for msg in chat_history if msg.get("role") == self.generation_client.enums.SYSTEM.value]

        # Format conversation history for the prompt
        conversation_text = ""
        for msg in chat_history:
            if msg.get("role") == self.generation_client.enums.USER.value:
                conversation_text += f"User: {msg.get('content', '')}\n\n"
            elif msg.get("role") == self.generation_client.enums.ASSISTANT.value:
                conversation_text += f"Assistant: {msg.get('content', '')}\n\n"

        sources = []
        retrieved_documents = []

        # If using RAG, retrieve relevant documents
        if use_rag:
            # Clean the query
            clean_query = query.replace("\n", " ").strip()

            # Check if query is in Arabic
            is_arabic = is_arabic_text(clean_query)
            if is_arabic:
                logger.info(f"Detected Arabic query: '{clean_query}'")

            # Rewrite the query if requested
            search_query = clean_query
            if use_query_rewriting:
                # Use LLM to rewrite the query for better retrieval
                # For Arabic queries, explicitly set cross-language search
                if is_arabic:
                    rewritten_query = await self.rewrite_query(
                        query=clean_query,
                        knowledge_base=knowledge_base,
                        is_cross_language=True
                    )
                else:
                    rewritten_query = await self.rewrite_query(
                        query=clean_query,
                        knowledge_base=knowledge_base
                    )

                if rewritten_query and rewritten_query != clean_query:
                    logger.info(f"Using rewritten query for retrieval: '{clean_query}' → '{rewritten_query}'")
                    search_query = rewritten_query

                # Note: Special handling for Arabic queries is now done in the rewrite_query method
                # The rewritten query already includes both Arabic and English terms

            # Retrieve related documents using either hybrid or semantic search
            if use_hybrid:
                retrieved_documents = await self.perform_hybrid_search(
                    knowledge_base=knowledge_base,
                    query=search_query,
                    limit=limit,
                )
            else:
                retrieved_documents = await self.perform_semantic_search(
                    knowledge_base=knowledge_base,
                    query=search_query,
                    limit=limit,
                )

        # Build the prompt based on whether we have documents
        if use_rag and retrieved_documents and len(retrieved_documents) > 0:
            # Format documents
            documents_text = ""
            for idx, doc in enumerate(retrieved_documents):
                doc_vars = {
                    "doc_number": str(idx + 1),
                    "score": f"{doc.score:.4f}",
                    "chunk_text": doc.text
                }

                doc_text = self.template_parser.get_template("chat", "document_prompt", doc_vars)
                documents_text += doc_text if doc_text else f"## Document {idx + 1} (Score: {doc.score:.4f})\n{doc.text}\n\n"

            # Check if this is a cross-language search (Arabic query for English content)
            is_arabic_query = is_arabic_text(query)

            # Set the language for the template parser based on query language
            if is_arabic_query:
                self.template_parser.set_language("ar")
            else:
                self.template_parser.set_language("en")

            # Get context prompt with appropriate language
            context_vars = {
                "documents": documents_text,
                "query": query
            }

            context_prompt = self.template_parser.get_template("chat", "context_prompt", context_vars)

            # If template not found, use default with cross-language handling if needed
            if not context_prompt:
                if is_arabic_query:
                    context_prompt = f"""
السؤال: {query}

المستندات المرجعية:
{documents_text}

إرشادات:
يرجى الإجابة على الاستفسار مباشرة بالاعتماد على المعلومات الواردة في المستندات.
قدم إجابة شاملة ومفصلة مع شرح واف.
يجب أن تكون إجابتك مفصلة - اهدف إلى كتابة 4-5 فقرات على الأقل مع معلومات تفصيلية.
عند استخدام معلومات من مستندات محددة، قم بالإشارة إليها بذكر أرقامها (مثلاً: 'وفقاً للمستند رقم 1...' أو 'كما ورد في المستند رقم 3...')
تأكد من ذكر أرقام المستندات في إجابتك عند استخدام معلومات منها.
قم بتوضيح المفاهيم، وتقديم أمثلة، وشرح الآثار المترتبة عندما يكون ذلك مناسبًا.
لا داعي لذكر أنك ستقدم المساعدة أو أنك راجعت المستندات - قدم المعلومات المفصلة المطلوبة مباشرة مع الإشارة المناسبة لأرقام المستندات.
إذا لم تجد إجابة كاملة في المستندات المرجعية، قدم أفضل إجابة شاملة ممكنة بناءً على المعلومات المتاحة. ويمكنك الاستعانة بمعرفتك العامة لتقديم أفضل إجابة مفصلة ممكنة.
قد تكون المستندات المرجعية باللغة الإنجليزية، لكن يجب عليك الإجابة باللغة العربية.
ترجم المعلومات من المستندات الإنجليزية إلى العربية بشكل دقيق مع الحفاظ على المعنى الأصلي.
"""
                else:
                    context_prompt = f"""
QUESTION: {query}

RELEVANT DOCUMENTS:
{documents_text}

INSTRUCTIONS:
Answer the question directly using information from the documents.
Provide a comprehensive, detailed response with thorough explanations.
Your answer should be substantial - aim for at least 4-5 paragraphs with detailed information.
When using information from specific documents, cite them by referring to their document numbers (e.g., 'According to Document 1...' or 'As mentioned in Document 3...').
Make sure to cite document numbers throughout your answer when drawing information from specific documents.
Elaborate on concepts, provide examples, and explain implications when appropriate.
Do not say you'll help or that you've reviewed the documents - just provide the detailed answer immediately with proper document citations.
If you can't find a complete answer in the documents, provide the best comprehensive answer you can. If the documents don't contain enough information, use your general knowledge to provide the best detailed answer possible.
"""

            # Combine everything into the final prompt
            prompt = f"""
{context_prompt}

Conversation History:
{conversation_text}
"""
            # Save sources for the response using SearchResult format
            sources = [
                {
                    "doc_num": str(idx + 1),  # Use 1-based indexing for doc_num
                    "text": doc.text,
                    "metadata": doc.metadata,
                    "score": doc.score
                }
                for idx, doc in enumerate(retrieved_documents)
            ]
        else:
            # No documents or not using RAG, use simple conversation format
            prompt = self.template_parser.get_template("chat", "conversation_format", {
                "conversation_history": conversation_text,
                "query": query
            }) or f"""
Conversation History:
{conversation_text}

Question:
{query}
"""

        # Format the system prompt for logging
        system_prompt_text = ""
        for msg in filtered_chat_history:
            if msg.get("role") == self.generation_client.enums.SYSTEM.value:
                system_prompt_text += f"SYSTEM PROMPT:\n{msg.get('content', '')}\n\n"

        # Create a formatted version of the prompt for logging
        formatted_prompt = f"{system_prompt_text}USER PROMPT:\n{prompt}"

        # Log the formatted prompt at DEBUG level
        logger.debug(f"LLM PROMPT (KB: {knowledge_base.id}, Query: '{query[:50]}{'...' if len(query) > 50 else ''}'):\n{'-'*80}\n{formatted_prompt}\n{'-'*80}")

        # Generate response
        response = await self.generation_client.generate_text(
            prompt=prompt,
            chat_history=filtered_chat_history
        )

        return response, sources

