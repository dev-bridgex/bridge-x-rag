from .BaseController import BaseController
from .NLPController import NLPController
import os
import shutil
import threading
import time
from app.logging import get_logger
from app.models.db_schemas import KnowledgeBase

logger = get_logger(__name__)

class KnowledgeBaseController(BaseController):
    def __init__(self):
        super().__init__()
        # Dictionary to store locks for directory creation
        self._dir_locks = {}

    def get_knowledge_base_path(self, knowledge_base_id: str):
        """Get or create a knowledge base directory path using knowledge base ID

        Uses a locking mechanism to prevent race conditions when multiple requests
        try to create the same directory simultaneously.

        Args:
            knowledge_base_id: The ID of the knowledge base

        Returns:
            str: The path to the knowledge base directory
        """
        # Use knowledge base ID for directory name to ensure uniqueness
        knowledge_base_dir_path = os.path.join(self.files_dir, knowledge_base_id)

        # Get or create a lock for this knowledge base ID
        if knowledge_base_id not in self._dir_locks:
            self._dir_locks[knowledge_base_id] = threading.Lock()

        # Acquire the lock before checking/creating the directory
        with self._dir_locks[knowledge_base_id]:
            if not os.path.exists(knowledge_base_dir_path):
                try:
                    os.mkdir(knowledge_base_dir_path)
                    logger.info(f"Created knowledge base directory: {knowledge_base_dir_path}")
                except Exception as e:
                    logger.error(f"Error creating knowledge base directory '{knowledge_base_dir_path}': {e}")
                    # If another process created the directory between our check and mkdir
                    if not os.path.exists(knowledge_base_dir_path):
                        raise

        return knowledge_base_dir_path


    def find_knowledge_base_path(self, knowledge_base_id: str):
        """Find an existing knowledge base directory path using knowledge base ID"""
        knowledge_base_dir_path = os.path.join(self.files_dir, knowledge_base_id)

        if not os.path.exists(knowledge_base_dir_path):
            return None

        return knowledge_base_dir_path


    def delete_knowledge_base_directory(self, knowledge_base_id: str) -> bool:
        """Delete a knowledge base directory and all its contents using knowledge base ID"""
        knowledge_base_dir_path = self.find_knowledge_base_path(knowledge_base_id)

        if knowledge_base_dir_path is None:
            logger.warning(f"Knowledge base directory for ID '{knowledge_base_id}' not found during deletion")
            return False

        try:
            shutil.rmtree(knowledge_base_dir_path)
            logger.info(f"Successfully deleted knowledge base directory: {knowledge_base_dir_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting knowledge base directory '{knowledge_base_dir_path}': {e}")
            return False


    async def delete_knowledge_base_resources(self, knowledge_base: KnowledgeBase, nlp_controller: NLPController) -> dict:
        """Delete all external resources associated with a knowledge base (vector database and file system)

        Args:
            knowledge_base: The knowledge base object
            nlp_controller: The NLP controller for vector database operations

        Returns:
            dict: A dictionary with details about which resources were deleted
        """
        result = {
            "vector_db_deleted": False,
            "directory_deleted": False,
            "overall_success": False
        }

        # Delete the knowledge base's vector database collection
        try:
            result["vector_db_deleted"] = await nlp_controller.delete_vector_db_collection(knowledge_base=knowledge_base)
            if not result["vector_db_deleted"]:
                logger.warning(f"Failed to delete vector database collection for knowledge base ID: {knowledge_base.id}")
            else:
                logger.info(f"Successfully deleted vector database collection for knowledge base ID: {knowledge_base.id}")
        except Exception as e:
            logger.error(f"Error deleting vector database collection for knowledge base ID '{knowledge_base.id}': {e}")
            result["vector_db_deleted"] = False

        # Delete the knowledge base directory
        result["directory_deleted"] = self.delete_knowledge_base_directory(knowledge_base_id=str(knowledge_base.id))

        # Set overall success flag
        result["overall_success"] = result["vector_db_deleted"] and result["directory_deleted"]

        return result


    async def update_knowledge_base_resources(self, knowledge_base: KnowledgeBase, new_knowledge_base_name: str, nlp_controller: NLPController) -> bool:
        """Update external resources when a knowledge base is updated (currently a placeholder for future extensions)

        Args:
            knowledge_base: The knowledge base object being updated
            new_knowledge_base_name: The new name for the knowledge base
            nlp_controller: The NLP controller for vector database operations

        Returns:
            bool: True if the update was successful, False otherwise
        """
        # Log the update operation
        logger.info(f"Updating knowledge base resources for {knowledge_base.id} (new name: {new_knowledge_base_name})")

        # Currently, there are no vector database operations needed when updating a knowledge base name
        # This method is included for future extensions, such as if we need to update collection metadata
        # or perform other operations when a knowledge base is renamed

        # For example, in the future we might want to update metadata in the vector database:
        # if nlp_controller and hasattr(nlp_controller, 'update_collection_metadata'):
        #     try:
        #         await nlp_controller.update_collection_metadata(
        #             knowledge_base=knowledge_base,
        #             metadata_updates={"knowledge_base_name": new_knowledge_base_name}
        #         )
        #     except Exception as e:
        #         logger.error(f"Error updating vector database metadata: {e}")
        #         return False

        # For now, just return True to indicate success
        return True
