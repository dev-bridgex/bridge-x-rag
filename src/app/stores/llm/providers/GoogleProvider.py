from google import genai
from google.genai import types
from google.genai.types import ContentDict
from ..LLMProviderInterface import LLMProviderInterface
from ..LLMEnums import DocumentTypeEnum, GoogleEnum
from app.logging import get_logger
from typing import List, Union, Optional, Dict, Any
import io
from PIL import Image # For determining MIME type

# --- Google GenAI Provider Class ---

class GoogleProvider(LLMProviderInterface):

    # Map DocumentTypeEnum to Google GenAI task types
    _TASK_TYPE_MAP = {
        DocumentTypeEnum.DOCUMENT: "RETRIEVAL_DOCUMENT",
        DocumentTypeEnum.QUERY: "RETRIEVAL_QUERY",
        # Add other mappings if your DocumentTypeEnum expands
        # e.g., DocumentTypeEnum.SIMILARITY: "SEMANTIC_SIMILARITY"
    }
    _DEFAULT_EMBEDDING_TASK_TYPE = "RETRIEVAL_DOCUMENT" # Default if type is None


    def __init__(
        self,
        api_key: str,
        default_input_max_characters: int = 4000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.4,
        default_image_description_max_output_tokens: int = 150,
        default_image_description_temperature: float = 0.5
        ) -> None:

        self.api_key = api_key
        self.logger = get_logger(__name__) # Get logger early

        try:
            # Initialize the Google GenAI client with the API key
            self.client = genai.Client(api_key=self.api_key)
            self.logger.info("Google GenAI client initialized successfully")
            self._is_configured = True
        except Exception as e:
            self.logger.error(f"Failed to initialize Google GenAI client: {e}")
            self._is_configured = False
            raise

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature
        self.default_image_description_max_output_tokens = default_image_description_max_output_tokens
        self.default_image_description_temperature = default_image_description_temperature

        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None # Often determined by Google's model
        self.enums = GoogleEnum

    def _check_configuration(self) -> bool:
        """Checks if the Google GenAI client was initialized."""
        if not self._is_configured or not self.client:
            self.logger.error("Google GenAI client is not configured. Please check API key and initialization.")
            return False
        return True

    def set_generation_model(self, model_id: str) -> None:
        """Sets the model ID for text/image generation (e.g., 'gemini-1.5-flash-latest')."""
        self.generation_model_id = model_id
        self.logger.info(f"Google GenAI generation model set to: {model_id}")

    def set_embedding_model(self, model_id: str, embedding_size: Optional[int] = None) -> None:
        """Sets the model ID for text embeddings (e.g., 'text-embedding-004')."""
        self.embedding_model_id = model_id
        # Google's embedding size is usually fixed per model, but store if needed
        self.embedding_size = embedding_size
        self.logger.info(f"Google GenAI embedding model set to: {model_id} (Size: {embedding_size or 'Model Default'})")


    def process_text(self, text: str) -> str:
        """
        Processes text for the Google API:
        1. Truncates to the maximum character length
        2. Preserves newlines (unlike other providers that replace them with spaces)
        3. Strips leading/trailing whitespace
        """
        return text[: self.default_input_max_characters].strip()


    def construct_prompt(self, prompt: str, role: str) -> Dict[str, Any]:
        """
        Processes text and formats it into a Google GenAI Content dictionary
        based on the role.

        For system prompts, returns a special format that will be recognized
        by generate_text and handled appropriately.
        """
        processed_text = self.process_text(prompt)

        if role == self.enums.SYSTEM.value:
            # For system prompts, return a standard dictionary that will be
            # recognized by generate_text
            return {"role": self.enums.SYSTEM.value, "content": processed_text}

        elif role == self.enums.USER.value:
            # Format as Google's user message
            return {'role': self.enums.USER.value, 'parts': [{'text': processed_text}]}

        elif role == self.enums.ASSISTANT.value:
            # Format as Google's model message
            return {'role': self.enums.ASSISTANT.value, 'parts': [{'text': processed_text}]}

        else:
            self.logger.warning(f"Unknown or unsupported role '{role}' provided to construct_prompt. Treating as 'user'.")
            # Default to user role if mapping fails
            return {'role': self.enums.USER.value, 'parts': [{'text': processed_text}]}


    async def generate_text(self, prompt: str, chat_history: list = [], max_output_tokens: Optional[int] = None, temperature: Optional[float] = None):
        """Generates text using the configured Google generation model asynchronously.

        For Google provider, this method handles two main cases:
        1. Simple case: Just a user query with optional system instructions (no chat history)
        2. Full chat history case: Processing complete conversation history
        """

        if not self._check_configuration(): return None
        if not self.generation_model_id:
            self.logger.error("Generation model for Google GenAI was not set.")
            return None

        resolved_max_output_tokens = max_output_tokens if max_output_tokens is not None else self.default_generation_max_output_tokens
        resolved_temperature = temperature if temperature is not None else self.default_generation_temperature

        # --- History and System Prompt Processing ---
        google_api_history: List[ContentDict] = []
        system_instruction_text: Optional[str] = None

        # Process the incoming chat_history
        for message in chat_history:
            if not isinstance(message, dict):
                self.logger.warning(f"Skipping unexpected item type in chat_history: {type(message)}")
                continue

            role = message.get("role")
            content = message.get("content")

            if content is None:
                self.logger.warning(f"Skipping message in history due to missing content: {message}")
                continue

            # Special handling for system messages
            if role == self.enums.SYSTEM.value:
                # Use the first system message as system_instruction
                if system_instruction_text is None:
                    system_instruction_text = content
                    self.logger.debug("Using first system message from history as system_instruction.")
                else:
                    self.logger.warning("Multiple system messages found in history. Only the first one is used as system_instruction.")
                # Don't add system messages to the regular history
                continue

            # For non-system messages, format and add to history
            formatted_message = self.construct_prompt(prompt=content, role=role)
            google_api_history.append(formatted_message)

        # Process and add the current user prompt (if provided)
        if prompt:
            current_user_message = self.construct_prompt(prompt=prompt, role=self.enums.USER.value)
            google_api_history.append(current_user_message)

        # Handle the simple case: Just a user query with system instructions
        # This is the case where we don't have chat history, just the user query and system instructions
        if len(google_api_history) == 1 and prompt and system_instruction_text:
            self.logger.debug("Using simplified format: just user query with system instructions")
            # We already have the user query in google_api_history and system_instruction_text is set

        # Safety check: Ensure there's something to send
        if not google_api_history and not (system_instruction_text and prompt):
            self.logger.error("No valid conversation history or prompt to send to Google GenAI.")
            return None

        # Log what we're sending to help with debugging
        self.logger.debug(f"Sending to Google GenAI: system_instruction={system_instruction_text is not None}, history_length={len(google_api_history)}")
        # --- End History Processing ---
        try:
            # Generate content using the async client
            response = await self.client.aio.models.generate_content(
                model=self.generation_model_id,
                contents=google_api_history,
                config=types.GenerateContentConfig(
                    max_output_tokens=resolved_max_output_tokens,
                    temperature=resolved_temperature,
                    system_instruction=system_instruction_text
                )
            )

            # Extract the text from the response
            if response and hasattr(response, 'text'):
                self.logger.info(f"Successfully generated text ({len(response.text)} chars).")
                return response.text
            else:
                self.logger.error("Error while generating text with Google GenAI: Empty or invalid response")
                return None

        except Exception as e:
            # Log detailed error information
            error_msg = str(e)
            self.logger.error(f"Error generating text with Google GenAI: {error_msg}")

            # Try to provide more context about what might have gone wrong
            if "validation errors" in error_msg.lower():
                self.logger.error("This appears to be a validation error with the request format. Check the format of the prompt and chat history.")
                # Log the first message to help with debugging
                if google_api_history:
                    first_msg = google_api_history[0]
                    self.logger.error(f"First message format: {type(first_msg)}, keys: {first_msg.keys() if isinstance(first_msg, dict) else 'N/A'}")

            return None


    def _batch_texts(self, texts: List[str], batch_size: int = 100) -> List[List[str]]:
        """
        Split a list of texts into batches of specified size.

        Args:
            texts: List of texts to batch
            batch_size: Maximum size of each batch (default: 100 for Google's API limit)

        Returns:
            List of batches, where each batch is a list of texts
        """
        return [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]

    async def embed_text(self,
                   text: Union[str, List[str]],
                   document_type: Optional[DocumentTypeEnum] = None, # Use DocumentTypeEnum
                   batch_size: int = 100
                   ) -> Optional[List[List[float]]]:
        """
        Generates embeddings using the configured Google embedding model asynchronously.

        Handles batching for large input lists to comply with Google's 100-item batch limit.
        """
        if not self._check_configuration(): return None
        if not self.embedding_model_id:
            self.logger.error("Embedding model for Google GenAI was not set.")
            return None

        try:
            # Map the DocumentTypeEnum to Google's task_type string
            task_type = self._TASK_TYPE_MAP.get(document_type, self._DEFAULT_EMBEDDING_TASK_TYPE)
            self.logger.debug(f"Using embedding task type: {task_type} for model {self.embedding_model_id}")

            if isinstance(text, str):
                text_list = [text] # API expects a list
            else:
                text_list = text

            # Process texts (e.g., truncate) before sending
            processed_texts = [self.process_text(t) for t in text_list]
            if not processed_texts:
                 self.logger.warning("Input text list for embedding is empty after processing.")
                 return [] # Return empty list for empty input

            # Check if we need to batch the requests
            if len(processed_texts) > batch_size:
                self.logger.info(f"Batching {len(processed_texts)} texts into batches of {batch_size} for Google GenAI embedding")
                batches = self._batch_texts(processed_texts, batch_size)

                # Process each batch and combine results
                all_embeddings = []
                for i, batch in enumerate(batches):
                    self.logger.debug(f"Processing batch {i+1}/{len(batches)} with {len(batch)} texts")

                    # Generate embeddings for this batch
                    batch_response = await self.client.aio.models.embed_content(
                        model=self.embedding_model_id,
                        contents=batch,
                        config=types.EmbedContentConfig(
                            task_type=task_type,
                            output_dimensionality=self.embedding_size
                        )
                    )

                    # Extract embeddings from the batch response
                    if batch_response and hasattr(batch_response, 'embeddings'):
                        batch_embeddings = [embedding.values for embedding in batch_response.embeddings]
                        all_embeddings.extend(batch_embeddings)
                        self.logger.debug(f"Successfully generated {len(batch_embeddings)} embeddings in batch {i+1}")
                    else:
                        self.logger.error(f"Error in batch {i+1}: Empty or invalid response")
                        return None

                self.logger.info(f"Successfully generated {len(all_embeddings)} total embeddings across {len(batches)} batches")
                return all_embeddings
            else:
                # For small requests, process directly without batching
                response = await self.client.aio.models.embed_content(
                    model=self.embedding_model_id,
                    contents=processed_texts,
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=self.embedding_size
                    )
                )

                # Extract embeddings from the response
                if response and hasattr(response, 'embeddings'):
                    embeddings = [embedding.values for embedding in response.embeddings]
                    self.logger.info(f"Successfully generated {len(embeddings)} embeddings.")
                    return embeddings
                else:
                    self.logger.error("Error while embedding text with Google GenAI: Empty or invalid response")
                    return None

        except Exception as e:
            self.logger.error(f"Error embedding text with Google GenAI: {e}")
            return None

    # --- Image Handling Methods ---

    def _get_image_mime_type(self, image_bytes: bytes) -> Optional[str]:
        """Attempts to determine the MIME type of the image bytes using PIL."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                format_upper = img.format.upper() if img.format else None
                if format_upper:
                    mime_type = Image.MIME.get(format_upper)
                    # Gemini supported types: PNG, JPEG, WEBP, HEIC, HEIF
                    supported_mimes = ["image/png", "image/jpeg", "image/webp", "image/heic", "image/heif"]
                    if mime_type in supported_mimes:
                        self.logger.debug(f"Detected image MIME type: {mime_type}")
                        return mime_type
                    else:
                        # Log warning but still return type; API might support more types than documented
                        self.logger.warning(f"Detected MIME type '{mime_type}' from format '{format_upper}' which might not be explicitly listed as supported by Gemini. Proceeding.")
                        return mime_type
                else:
                    self.logger.warning("Could not determine image format using PIL.")
                    return None
        except ImportError:
             self.logger.error("Pillow library not installed. Cannot determine image MIME type. Please install with 'pip install Pillow'")
             return None
        except Exception as e:
            # Catch PIL-specific errors or general issues opening the image
            self.logger.error(f"Error determining image MIME type with PIL: {e}", exc_info=False) # exc_info=False to avoid long traceback for common image errors
            return None

    async def generate_image_description(
        self,
        image_bytes: bytes,
        prompt_text: str = "Describe this image in detail.",
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Optional[str]:
        """
        Generates a text description from image bytes using a Google GenAI vision model asynchronously.
        """
        if not self._check_configuration(): return None
        if not self.generation_model_id:
            self.logger.error("Generation model for Google GenAI was not set (required for image generation).")
            return None
        # Add check: Maybe warn if model name doesn't contain 'vision' or 'gemini'?
        if 'gemini' not in self.generation_model_id and 'vision' not in self.generation_model_id:
             self.logger.warning(f"Model '{self.generation_model_id}' might not be vision-capable.")

        try:
            # 1. Determine MIME Type
            mime_type = self._get_image_mime_type(image_bytes)
            if not mime_type:
                self.logger.error("Failed to determine image MIME type. Cannot proceed with Google GenAI image description.")
                return None

            # 2. Set up parameters
            resolved_max_output_tokens = max_output_tokens if max_output_tokens is not None else self.default_image_description_max_output_tokens
            resolved_temperature = temperature if temperature is not None else self.default_image_description_temperature

            # 3. Prepare system instruction and prompt
            system_instruction = """You are an expert at analyzing images and extracting their conceptual meaning.
When describing images, focus on:
1. The main concept or idea the image is trying to convey
2. Any educational or informational purpose the image serves
3. How the image relates to the subject matter of the document
4. The relationships between elements in the image and what they represent
5. The practical application or real-world relevance of what's shown

Provide descriptions that explain both what the image shows AND what it means conceptually.
Your descriptions should be useful for answering questions about the concepts depicted in the image."""
            full_prompt = f"{system_instruction}\n\n{prompt_text.strip()}"

            # 4. Create image part
            # The new SDK will handle the image part differently
            from PIL import Image as PILImage
            image = PILImage.open(io.BytesIO(image_bytes))

            # 5. Generate content using the async client
            response = await self.client.aio.models.generate_content(
                model=self.generation_model_id,
                contents=[full_prompt, image],
                config=types.GenerateContentConfig(
                    max_output_tokens=resolved_max_output_tokens,
                    temperature=resolved_temperature
                )
            )

            # 6. Extract the text from the response
            if response and hasattr(response, 'text'):
                self.logger.info(f"Successfully generated image description ({len(response.text)} chars).")
                return response.text
            else:
                self.logger.error("Error while generating image description with Google GenAI: Empty or invalid response")
                return None

        except Exception as e:
            self.logger.error(f"Error generating image description with Google GenAI: {e}")
            return None
