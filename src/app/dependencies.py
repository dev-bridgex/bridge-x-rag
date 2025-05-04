from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.mongodb import get_database
from app.models import KnowledgeBaseModel, AssetModel, ChunkModel
from app.controllers import KnowledgeBaseController, AssetController, ProcessingController, NLPController
from app.stores.llm.templates.template_parser import TemplateParser

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

# Template Parser
def get_template_parser(request: Request):
    """Dependency for TemplateParser

    Creates a new TemplateParser instance for each request.
    This allows language settings to be scoped to the request.
    """
    settings = request.app.template_parser_settings
    return TemplateParser(
        language=settings["primary_lang"],
        default_language=settings["default_lang"]
    )


def get_processing_controller(request: Request, template_parser: TemplateParser = Depends(get_template_parser)):
    """Dependency for ProcessingController

    Creates a ProcessingController instance with the necessary clients from the request app state.
    """
    return ProcessingController(
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=template_parser
    )


# NLP Controller
def get_nlp_controller(
    request: Request,
    template_parser: TemplateParser = Depends(get_template_parser),
    chunk_model: ChunkModel = Depends(get_chunk_model)
):
    """Dependency for NLPController

    Creates an NLPController instance with the necessary clients from the request app state.
    Injects the spaCy NLP client if available.
    """
    return NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=template_parser,
        chunk_model=chunk_model,
        nlp_client=getattr(request.app, 'nlp_client', None)
    )
