from enum import Enum

class LLMProviderEnum(str, Enum):
    OPENAI = "OPENAI"
    COHERE = "COHERE"
    GOOGLE = "GOOGLE"


class OpenAIEnum(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class CohereAPIv1Enum(str, Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "CHATBOT"

    class InputTypes(str, Enum):
        DOCUMENT = "search_document"
        QUERY = "search_query"
        IMAGE = "image"


class CohereAPIv2Enum(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    class InputTypes(str, Enum):
        DOCUMENT = "search_document"
        QUERY = "search_query"
        IMAGE = "image"


class GoogleEnum(str, Enum):
    SYSTEM = "system"  # Represents the concept, but usually handled differently in API
    USER = "user"
    ASSISTANT = "model" # Google uses 'model' for the assistant role in contents


class DocumentTypeEnum(str, Enum):
    DOCUMENT = "document"
    QUERY = "query"