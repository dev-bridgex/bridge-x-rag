from .BaseController import BaseController
from fastapi import UploadFile
import os
import re
import aiofiles
from app.logging import get_logger
from app.models.db_schemas import Asset
from app.models import FileTypesEnum
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Optional

logger = get_logger(__name__)

class AssetController(BaseController):
    def __init__(self):
        super().__init__()
        self.size_scale = 1048576  # Convert MB to Bytes

    def validate_uploaded_file(self, file: UploadFile):
        """
        Validates the uploaded file.
        Raises ValueError with descriptive message if validation fails.

        Args:
            file: The uploaded file to validate

        Returns:
            bool: True if the file is valid

        Raises:
            ValueError: If the file type is not supported or file size exceeds the limit
        """
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            error_message = f"File type {file.content_type} not supported. Allowed types: {self.app_settings.FILE_ALLOWED_TYPES}"
            logger.warning(f"File validation failed: {error_message}")
            raise ValueError(error_message)

        # Check file size - handle case where size might be None
        file_size = file.size
        if file_size is None:
            # Try to determine size by reading and seeking back
            try:
                file.file.seek(0, 2)  # Seek to end
                file_size = file.file.tell()  # Get position (size)
                file.file.seek(0)  # Seek back to beginning
            except Exception as e:
                logger.warning(f"Could not determine file size: {e}")
                # Assume it's valid and let other validations catch issues
                file_size = 0

        if file_size > self.app_settings.FILE_MAX_SIZE * self.size_scale:
            max_size_mb = self.app_settings.FILE_MAX_SIZE
            error_message = f"File size ({file_size / self.size_scale:.2f} MB) exceeds maximum allowed size ({max_size_mb} MB)"
            logger.warning(f"File validation failed: {error_message}")
            raise ValueError(error_message)

        return True

    def generate_unique_filepath(self, project_path: str, original_file_name: str):
        """Generate a unique file path for an asset in a project directory"""
        random_key = self.generate_random_string()
        cleaned_file_name = self.get_clean_file_name(orig_file_name=original_file_name)
        new_file_name = random_key + "_" + cleaned_file_name

        new_file_path = os.path.join(
            project_path, new_file_name
        )

        while os.path.exists(new_file_path):
            random_key = self.generate_random_string()
            new_file_name = random_key + "_" + cleaned_file_name
            new_file_path = os.path.join(
                project_path, new_file_name
            )

        return new_file_path, new_file_name

    def get_clean_file_name(self, orig_file_name: str):
        """Clean a file name by removing special characters"""
        # remove any special characters except underscore and .
        cleaned_file_name = re.sub(r'[^\w.]', '', orig_file_name.strip())

        # replace spaces with underscore
        cleaned_file_name = cleaned_file_name.replace(" ", "_")

        return cleaned_file_name

    async def save_uploaded_file(self, file: UploadFile, file_path: str, chunk_size: int):
        """Save an uploaded file to the specified path"""
        try:
            # Opens the destination file asynchronously
            async with aiofiles.open(file=file_path, mode="wb") as f:
                # Reads the uploaded file in chunks
                while chunk := await file.read(chunk_size):
                    # write the chunk in the destination file f
                    await f.write(chunk)

            return True
        except Exception as e:
            logger.error(f"Error while uploading file: {e}")

            # Try to clean up the file if it was partially written
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up file after upload error: {cleanup_error}")

            return False

    def delete_asset_file(self, file_path: str) -> bool:
        """Delete an asset file from the file system"""
        if not os.path.exists(file_path):
            logger.warning(f"Asset file not found during deletion: {file_path}")
            return False

        try:
            os.remove(file_path)
            logger.info(f"Successfully deleted asset file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting asset file '{file_path}': {e}")
            return False

    def get_file_extension(self, file_name: str) -> str:
        """Get the extension of a file"""
        return os.path.splitext(file_name)[-1]

    def get_file_path(self, file_name: str, project_path: str) -> str:
        """Get the full path to a file in a project directory"""
        return os.path.join(project_path, file_name)

    def get_file_loader(self, file_name: str, file_path: str):
        """Get the appropriate document loader for a file based on its extension"""
        file_extension = self.get_file_extension(file_name=file_name)

        if file_extension == FileTypesEnum.TXT.value:
            return TextLoader(file_path, encoding="utf-8")

        if file_extension == FileTypesEnum.PDF.value:
            return PyMuPDFLoader(file_path)

        return None

    def get_file_content(self, file_name: str, file_path: str) -> List[Document]:
        """Load the content of a file as a list of documents"""
        loader = self.get_file_loader(file_name=file_name, file_path=file_path)
        if loader is None:
            logger.error(f"No loader available for file: {file_name}")
            return None
        return loader.load()

    def process_file_content(
        self,
        file_content: List[Document],
        file_name: str,
        chunk_size: int=400,
        overlap_size: int=20
    ) -> List[Document]:
        """Process file content into chunks"""
        if not file_content:
            logger.error(f"No content to process for file: {file_name}")
            return None

        file_content_texts = [
            document.page_content
            for document in file_content
        ]

        file_content_metadatas = [
            document.metadata
            for document in file_content
        ]

        # Improved splitter with paragraph and sentence awareness
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap_size,
            separators=["\n\n", "\n"], # favors paragraphs
            length_function=len,
            is_separator_regex=False
        )

        chunks = text_splitter.create_documents(
            file_content_texts,
            metadatas=file_content_metadatas
        )

        return chunks
