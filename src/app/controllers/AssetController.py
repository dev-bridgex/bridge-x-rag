from .BaseController import BaseController
from fastapi import UploadFile
import os
import re
import aiofiles
import base64
import hashlib
from app.logging import get_logger
from typing import List, Dict, Any, Optional, Tuple
import pymupdf
from app.helpers.config import get_settings


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

    def generate_unique_filepath(self, knowledge_base_path: str, original_file_name: str):
        """Generate a unique file path for an asset in a project directory"""
        random_key = self.generate_random_string()
        cleaned_file_name = self.get_clean_file_name(orig_file_name=original_file_name)
        new_file_name = random_key + "_" + cleaned_file_name

        new_file_path = os.path.join(
            knowledge_base_path, new_file_name
        )

        while os.path.exists(new_file_path):
            random_key = self.generate_random_string()
            new_file_name = random_key + "_" + cleaned_file_name
            new_file_path = os.path.join(
                knowledge_base_path, new_file_name
            )

        return new_file_path, cleaned_file_name

    def get_clean_file_name(self, orig_file_name: str):
        """Clean a file name by removing special characters except _, -, ., and space, then replace space with _"""
        # Allow alphanumeric, underscore, hyphen, dot, and space
        cleaned_file_name = re.sub(r'[^\w.\- ]', '', orig_file_name.strip())
        # Replace spaces with underscore
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

    async def generate_file_hash(self, file: UploadFile) -> str:
        """
        Generate a SHA-256 hash of the file content for deduplication.

        Args:
            file: The uploaded file

        Returns:
            str: Hexadecimal hash of the file content
        """
        try:
            # Reset file position to beginning
            await file.seek(0)

            # Create hash object
            file_hash = hashlib.sha256()

            # Read and update hash in chunks to handle large files
            chunk_size = 4096  # 4KB chunks
            while chunk := await file.read(chunk_size):
                file_hash.update(chunk)

            # Reset file position for subsequent operations
            await file.seek(0)

            # Return the hexadecimal digest
            return file_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error generating file hash: {e}")
            # Return empty string on error, which won't match any existing hash
            return ""

    async def read_file_and_hash(self, file_path: str) -> str:
        """
        Read a file from disk and generate its SHA-256 hash.

        Args:
            file_path: Path to the file

        Returns:
            str: Hexadecimal hash of the file content
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"File not found for hashing: {file_path}")
                return ""

            # Create hash object
            file_hash = hashlib.sha256()

            # Read and hash file in chunks
            async with aiofiles.open(file_path, 'rb') as f:
                chunk_size = 4096  # 4KB chunks
                while chunk := await f.read(chunk_size):
                    file_hash.update(chunk)

            return file_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error reading file and generating hash: {e}")
            return ""
