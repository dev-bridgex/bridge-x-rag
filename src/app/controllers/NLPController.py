from .BaseController import BaseController
from app.stores.vectordb import VectorDBProviderInterface
from app.stores.llm import LLMProviderInterface
from app.stores.llm.LLMEnums import DocumentTypeEnum
from app.models.db_schemas import Project, DataChunk
from typing import List
import json


class NLPController(BaseController):
    def __init__(self, vectordb_client: VectorDBProviderInterface,
                 generation_client: LLMProviderInterface,
                 embedding_client: LLMProviderInterface) -> None:
        super().__init__()
        
        self.vectordb_client: VectorDBProviderInterface = vectordb_client
        self.generation_client: LLMProviderInterface = generation_client
        self.embedding_client: LLMProviderInterface = embedding_client
        

    def create_collection_name(self, project_name: str):
        return f"collection_{project_name}".strip()
    
    async def list_vector_db_collections(self) -> List:
        return await self.vectordb_client.list_all_collections()
    
    async def delete_vector_db_collection(self, project: Project) -> bool:
        collection_name = self.create_collection_name(project_name=project.project_name) 
        return await self.vectordb_client.delete_collection(collection_name=collection_name)
    
    async def is_collection_exists(self, project: Project) -> bool:
        collection_name = self.create_collection_name(project_name=project.project_name)
        return await self.vectordb_client.is_collection_exists(collection_name=collection_name)

            
        
    async def get_vector_db_collection_info(self, project: Project):
        collection_name = self.create_collection_name(project_name=project.project_name)  
        collection_info = await self.vectordb_client.get_collection_info(collection_name=collection_name)
        
        if not collection_info:
            return None
        
        return json.loads(
            json.dumps(collection_info, default = lambda x: x.__dict__)
        )
       
    
    async def create_vector_db_collection(self, project: Project, do_reset: bool = False) -> str | None:
        collection_name = self.create_collection_name(project_name=project.project_name)
        
        is_created = await self.vectordb_client.create_collection(
            collection_name = collection_name,
            embedding_size = self.embedding_client.embedding_size,
            do_reset = do_reset
        )
        
        if not is_created:
            return None
        
        return collection_name
    
        
    async def index_into_vector_db(
        self,
        collection_name: str,
        chunks: List[DataChunk],
        chunks_ids: List[int],
        ) -> bool:
        
        # step2: process data chunks and vectorize (create embeddings)
        texts = [ chunk.chunk_text for chunk in chunks ]
        metadatas = [ chunk.chunk_metadata for chunk in chunks ]
        vectors = [
            self.embedding_client.embed_text(
                text=text,
                document_type=DocumentTypeEnum.DOCUMENT.value
                )
            for text in texts
        ]
        
        # step4: insert data chunks into vectord
        is_inserted = await self.vectordb_client.insert_many(
            collection_name = collection_name,
            texts = texts,
            metadatas = metadatas,
            vectors = vectors,
            record_ids = chunks_ids
        )
        
        if not is_inserted:
            return False
        
        return True
    

    async def search_vector_db_collection(
        self,
        project: Project,
        query: str,
        limit: int = 10
        ):
        
        # step1: get collection name
        collection_name = self.create_collection_name(project_name=project.project_name)  
        
        # step2: generate text embedding vector
        vector =  self.embedding_client.embed_text(text=query, 
                                                   document_type=DocumentTypeEnum.DOCUMENT.value)
        
        if not vector or len(vector) == 0:
            return None
        
        # step3: do semantic search in the vector db and retrieve most similar texts
        retrieved_documents = await self.vectordb_client.search_by_vector(
            collection_name = collection_name,
            vector = vector,
            limit = limit
        )
        
        if not retrieved_documents:
            return None
        
        # return json.loads(
        #     json.dumps(retrieved_documents, default = lambda x: x.__dict__)
        # )
        
        return retrieved_documents
        


        
        
        
        
        
        
        
        
        
        
        
        