from enum import Enum

class LLMProviderEnum(Enum):
    OPENAI = "OPENAI"
    COHERE = "COHERE"
    

class OpenAIEnum(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    

class CohereEnum(Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "CHATBOT"
    
    class InputTypes(Enum):
        DOCUMENT = "search_document"
        QUERY = "search_query"
        IMAGE = "image"
        

class CohereAPIv2Enum(CohereEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    


class DocumentTypeEnum(Enum):
    DOCUMENT = "document"
    QUERY = "query"