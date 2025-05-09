from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.mongodb import get_database
from app.models import KnowledgeBaseModel, AssetModel, ChunkModel
from app.controllers import KnowledgeBaseController, AssetController, NLPController

# Database models
async def get_knowledge_base_model(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Dependency for KnowledgeBaseModel"""
    return await KnowledgeBaseModel.create_instance(db_client=db)

async def get_asset_model(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Dependency for AssetModel"""
    return await AssetModel.create_instance(db_client=db)

async def get_chunk_model(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Dependency for ChunkModel"""
    return await ChunkModel.create_instance(db_client=db)

# Controllers
def get_knowledge_base_controller():
    """Dependency for KnowledgeBaseController"""
    return KnowledgeBaseController()

def get_asset_controller():
    """Dependency for AssetController"""
    return AssetController()

# NLP Controller
def get_nlp_controller(request: Request):
    """Dependency for NLPController

    Creates an NLPController instance with the necessary clients from the request app state.
    """
    return NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client
    )
