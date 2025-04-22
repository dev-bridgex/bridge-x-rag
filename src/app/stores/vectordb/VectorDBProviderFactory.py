
from .VectorDBEnums import VectorDBProviderEnum
from .VectorDBProviderInterface import VectorDBProviderInterface
from .providers import QdrantDBProvider
from app.helpers.config import Settings 
from app.controllers import BaseController


class VectorDBProviderFactory:
    
    def __init__(self, config: Settings):
        self.config = config
        self.base_controller = BaseController()
        
    def create(self, provider: str) -> VectorDBProviderInterface | None:
        if provider == VectorDBProviderEnum.QDRANT.value:
            
            if self.config.VECTOR_DB_PATH and len(self.config.VECTOR_DB_PATH):
                db_path = self.base_controller.get_database_path(db_name=self.config.VECTOR_DB_PATH)
            else:
                db_path = None
                
            return QdrantDBProvider(
                db_path=db_path,
                distance_method=self.config.VECTOR_DB_DISTANCE_METHOD,
                url=self.config.QDRANT_URL,
                api_key=self.config.QDRANT_API_KEY,
                prefer_grpc=self.config.QDRANT_PREFER_GRPC
            )
            
        return None