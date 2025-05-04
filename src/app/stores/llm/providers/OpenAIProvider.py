from ..LLMProviderInterface import LLMProviderInterface
from ..LLMEnums import OpenAIEnum
from openai import AsyncOpenAI
from app.logging import get_logger
from typing import List, Union, Optional
import base64


class OpenAIProvider(LLMProviderInterface):

    def __init__(
        self,
        api_key: str,
        api_url: str = None,
        default_input_max_characters: int = 1000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1,
        default_image_description_max_output_tokens: int = 150,
        default_image_description_temperature: float = 0.5
        ) -> None:

        self.api_key = api_key
        self.api_url = api_url

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature
        self.default_image_description_max_output_tokens = default_image_description_max_output_tokens
        self.default_image_description_temperature = default_image_description_temperature

        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None
        self.enums = OpenAIEnum

        # Initialize async client
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url = self.api_url if self.api_url and len(self.api_url) else None
        )

        self.logger = get_logger(__name__)


    def set_generation_model(self, model_id: str) -> None:
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int) -> None:
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str) -> str:
        return text[: self.default_input_max_characters].replace("\n", " ").strip()

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": self.process_text(prompt)
        }

    async def generate_text(self, prompt: str, chat_history: list = [], max_output_tokens: int = None, temperature: float = None):
        """Generate text from a prompt asynchronously"""
        if not self.client:
            self.logger.error("OpenAI client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for OpenAI was not set")
            return None

        max_output_tokens = max_output_tokens if max_output_tokens else self.default_generation_max_output_tokens
        temperature = temperature if temperature else self.default_generation_temperature

        # Create a copy of chat history to avoid modifying the original
        chat_messages = chat_history.copy()
        chat_messages.append(
            self.construct_prompt(prompt=prompt, role=OpenAIEnum.USER.value)
        )

        try:
            response = await self.client.chat.completions.create(
                model = self.generation_model_id,
                messages = chat_messages,
                max_tokens = max_output_tokens,
                temperature = temperature
            )

            if not response or not response.choices or len(response.choices) == 0 or not response.choices[0].message:
                self.logger.error("Error while generating text with OpenAI")
                return None

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Error in text generation with OpenAI: {str(e)}")
            return None

    async def embed_text(self, text: Union[str, List[str]], document_type: str = None):
        """Embed text asynchronously"""
        if not self.client:
            self.logger.error("OpenAI client was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error("Embedding model for OpenAI was not set")
            return None

        try:
            response = await self.client.embeddings.create(
                model = self.embedding_model_id,
                input = text
            )

            if not response or not response.data or len(response.data) == 0 or not response.data[0].embedding:
                self.logger.error("Error while embedding text with OpenAI")
                return None

            return [ rec.embedding for rec in response.data ]
        except Exception as e:
            self.logger.error(f"Error in text embedding with OpenAI: {str(e)}")
            return None

    async def generate_image_description(
        self,
        image_bytes: bytes,
        prompt_text: str = "Describe this image in detail.",
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Optional[str]:
        """
        Generate text description from an image using OpenAI's vision model

        Args:
            prompt_text: Text prompt describing what to generate about the image
            image_bytes: Raw image bytes
            max_output_tokens: Maximum number of tokens to generate
            temperature: Temperature for generation

        Returns:
            Generated text description or None if generation fails
        """
        try:
            if not self.client:
                self.logger.error("OpenAI client was not set")
                return None

            # Set parameters
            max_output_tokens = max_output_tokens if max_output_tokens else self.default_image_description_max_output_tokens
            temperature = temperature if temperature else self.default_image_description_temperature

            # Convert image to base64
            encoded_image = base64.b64encode(image_bytes).decode('utf-8')

            system_instruction: str = """You are an expert at analyzing images and extracting their conceptual meaning.
When describing images, focus on:
1. The main concept or idea the image is trying to convey
2. Any educational or informational purpose the image serves
3. How the image relates to the subject matter of the document
4. The relationships between elements in the image and what they represent
5. The practical application or real-world relevance of what's shown

Provide descriptions that explain both what the image shows AND what it means conceptually.
Your descriptions should be useful for answering questions about the concepts depicted in the image."""

            # Create the message with text and image
            messages=[
                {
                    "role": "system",
                    "content": system_instruction,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt_text.strip()
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{encoded_image}"
                            },
                        },
                    ],
                },
            ]

            # Generate response
            response = await self.client.chat.completions.create(
                model=self.generation_model_id,
                messages=messages,
                max_tokens=max_output_tokens,
                temperature=temperature
            )

            if not response or not response.choices or len(response.choices) == 0 or not response.choices[0].message:
                self.logger.error("Error while generating image description with OpenAI")
                return None

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Error generating image description with OpenAI: {e}")
            return None