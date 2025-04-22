import uuid
from qdrant_client import AsyncQdrantClient

from qdrant_client.http.models import (
    Distance, PointStruct, UpdateStatus, CollectionInfo, CollectionsResponse,
    UpdateResult, Filter, VectorParams, QueryResponse
)
from app.stores.vectordb.VectorDBProviderInterface import VectorDBProviderInterface
from app.stores.vectordb.VectorDBEnums import DistanceMethodEnum
from app.logging import get_logger
# from logging import getLogger
from typing import Optional, List, Union, Dict, Any

class QdrantDBProvider(VectorDBProviderInterface):
    """Asynchronous provider for interacting with Qdrant."""

    def __init__(self,
                 db_path: Optional[str] = None,
                 distance_method: str = DistanceMethodEnum.COSINE.value,
                 url: Optional[str] = "",
                 api_key: Optional[str] = None,
                 prefer_grpc: bool = False,
                 timeout: Optional[int] = 10,
                 # grpc_options: Optional[dict] = None, # Example for future config
                 ) -> None:

        self.url = url
        self.api_key = api_key
        self.db_path = db_path if db_path and len(db_path) else None
        self.prefer_grpc = prefer_grpc
        self.timeout = timeout
        # self.grpc_options = grpc_options

        # Use the Async client
        self.client: Optional[AsyncQdrantClient] = None

        distance_map = {
            DistanceMethodEnum.COSINE.value: Distance.COSINE,
            DistanceMethodEnum.DOT.value: Distance.DOT,
            DistanceMethodEnum.EUCLID.value: Distance.EUCLID,
            DistanceMethodEnum.MANHATTAN.value: Distance.MANHATTAN,
        }
        if distance_method in distance_map:
            self.distance_method = distance_map[distance_method]
        else:
            # Get logger instance early for potential error logging
            self.logger = get_logger(__name__)
            self.logger.error(f"Unsupported distance method provided: {distance_method}")
            raise ValueError(f"Unsupported distance method: {distance_method}")

        self.logger = get_logger(__name__) # Get logger if not already done
        self.logger.info(f"Async QdrantDBProvider initialized. URL: {self.url}, Path: {self.db_path}, Distance: {distance_method}")


    async def _check_connection(self):
        """Helper method to ensure the client is connected."""
        if not self.client:
            self.logger.error("Qdrant client is not connected. Call connect() first.")
            # Consider raising a more specific custom exception if needed
            raise ConnectionError("Qdrant client is not connected.")


    async def connect(self) -> None:
        """Establishes an asynchronous connection to Qdrant."""
        if self.client:
            self.logger.warning("Already connected to Qdrant.")
            return

        try:
            if not self.db_path:
                self.logger.info(f"Connecting to Qdrant Cloud Database Instance asynchronously... URL: {self.url}, gRPC: {self.prefer_grpc}")

                # Instantiate the AsyncQdrantClient
                self.client = AsyncQdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                    prefer_grpc=self.prefer_grpc,
                    timeout=self.timeout,
                    # grpc_options=self.grpc_options
                )
                self.logger.info("Successfully connected to Qdrant Cloud Database Instance.")
            
            else:
                self.logger.info(f"Connecting to Qdrant Local Database Instance asynchronously... URL: {self.url}, Path: {self.db_path}, gRPC: {self.prefer_grpc}")
                
                # Instantiate the AsyncQdrantClient
                self.client = AsyncQdrantClient(
                    url=self.url,
                    path = self.db_path,
                    prefer_grpc=self.prefer_grpc,
                    timeout=self.timeout,
                    # grpc_options=self.grpc_options
                )
                self.logger.info("Successfully connected to Qdrant Cloud Database Instance.")
                 
        except Exception as e:
            self.logger.error(f"Failed to connect to Qdrant: {e}", exc_info=True)
            self.client = None # Ensure client is None on failure
            raise ConnectionError(f"Failed to connect to Qdrant: {e}") from e


    async def disconnect(self) -> None:
        """Closes the asynchronous connection to Qdrant."""
        if self.client:
            try:
                self.logger.info("Disconnecting from Qdrant...")
                await self.client.close(grpc_grace=1.0) # close is async, add grace period
                self.logger.info("Successfully disconnected from Qdrant.")
            except Exception as e:
                self.logger.error(f"Error while closing Qdrant client: {e}", exc_info=True)
            finally:
                self.client = None # Ensure reference is removed
        else:
            self.logger.info("Already disconnected or never connected.")


    async def __aenter__(self):
        """Async context manager enter."""
        await self.connect()
        return self


    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()



    # --- Collection Methods ---

    async def list_all_collections(self) -> Optional[CollectionsResponse]:
        """Lists all collections asynchronously. Returns CollectionsResponse or None on error."""
        await self._check_connection()
        try:
            self.logger.debug("Fetching list of all collections.")
            response = await self.client.get_collections()
            return response
        except Exception as e:
            self.logger.error(f"Error listing collections: {e}", exc_info=True)
            return None


    async def get_collection_info(self, collection_name: str) -> Optional[CollectionInfo]:
        """Gets info about a specific collection asynchronously. Returns CollectionInfo or None."""
        await self._check_connection()
        try:
            self.logger.debug(f"Fetching info for collection: {collection_name}")
            collection_info = await self.client.get_collection(collection_name=collection_name)
            return collection_info
        except Exception as e:
             self.logger.error(f"Error getting info for collection '{collection_name}': {e}", exc_info=True)
             # Consider checking e for specific Qdrant "not found" errors if needed
             return None


    async def is_collection_exists(self, collection_name: str) -> bool:
        """Checks if a collection exists asynchronously."""
        await self._check_connection()
        try:
            self.logger.debug(f"Checking existence of collection: {collection_name}")
            exists = await self.client.collection_exists(collection_name=collection_name)
            self.logger.debug(f"Collection '{collection_name}' exists: {exists}")
            return exists
        except Exception as e:
            self.logger.error(f"Error checking existence of collection '{collection_name}': {e}", exc_info=True)
            return False


    async def delete_collection(self, collection_name: str) -> bool:
        """Deletes a collection asynchronously. Returns True if deletion succeeded or collection didn't exist, False on error."""
        await self._check_connection()
        self.logger.info(f"Attempting to delete collection: {collection_name}")
        try:
            if not await self.is_collection_exists(collection_name):
                self.logger.warning(f"Collection '{collection_name}' does not exist, deletion skipped.")
                return True # Consider the state as "deleted"

            result = await self.client.delete_collection(collection_name=collection_name, timeout=self.timeout)

            if result:
                self.logger.info(f"Successfully deleted collection: {collection_name}")
                return True
            else:
                self.logger.warning(f"Deletion call for '{collection_name}' returned False (server-side issue?).")
                return False
        except Exception as e:
            self.logger.error(f"Error deleting collection '{collection_name}': {e}", exc_info=True)
            return False


    async def create_collection(self,
                                collection_name: str,
                                embedding_size: int,
                                do_reset: bool = False) -> bool:
        """Creates a collection asynchronously. Returns True if newly created, False otherwise."""
        await self._check_connection()
        self.logger.info(f"Request to create collection: {collection_name} (size: {embedding_size}, reset: {do_reset})")

        try:
            collection_already_exists = await self.is_collection_exists(collection_name)

            if collection_already_exists and do_reset:
                self.logger.info(f"Resetting collection '{collection_name}'. Deleting existing first.")
                delete_success = await self.delete_collection(collection_name=collection_name)
                if not delete_success:
                    self.logger.error(f"Failed to delete existing collection '{collection_name}' during reset. Aborting creation.")
                    return False
                collection_already_exists = False # It's gone now

            if collection_already_exists:
                 self.logger.warning(f"Collection '{collection_name}' already exists and reset=False. Creation skipped.")
                 return False

            # Proceed with creation
            self.logger.info(f"Creating new collection: {collection_name}")
            success = await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams( # Use imported VectorParams
                    size=embedding_size,
                    distance=self.distance_method
                ),
                timeout=self.timeout
                # Add other configs (hnsw_config, etc.) here if needed
            )
            if success:
                self.logger.info(f"Successfully created collection: {collection_name}")
                return True
            else:
                self.logger.warning(f"Create collection call for '{collection_name}' returned False (server-side issue?).")
                return False
        except Exception as e:
            self.logger.error(f"Error during create/reset for collection '{collection_name}': {e}", exc_info=True)
            return False

    # --- Point/Record Methods ---

    async def insert_one(self, collection_name: str,
                         text: str,
                         vector: List[float],
                         metadata: Optional[Dict[str, Any]] = None,
                         record_id: Optional[Union[str, int, uuid.UUID]] = None,
                         wait: bool = True) -> bool:
        
        """Inserts/updates a single record asynchronously. Returns True on success, False otherwise."""
        await self._check_connection()

        if not await self.is_collection_exists(collection_name):
            self.logger.error(f"Cannot insert record into non-existent collection: {collection_name}")
            return False

        if record_id is None:
            record_id = str(uuid.uuid4())

        payload = {"text": text}
        if metadata:
            payload.update(metadata)

        try:
            self.logger.debug(f"Upserting single record '{record_id}' into '{collection_name}'.")
            update_result: UpdateResult = await self.client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct( # Use imported PointStruct
                        id=record_id,
                        vector=vector,
                        payload=payload
                    )
                ],
                wait=wait
            )

            if wait: # Only check status if we waited
                if update_result.status == UpdateStatus.COMPLETED:
                     self.logger.debug(f"Successfully upserted record '{record_id}' (wait=True). Status: {update_result.status}")
                     return True
                else:
                     self.logger.warning(f"Upsert operation for record '{record_id}' (wait=True) resulted in status: {update_result.status}")
                     return False
            else:
                self.logger.debug(f"Submitted upsert for record '{record_id}' (wait=False).")
                return True # Assume submission success if no exception

        except Exception as e:
            self.logger.error(f"Error upserting record '{record_id}' into '{collection_name}': {e}", exc_info=True)
            return False

    async def insert_many(self,
                          collection_name: str,
                          texts: List[str],
                          vectors: List[List[float]],
                          metadatas: Optional[List[Optional[Dict[str, Any]]]] = None,
                          record_ids: Optional[List[Union[str, int, uuid.UUID]]] = None,
                          batch_size: int = 64,
                          wait: bool = False) -> bool:
        
        """Inserts/updates records in batches asynchronously. Returns True if all batches submitted, False on first error."""
        await self._check_connection()

        if not await self.is_collection_exists(collection_name):
            self.logger.error(f"Cannot insert records into non-existent collection: {collection_name}")
            return False

        num_records = len(texts)
        # Input validation (remains synchronous)
        if len(vectors) != num_records: raise ValueError("Texts and vectors length mismatch.")
        if metadatas is not None and len(metadatas) != num_records: raise ValueError("Texts and metadatas length mismatch.")
        if record_ids is not None and len(record_ids) != num_records: raise ValueError("Texts and record_ids length mismatch.")

        # Prepare defaults (synchronous)
        if metadatas is None:metadatas = [None] * num_records
        
        # Use caller-provided IDs if available, otherwise generate UUIDs
        ids_to_use = record_ids if record_ids is not None else [str(uuid.uuid4()) for _ in range(num_records)]

        total_submitted = 0
        num_batches = (num_records + batch_size - 1) // batch_size
        self.logger.info(f"Starting async insert_many into '{collection_name}'. Records: {num_records}, Batch Size: {batch_size}, Batches: {num_batches}")

        for i in range(0, num_records, batch_size):
            batch_num = i // batch_size + 1
            batch_end = min(i + batch_size, num_records)
            self.logger.debug(f"Processing batch {batch_num}/{num_batches}: records {i} to {batch_end-1}")

            # Prepare batch points (synchronous)
            batch_points: List[PointStruct] = []
            try:
                for idx in range(i, batch_end):
                    payload = {
                        "text": texts[idx], 
                        "metadata": (metadatas[idx])
                    }
                    batch_points.append(
                        PointStruct(id=ids_to_use[idx], vector=vectors[idx], payload=payload)
                    )
            except Exception as e: # Catch errors during PointStruct prep
                 self.logger.error(f"Error preparing points for batch {batch_num} (index {idx}): {e}", exc_info=True)
                 return False # Fail fast

            if not batch_points:
                self.logger.warning(f"Skipping empty batch {batch_num}.")
                continue

            # Upsert the batch asynchronously
            try:
                update_result: UpdateResult = await self.client.upsert(
                    collection_name=collection_name,
                    points=batch_points,
                    wait=wait
                )
                # With wait=False, successful await means accepted by server.
                # Check update_result.status only if wait=True and if necessary.
                total_submitted += len(batch_points)
                self.logger.debug(f"Submitted batch {batch_num} ({len(batch_points)} points) for upsert (wait={wait}).")

            except Exception as e:
                self.logger.error(f"Error upserting batch {batch_num} into '{collection_name}': {e}", exc_info=True)
                return False # Stop on first batch error

        self.logger.info(f"Finished insert_many for '{collection_name}'. Total submitted: {total_submitted}/{num_records}.")
        return True


    async def search_by_vector(self,
                               collection_name: str,
                               vector: List[float],
                               limit: int = 5,
                               score_threshold: Optional[float] = None,
                               query_filter: Optional[Filter] = None # Use imported Filter
                               ) -> List[Dict[str, Any]] | None:
        
        """Searches asynchronously. Returns list of dicts or [] on error/no results."""
        await self._check_connection()
        self.logger.debug(f"Async searching collection '{collection_name}' (limit={limit}, threshold={score_threshold}).")

        try:
            results: QueryResponse = await self.client.query_points(
                collection_name = collection_name,
                query = vector,
                query_filter = query_filter, # Pass the filter object
                limit = limit,
                score_threshold = score_threshold,
                with_payload=True, # Request payload
                with_vectors=False # Don't need vectors in result usually
            )

            if not results:
                self.logger.debug(f"No results found for search in '{collection_name}'.")
                return None

            # output = []
            # for point in results.points:
            #      text_payload = point.payload.get("text") if point.payload else None
            #      output.append({
            #         "id": point.id,
            #         "score": point.score,
            #         "text": text_payload,
            #         # "payload": point.payload # Optionally include full payload
            #      })
                 
            # self.logger.debug(f"Found {len(output)} results for search in '{collection_name}'.")
            
            return results

        except Exception as e:
            self.logger.error(f"Error during vector search in '{collection_name}': {e}", exc_info=True)
            return None
