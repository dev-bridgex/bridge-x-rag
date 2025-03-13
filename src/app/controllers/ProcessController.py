from .BaseController import BaseController
from app.models import FileTypes
import os
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class ProcessController(BaseController):
    
    def __init__(self):
        super().__init__()


    def get_file_extension(self, file_id: str):
        return os.path.splitext(file_id)[-1]
    
    def get_file_path(self, file_id: str, project_path: str):
        file_path = os.path.join( project_path, file_id )
        if not os.path.exists(file_path):
            return None
        return file_path
    
    
    def get_file_loader(self, file_id: str, file_path: str):
        
        file_extension = self.get_file_extension(file_id=file_id)
        
        if file_extension == FileTypes.TXT.value:
            return TextLoader(file_path, encoding="utf-8")
        
        if file_extension == FileTypes.PDF.value:
            return PyMuPDFLoader(file_path)
        
        return None
    
    
    def get_file_content(self, file_id: str, file_path: str) -> list[Document]:
        loader = self.get_file_loader(file_id=file_id, file_path=file_path)
        return loader.load()
        
    
    def process_file_content(
        self, 
        file_content: list[Document],
        file_id: str,
        chunk_size: int=100,
        overlap_size: int=20        
        ):
        
        
        file_content_texts = [
            document.page_content
            for document in file_content
        ]
        
        file_content_metadatas = [
            document.metadata
            for document in file_content
        ]
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap_size,
            length_function=len,
            is_separator_regex=False,
        )
        
        chunks = text_splitter.create_documents(
            file_content_texts,
            metadatas=file_content_metadatas
            )
        
        return chunks
        
    
        
        
    