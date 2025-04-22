from ..LLMProviderInterface import LLMProviderInterface
from ..LLMEnums import CohereAPIv2Enum, DocumentTypeEnum
import cohere
from cohere.v2.client import V2Client
from app.logging import get_logger


class CohereProvider(LLMProviderInterface):
    
    def __init__(
        self, 
        api_key: str,
        cohere_api_version: int = 1,
        default_input_max_characters: int = 1000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1
        ) -> None:
        
        self.api_key = api_key
        
        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature
        
        self.generation_model_id = None
        
        self.embedding_model_id = None
        self.embedding_size = None
        
        self.cohere_api_version = cohere_api_version
        
        self.client_v1 = cohere.Client(api_key=self.api_key) if cohere_api_version == 1 else None
        self.client_v2 = cohere.ClientV2(api_key=self.api_key) if cohere_api_version == 2 else None
            
        self.logger = get_logger(__name__)
        
    
    def set_generation_model(self, model_id: str) -> None:
        self.generation_model_id = model_id
     
    def set_embedding_model(self, model_id: str, embedding_size: int) -> None:
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size
        
    def process_text(self, text: str) -> str:
        return text[: self.default_input_max_characters].strip()
    
    def construct_pompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": self.process_text(prompt)
        }
        
    def generate_text(self, prompt: str, chat_history: list = [], max_output_tokens: int = None, temperature: float = None):
        
        if not self.client_v1 or not self.client_v2:
            self.logger.error("Cohere client was not set")
            return None
        
        if not self.generation_model_id:
            self.logger.error("Generation model for Cohere was not set")
            return None
        
        max_output_tokens = max_output_tokens if max_output_tokens else self.default_generation_max_output_tokens
        temperature = temperature if temperature else self.default_generation_temperature
        
        if self.cohere_api_version == 1:
            response = self.client_v1.chat(
                model = self.generation_model_id,
                chat_history = chat_history,
                message = self.process_text(prompt),
                temperature = temperature,
                max_tokens = max_output_tokens
            )
            
            if not response or not response.text:
                return None

            return response.text
        
        else:
            chat_history.append(
                self.construct_pompt(prompt=prompt, role=CohereAPIv2Enum.USER.value)
            )
            
            response = self.client_v2.chat(
                model = self.generation_model_id,
                messages = chat_history,
                temperature = temperature,
                max_tokens = max_output_tokens
            )
            
            if not response or not response.message or not response.message.content \
                or len(response.message.content) == 0 or not response.message.content[0].text:
                    
                    return None
            
            return response.message.content[0].text
            
            
    def embed_text(self, text: str, document_type: str = None):

        if not self.client_v1 and not self.client_v2:
            self.logger.error("Cohere client was not set")
            return None
        
        if not self.embedding_model_id:
            self.logger.error("Embedding model for Cohere was not set")
            return None
        
        input_type = CohereAPIv2Enum.InputTypes.value.DOCUMENT.value
        if document_type == DocumentTypeEnum.QUERY:
            input_type = CohereAPIv2Enum.InputTypes.value.QUERY.value
        
        if self.cohere_api_version == 1:
            response = self.client_v1.embed(
                model = self.embedding_model_id,
                texts = [self.process_text(text)],
                input_type = input_type,
                embedding_types = ['float']
            )
        else:
            response = self.client_v2.embed(
                model = self.embedding_model_id,
                texts = [self.process_text(text)],
                input_type = input_type,
                embedding_types = ['float']
            )
            
        
        if not response or not response.embeddings or not response.embeddings.float_:
            self.logger.error("Error while embedding text with Cohere")
            
        return response.embeddings.float_[0]