from ..LLMProviderInterface import LLMProviderInterface
from ..LLMEnums import CohereAPIv2Enum, CohereAPIv1Enum, DocumentTypeEnum
import cohere
from app.logging import get_logger
from typing import List, Union, Optional

class CohereProvider(LLMProviderInterface):

    def __init__(
        self,
        api_key: str,
        cohere_api_version: int = 1,
        default_input_max_characters: int = 1000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1,
        default_image_description_max_output_tokens: int = 150,
        default_image_description_temperature: float = 0.5
        ) -> None:

        self.api_key = api_key

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature
        self.default_image_description_max_output_tokens = default_image_description_max_output_tokens
        self.default_image_description_temperature = default_image_description_temperature

        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None
        self.enums = CohereAPIv2Enum if cohere_api_version == 2 else CohereAPIv1Enum
        self.cohere_api_version = cohere_api_version

        # Initialize async clients
        if cohere_api_version == 1:
            self.client = cohere.AsyncClient(api_key=self.api_key)
        else:
            self.client = cohere.AsyncClientV2(api_key=self.api_key)

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
            self.logger.error("Cohere client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for Cohere was not set")
            return None

        max_output_tokens = max_output_tokens if max_output_tokens else self.default_generation_max_output_tokens
        temperature = temperature if temperature else self.default_generation_temperature

        try:
            if self.cohere_api_version == 1:
                response = await self.client.chat(
                    model=self.generation_model_id,
                    chat_history=chat_history,
                    message=self.process_text(prompt),
                    temperature=temperature,
                    max_tokens=max_output_tokens
                )

                if not response or not response.text:
                    self.logger.error("Error while generating text with Cohere")
                    return None

                return response.text
            else:
                # Create a copy of chat history to avoid modifying the original
                chat_messages = chat_history.copy()
                chat_messages.append(
                    self.construct_prompt(prompt=prompt, role=CohereAPIv2Enum.USER.value)
                )

                response = await self.client.chat(
                    model=self.generation_model_id,
                    messages=chat_messages,
                    temperature=temperature,
                    max_tokens=max_output_tokens
                )

                if not response or not response.message or not response.message.content \
                    or len(response.message.content) == 0 or not response.message.content[0].text:
                    self.logger.error("Error while generating text with Cohere")
                    return None

                return response.message.content[0].text
        except Exception as e:
            self.logger.error(f"Error in text generation with Cohere: {str(e)}")
            return None

    async def embed_text(self, text: Union[str, List[str]], document_type: str = None, batch_size: int = 100):
        """
        Embed text asynchronously

        Args:
            text: Text or list of texts to embed
            document_type: Type of document (DOCUMENT or QUERY)
            batch_size: Maximum number of texts to process in a single API call

        Returns:
            List of embedding vectors or None if embedding fails
        """
        if not self.client:
            self.logger.error("Cohere client was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error("Embedding model for Cohere was not set")
            return None

        try:
            input_type = CohereAPIv2Enum.InputTypes.value.DOCUMENT.value
            texts_to_embed = []

            if document_type == DocumentTypeEnum.DOCUMENT.value:
                texts_to_embed = [self.process_text(t) for t in text]

            if document_type == DocumentTypeEnum.QUERY.value:
                input_type = CohereAPIv2Enum.InputTypes.value.QUERY.value
                texts_to_embed = [self.process_text(text)]

            # Cohere handles batching internally, so we don't need to implement it ourselves
            # The batch_size parameter is included for interface compatibility
            response = await self.client.embed(
                model=self.embedding_model_id,
                texts=texts_to_embed,
                input_type=input_type,
                embedding_types=['float']
            )

            if not response or not response.embeddings or not response.embeddings.float_:
                self.logger.error("Error while embedding text with Cohere")
                return None

            return [float_embedding for float_embedding in response.embeddings.float_]
        except Exception as e:
            self.logger.error(f"Error in text embedding with Cohere: {str(e)}")
            return None

    async def generate_image_description(self, image_bytes: bytes, prompt_text: str = "Describe this image in detail.", max_output_tokens: Optional[int] = None, temperature: Optional[float] = None) -> Optional[str]:
        """Generate image description asynchronously"""
        self.logger.error("Image description is not supported for Cohere")
        raise NotImplementedError("Image description is not supported for Cohere")