from .BaseController import BaseController
from app.models import FileTypesEnum
import os
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class ProcessController(BaseController):
    
    def __init__(self):
        super().__init__()


    def get_file_extension(self, file_name: str):
        return os.path.splitext(file_name)[-1]
    
    def get_file_path(self, file_name: str, project_path: str):
        return os.path.join( project_path, file_name )
    
    
    def get_file_loader(self, file_name: str, file_path: str):
        
        file_extension = self.get_file_extension(file_name=file_name)
        
        if file_extension == FileTypesEnum.TXT.value:
            return TextLoader(file_path, encoding="utf-8")
        
        if file_extension == FileTypesEnum.PDF.value:
            return PyMuPDFLoader(file_path)
        
        return None
    
    
    def get_file_content(self, file_name: str, file_path: str) -> list[Document]:
        loader = self.get_file_loader(file_name=file_name, file_path=file_path)
        return loader.load()
        
    
    def process_file_content(
        self, 
        file_content: list[Document],
        file_name: str,
        chunk_size: int=600,
        overlap_size: int=100        
        ):
        
        
        file_content_texts = [
            document.page_content
            for document in file_content
        ]
        
        file_content_metadatas = [
            document.metadata
            for document in file_content
        ]
        
        # Improved splitter with paragraph and sentence awareness
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap_size,
            separators=["\n\n", "\n", ".", "!", "?", " ", ""],  # favors paragraph/sentence endings
            length_function=len,
            is_separator_regex=False
        )

        chunks = text_splitter.create_documents(
            file_content_texts,
            metadatas=file_content_metadatas
            )
        
        return chunks
        
    
        
        
    