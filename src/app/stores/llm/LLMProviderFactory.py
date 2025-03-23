from .LLMEnums import LLMProviderEnum
from .LLMProviderInterface import LLMProviderInterface
from .providers import OpenAIProvider, CohereProvider
from app.helpers.config import Settings

class LLMProviderFactory:
    def __init__(self, config: Settings) -> None:
        self.config = config
    
    def create(self, provider: str) -> LLMProviderInterface:
        if provider == LLMProviderEnum.OPENAI.value:
            return OpenAIProvider(
                api_key=self.config.OPENAI_API_KEY,
                api_url = self.config.OPENAI_API_URL,
                default_input_max_characters = self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens = self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature = self.config.GENERATION_DAFAULT_TEMPERATURE
            )
            
        if provider == LLMProviderEnum.COHERE.value:
            return CohereProvider(
                api_key = self.config.COHERE_API_KEY,
                cohere_api_version = self.config.COHERE_API_VESION,
                default_input_max_characters = self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens = self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature = self.config.GENERATION_DAFAULT_TEMPERATURE
            )
        
        return None