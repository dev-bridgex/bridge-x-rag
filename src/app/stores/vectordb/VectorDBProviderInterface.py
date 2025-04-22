from abc import ABC, abstractmethod
from typing import List, Dict, Any


class VectorDBProviderInterface(ABC):

    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def is_collection_exists(self, collection_name: str) -> bool:
        pass

    @abstractmethod
    def list_all_collections(self) -> List:
        pass

    @abstractmethod
    def get_collection_info(self, collection_name: str) -> dict | None:
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> bool:
        pass

    @abstractmethod
    def create_collection(self,
                          collection_name: str,
                          embedding_size: int,
                          do_reset: bool = False
    ) -> bool:

        pass

    @abstractmethod
    def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: List[float],
        metadata: dict = None,
        record_id: str = None
    ) -> bool:

        pass

    @abstractmethod
    def insert_many(
        self,
        collection_name: str,
        texts: List[str],
        vectors:  List[List[float]],
        metadatas: List[dict] = None,
        record_ids: List = None,
        batch_size: int = 64
    ) -> bool:

        pass

    @abstractmethod
    def search_by_vector(
        self,
        collection_name: str,
        vector: List[float],
        limit: int = 5
    ) -> List:

        pass

    @abstractmethod
    def delete_by_metadata(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any]
    ) -> bool:
        """Delete records from a collection based on metadata filter

        Args:
            collection_name: Name of the collection to delete from
            filter_dict: Dictionary of metadata key-value pairs to filter by

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        pass

    @abstractmethod
    def search_by_metadata(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any],
        limit: int = 10
    ) -> List:
        """Search for records in a collection based on metadata filter

        Args:
            collection_name: Name of the collection to search in
            filter_dict: Dictionary of metadata key-value pairs to filter by
            limit: Maximum number of results to return

        Returns:
            List: List of matching records
        """
        pass

    @abstractmethod
    def batch_search_by_metadata(
        self,
        collection_name: str,
        filter_dicts: List[Dict[str, Any]]
    ) -> Dict[str, List]:
        """Search for records in a collection based on multiple metadata filters

        This is more efficient than calling search_by_metadata multiple times when checking
        for many potential duplicates.

        Args:
            collection_name: Name of the collection to search in
            filter_dicts: List of dictionaries, each containing metadata key-value pairs to filter by

        Returns:
            Dict: Dictionary mapping filter keys to lists of matching records
        """
        pass



