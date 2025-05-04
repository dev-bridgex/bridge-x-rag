from .BaseController import BaseController
from app.models import FileTypesEnum

from app.stores.llm import LLMProviderInterface
from app.stores.llm.templates.template_parser import TemplateParser

from typing import List, Dict, Any, Tuple, Optional
from app.logging import get_logger
from dataclasses import dataclass
import os
import pymupdf
import re
from base64 import b64encode

import time
import asyncio
import random
from functools import partial


logger = get_logger(__name__)

@dataclass
class Document:
    """
    Document class for storing text chunks and their metadata.

    Common metadata fields include:
    - content_id: Unique identifier for the chunk content
    - document_name: Name of the document
    - source_path: Path to the source document
    - page_num: Page number in the document
    - content_type: Type of content (text or image)

    For images, additional metadata may include:
    - image_description: AI-generated description of the image
    - surrounding_text: Text surrounding the image for context

    All metadata is stored directly in the metadata dictionary and passed to the DataChunk model.
    """
    page_content: str
    metadata: dict

class ProcessingController(BaseController):

    def __init__(self,
                 generation_client: LLMProviderInterface,
                 embedding_client: LLMProviderInterface,
                 template_parser: TemplateParser = None) -> None:
        super().__init__()

        self.generation_client: LLMProviderInterface = generation_client
        self.embedding_client: LLMProviderInterface = embedding_client
        self.template_parser = template_parser or TemplateParser()

        # Log the configured number of workers for image processing
        logger.info(f"PDF image processing configured with {self.app_settings.PDF_IMAGE_PROCESSING_MAX_WORKERS} max workers")

    def get_file_extension(self, file_name: str) -> str:
        """Get the extension of a file"""
        return os.path.splitext(file_name)[-1]

    def get_file_path(self, file_name: str, knowledge_base_path: str) -> str:
        """Get the full path to a file in a knowledge_base directory"""
        return os.path.join(knowledge_base_path, file_name)

    def is_supported_file_type(self, file_name: str) -> bool:
        """Check if the file type is supported for processing

        Parameters:
        - file_name (str): The name of the file

        Returns:
        - bool: True if the file type is supported, False otherwise
        """
        file_extension = self.get_file_extension(file_name=file_name)
        return file_extension in [FileTypesEnum.TXT.value, FileTypesEnum.PDF.value]

    async def get_file_content(self, file_name: str, file_path: str, chunk_size: int = 500, max_concurrent: Optional[int] = None) -> List[Document]:
        """
        Load the content of a file as a list of documents using direct PyMuPDF processing.

        Parameters:
        - file_name (str): The name of the file
        - file_path (str): The full path to the file
        - chunk_size (int): The maximum size of each chunk in characters
        - max_concurrent (int): Maximum number of concurrent tasks for image processing in PDFs

        Returns:
        - List[Document]: A list of Document objects containing the file content
        """
        file_extension = self.get_file_extension(file_name=file_name)

        if file_extension == FileTypesEnum.TXT.value:
            return await self.process_text(file_path=file_path, chunk_size=chunk_size)

        if file_extension == FileTypesEnum.PDF.value:
            # Use the configured max_concurrent or fall back to the app setting
            concurrent_limit = max_concurrent if max_concurrent is not None else self.app_settings.PDF_IMAGE_PROCESSING_MAX_WORKERS
            return await self.process_pdf(pdf_path=file_path, max_chunk_size = chunk_size, max_concurrent=concurrent_limit)

        logger.error(f"No processor available for file: {file_name} with extension {file_extension}")
        return None


    async def process_pdf(self, pdf_path, max_chunk_size: int = 500, max_concurrent: int = 10):
        """
        Processes a PDF file by extracting text and images using PyMuPDF directly.

        Parameters:
        - pdf_path (str): The file path of the PDF to process.
        - max_concurrent (int): Maximum number of concurrent async tasks for image processing.

        Returns:
        - List[Document]: A list of Document objects containing text and image chunks.
        """
        start_time = time.time()
        logger.info(f"Processing PDF: {pdf_path}")
        doc = pymupdf.open(pdf_path)

        # Extract the document name from the path
        # If the file was saved with a random prefix (12 chars + underscore), remove it
        basename = os.path.basename(pdf_path)
        if len(basename) > 13 and basename[12] == '_':
            document_name = basename[13:]  # Remove the random prefix (12 chars + underscore)
        else:
            document_name = basename

        logger.info(f"Processing PDF with document name: {document_name}")

        # Extract and process text with improved chunking
        text_start_time = time.time()
        processed_text_chunks = []

        extracted_chunks = self._extract_text_with_cleaning(doc, max_chunk_size=max_chunk_size)
        for idx, chunk_data in enumerate(extracted_chunks):
            # Create a new Document instance with the required fields
            chunk = Document(
                page_content=chunk_data["text"],
                metadata={
                    "content_id": f"text_{document_name}_{chunk_data['page']}_{idx}",
                    "document_name": document_name,
                    "page_num": chunk_data["page"],
                    "content_type": "text",
                    "source_path": pdf_path
                }
            )
            processed_text_chunks.append(chunk)

        text_processing_time = time.time() - text_start_time
        logger.info(f"Text processing completed in {text_processing_time:.2f} seconds, extracted {len(processed_text_chunks)} text chunks")

        # Prepare image data for async processing
        image_start_time = time.time()
        image_data_list = []

        # First, collect all image data
        for page_num, page in enumerate(doc):
            # Extract and clean full page text
            full_page_text = page.get_text("text")
            cleaned_page_text = self._clean_text(full_page_text)

            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                # Extract surrounding text for context
                surrounding_text = self._extract_surrounding_text(
                    cleaned_page_text, position=img_index
                )

                # Prepare data for async processing
                image_data = {
                    'image_bytes': image_bytes,
                    'surrounding_text': surrounding_text,
                    'document_name': document_name,
                    'page_num': page_num,
                    'img_index': img_index,
                    'source_path': pdf_path
                }

                image_data_list.append(image_data)

        # Process images asynchronously
        processed_image_chunks = []
        total_images = len(image_data_list)

        if total_images > 0:
            logger.info(f"Starting processing of {total_images} images with max {max_concurrent} concurrent tasks")

            # Create a semaphore to limit concurrency
            semaphore = asyncio.Semaphore(max_concurrent)

            # Add a rate limiter to ensure we don't exceed provider rate limits
            # Use the configured rate limit delay from application settings
            rate_limit_delay = self.app_settings.API_RATE_LIMIT_DELAY
            last_request_time = 0

            async def process_with_rate_limiting(image_data):
                nonlocal last_request_time
                async with semaphore:
                    # Apply rate limiting
                    current_time = time.time()
                    time_since_last_request = current_time - last_request_time
                    if time_since_last_request < rate_limit_delay:
                        delay_needed = rate_limit_delay - time_since_last_request
                        await asyncio.sleep(delay_needed)

                    # Update the last request time
                    last_request_time = time.time()

                    # Process the image
                    return await self._process_single_image(image_data)

            # Create tasks for all images with rate limiting
            tasks = [process_with_rate_limiting(image_data) for image_data in image_data_list]

            # Process images in batches to show progress
            completed = 0
            successful = 0
            for future in asyncio.as_completed(tasks):
                try:
                    chunk = await future
                    if chunk is not None:  # Only add non-None chunks
                        processed_image_chunks.append(chunk)
                        successful += 1

                    # Log progress periodically
                    completed += 1
                    if completed % 5 == 0 or completed == total_images:
                        logger.info(f"Processed {completed}/{total_images} images ({(completed/total_images)*100:.1f}%), {successful} successful")

                except Exception as e:
                    logger.error(f"Error in image processing: {str(e)}")

        image_processing_time = time.time() - image_start_time
        logger.info(f"Image processing completed in {image_processing_time:.2f} seconds, processed {len(processed_image_chunks)} images")

        # Combine text and image chunks
        all_chunks = processed_text_chunks + processed_image_chunks

        # Close the document
        doc.close()

        total_processing_time = time.time() - start_time
        logger.info(f"Processed PDF {pdf_path}: {len(processed_text_chunks)} text chunks, {len(processed_image_chunks)} image chunks in {total_processing_time:.2f} seconds")
        return all_chunks

    async def process_text(self, file_path, chunk_size=500):
        """
        Processes a text file using PyMuPDF and chunks the content.

        Parameters:
        - file_path (str): The file path of the text file to process.
        - chunk_size (int): The maximum size of each chunk in characters.

        Returns:
        - List[Document]: A list of Document objects containing text chunks.
        """
        logger.info(f"Processing text file: {file_path}")

        # Extract the document name from the path
        # If the file was saved with a random prefix (12 chars + underscore), remove it
        basename = os.path.basename(file_path)
        if len(basename) > 13 and basename[12] == '_':
            document_name = basename[13:]  # Remove the random prefix (12 chars + underscore)
        else:
            document_name = basename

        logger.info(f"Processing text file with document name: {document_name}")

        try:
            # Open the text file with PyMuPDF
            doc = pymupdf.open(file_path)

            # Extract text content
            text_content = ""
            for page in doc:
                text_content += page.get_text("text")

            # Close the document
            doc.close()

            # Clean the text
            cleaned_text = self._clean_text(text_content)

            # Chunk the text using sentence-aware chunking
            text_chunks = self._sentence_aware_chunking(cleaned_text, max_chunk_size=chunk_size)

            # Create Document objects for each chunk
            processed_chunks = []
            for idx, chunk_text in enumerate(text_chunks):
                if len(chunk_text.strip()) > 0:  # Skip empty chunks
                    chunk = Document(
                        page_content=chunk_text,
                        metadata={
                            "content_id": f"text_{document_name}_{idx}",
                            "document_name": document_name,
                            "page_num": 1,  # Text files are considered single page
                            "content_type": "text",
                            "source_path": file_path
                        }
                    )
                    processed_chunks.append(chunk)

            logger.info(f"Processed text file {file_path}: {len(processed_chunks)} chunks")
            return processed_chunks

        except Exception as e:
            logger.error(f"Error processing text file {file_path}: {str(e)}")
            return []

    async def _process_single_image(self, image_data):
        """
        Process a single image to generate its description and create a Document object.
        Returns None if processing fails after all retries, so no error document is created.

        Parameters:
        - image_data: A dictionary containing all necessary data to process an image
          {
            'image_bytes': bytes,
            'surrounding_text': str,
            'document_name': str,
            'page_num': int,
            'img_index': int,
            'source_path': str
          }

        Returns:
        - Document: A Document object containing the image description and metadata, or None if processing fails
        """
        max_retries = 5  # Maximum number of retry attempts

        # Extract data from the input dictionary
        image_bytes = image_data['image_bytes']
        surrounding_text = image_data['surrounding_text']
        document_name = image_data['document_name']
        page_num = image_data['page_num']
        img_index = image_data['img_index']
        source_path = image_data['source_path']

        for attempt in range(max_retries):
            try:
                # Generate image description asynchronously
                start_time = time.time()

                # Log that we're attempting to process this image
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt}/{max_retries-1} for image {document_name}_{page_num}_{img_index}")

                image_description = await self.generation_client.generate_image_description(
                    image_bytes=image_bytes,
                    prompt_text=(
                        "Analyze this image and explain its conceptual meaning in the context of the document. "
                        "Your description should: "
                        "1. Clearly identify what concept or principle the image is illustrating "
                        "2. Explain how the visual elements represent specific concepts or relationships "
                        "3. Provide enough detail that someone could answer questions about the concept based on your description "
                        "4. Connect the image to the subject matter of the document "
                        "5. Focus on the educational or informational purpose of the image "
                        "\n\n"
                        f"Context from surrounding text: {surrounding_text}"
                    )
                )

                # If we got here, the API call succeeded
                processing_time = time.time() - start_time
                logger.debug(f"Image description generation took {processing_time:.2f} seconds for image {document_name}_{page_num}_{img_index}")

                # Only create a document if we got a valid description
                if image_description:
                    # Combine description with surrounding text
                    combined_description = f"Image Description: {image_description}\nContext: {surrounding_text}"

                    # Create a Document instance with the required fields
                    chunk = Document(
                        page_content=combined_description,
                        metadata={
                            "content_id": f"image_{document_name}_{page_num}_{img_index}",
                            "document_name": document_name,
                            "page_num": page_num + 1,
                            "content_type": "image",
                            "source_path": source_path,
                        }
                    )

                    return chunk
                else:
                    logger.warning(f"Empty image description returned for {document_name}_{page_num}_{img_index}")
                    return None

            except Exception as e:
                error_str = str(e)

                # Generic detection of rate limit and service availability errors across providers
                # Common HTTP status codes and error messages
                is_rate_limit = any(marker in error_str for marker in ["429", "RESOURCE_EXHAUSTED", "rate limit", "quota exceeded", "too many requests"])
                is_service_unavailable = any(marker in error_str for marker in ["503", "UNAVAILABLE", "service unavailable", "overloaded", "temporarily unavailable"])

                # If this is the last attempt or not a retryable error, log and return None
                if attempt == max_retries - 1 or (not is_rate_limit and not is_service_unavailable):
                    logger.error(f"Failed to process image {document_name}_{page_num}_{img_index} after {attempt+1} attempts: {error_str}")
                    return None

                # Default to a fixed delay of 5 seconds for all retryable errors
                delay = 5.0

                # Try to extract the suggested retry delay from provider responses if available
                # This works for Google's API which includes 'retryDelay' in error messages
                if "retryDelay" in error_str:
                    try:
                        import re
                        retry_delay_match = re.search(r"'retryDelay':\s*'(\d+)s'", error_str)
                        if retry_delay_match:
                            suggested_delay = float(retry_delay_match.group(1))
                            # Use the suggested delay, but cap it at 20 seconds to avoid very long waits
                            delay = min(suggested_delay, 20.0)
                            logger.info(f"Using provider's suggested retry delay of {delay}s")
                    except Exception as extract_error:
                        logger.warning(f"Failed to extract retry delay from response: {extract_error}")

                # Log the appropriate error message
                if is_rate_limit:
                    logger.warning(f"Rate limit hit for image {document_name}_{page_num}_{img_index}. Retrying in {delay:.1f}s (attempt {attempt+1}/{max_retries-1})")
                else:
                    logger.warning(f"Service unavailable for image {document_name}_{page_num}_{img_index}. Retrying in {delay:.1f}s (attempt {attempt+1}/{max_retries-1})")

                await asyncio.sleep(delay)

        # This should never be reached due to the return in the last iteration of the loop,
        # but added as a safeguard
        return None


    def _extract_text_with_cleaning(self, doc, max_chunk_size=500):
        """
        Extracts and cleans text from a PDF, removing repetitive headers/footers.

        Parameters:
        - doc (pymupdf.Document): A PyMuPDF document object.

        Returns:
        - list: A list of dictionaries with "page" (page number) and "text" (cleaned chunk).

        Process:
        1. Identifies repeating headers/footers by analyzing all pages.
        2. Removes identified headers/footers from each page.
        3. Splits the remaining text into sentence-aware chunks.
        4. Returns the cleaned and chunked text with metadata.
        """
        all_chunks = []
        header_candidates = []

        # Identify potential headers/footers
        for page in doc:
            text_lines = page.get_text("text").splitlines()
            if len(text_lines) > 2:
                header_candidates.append(text_lines[0])  # Add first line as header
                header_candidates.append(text_lines[-1])  # Add last line as footer

        # Find common headers/footers across pages
        common_headers = {
            k
            for k, _ in dict.fromkeys(header_candidates).items()
            if header_candidates.count(k) > 2
        }

        # Process each page
        for page_num, page in enumerate(doc):
            text_lines = page.get_text("text").splitlines()
            clean_lines = [line for line in text_lines if line not in common_headers]
            cleaned_text = self._clean_text(" ".join(clean_lines))
            chunks = self._sentence_aware_chunking(cleaned_text, max_chunk_size=max_chunk_size)

            #

            logger.debug(f"Page {page_num + 1} has {len(chunks)} chunks")

            # Store chunks with metadata
            for chunk in chunks:
                if len(chunk) > 50:  # Only include meaningful chunks
                    all_chunks.append({"page": page_num + 1, "text": chunk})
        return all_chunks

    def _clean_text(self, text):
        """
        Cleans raw text by removing unnecessary elements.

        Parameters:
        - text (str): The raw text to clean.

        Returns:
        - str: The cleaned and normalized text.

        Cleaning Steps:
        - Removes URLs, email addresses, and phone numbers.
        - Replaces multiple spaces with a single space.
        """
        text = re.sub(r"https?://\S+|www\.\S+", "", text)  # Remove URLs
        text = re.sub(r"\S+@\S+\.\S+", "", text)  # Remove emails
        text = re.sub(r"\+?\d[\d\s\-\(\)]{8,}\d", "", text)  # Remove phone numbers
        text = re.sub(r"\s{2,}", " ", text)  # Replace multiple spaces
        return text.strip()


    def _sentence_aware_chunking(self, text, max_chunk_size=500):
        """
        Splits text into manageable chunks, preserving sentence boundaries.

        Parameters:
        - text (str): The input text to chunk.
        - max_chunk_size (int): Maximum size of each chunk (in characters).
        - overlap (int): Number of overlapping characters between consecutive chunks.

        Returns:
        - list: A list of text chunks.

        Notes:
        - Ensures sentences are not split across chunks for better context retention.
        - Useful for generating embeddings and storing in CrateDB.
        """
        sentences = re.split(r"(?<=[.!?]) +", text)
        chunks = []
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_chunk_size:
                current_chunk += " " + sentence
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks


    def _extract_surrounding_text(self, page_text, position=0, max_length=300):
        """
        Extracts nearby text to provide context for an image.

        Parameters:
        - page_text (str): The full text of the page containing the image.
        - position (int): Approximate index of the image on the page.
        - max_length (int): Maximum number of characters to include in the snippet.

        Returns:
        - str: A snippet of text surrounding the image's position.

        Notes:
        - Captures sentences around the image's position for better contextualization.
        """
        lines = re.split(r"(?<=[.!?])\s+", page_text)  # Split into sentences
        start = max(0, position - 1)
        end = min(len(lines), position + 2)  # Capture sentences around the position

        # Combine and trim to max_length
        surrounding_snippet = " ".join(lines[start:end])
        return surrounding_snippet[:max_length].strip()


    def _encode_image(self, image_bytes):
        return b64encode(image_bytes).decode("utf-8")

    def enhance_file_chunks(self, file_chunks: List[Document], file_name: str, **_) -> List[Document]:
        """
        Enhance file chunks with additional metadata or processing if needed.

        Parameters:
        - file_chunks (List[Document]): The chunks already created by get_file_content
        - file_name (str): The name of the file
        - **_: Additional parameters for future enhancements (currently unused)

        Returns:
        - List[Document]: A list of Document objects with enhanced metadata
        """
        if not file_chunks:
            logger.error(f"No chunks to enhance for file: {file_name}")
            return None

        # For now, we just return the chunks as is
        # The document_name and content_id are already cleaned in process_pdf and process_text methods
        # In the future, we might want to add more processing here
        return file_chunks

