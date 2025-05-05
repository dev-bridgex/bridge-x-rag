from abc import ABC, abstractmethod
from typing import List, Union, Optional, Dict

class LLMProviderInterface(ABC):

    @abstractmethod
    def set_generation_model(self, model_id: str) -> None:
        pass

    @abstractmethod
    def set_embedding_model(self, model_id: str, embedding_size: int) -> None:
        pass

    @abstractmethod
    async def generate_text(self, prompt: str, chat_history: list = [], max_output_tokens: int = None, temperature: float = None) -> Optional[str]:
        """Generate text from a prompt asynchronously"""
        pass

    @abstractmethod
    async def embed_text(self, text: Union[str, List[str]], document_type: str = None, batch_size: int = 100) -> Optional[List[List[float]]]:
        """
        Embed text asynchronously

        Args:
            text: Text or list of texts to embed
            document_type: Type of document (e.g., DOCUMENT, QUERY)
            batch_size: Maximum number of texts to process in a single API call

        Returns:
            List of embedding vectors or None if embedding fails
        """
        pass

    @abstractmethod
    def construct_prompt(self, prompt: str, role: str) -> Dict[str, str]:
        pass

    @abstractmethod
    async def generate_image_description(self, image_bytes: bytes, prompt_text: str = "Describe this image in detail.", max_output_tokens: Optional[int] = None, temperature: Optional[float] = None) -> Optional[str]:
        """Generate image description asynchronously"""
        pass