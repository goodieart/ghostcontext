from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI

from ghostcontext.config import load_settings
from ghostcontext.routers.chat_completions import router as openai_router
from ghostcontext.services.upstream import build_async_openai_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    load_dotenv()
    settings = load_settings()
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_path.mkdir(parents=True, exist_ok=True)

    chroma_client = chromadb.PersistentClient(path=str(settings.chroma_path))
    collection = chroma_client.get_or_create_collection(name=settings.collection_name)
    llm_client = build_async_openai_client(
        base_url=settings.upstream_base_url,
        api_key=settings.upstream_api_key,
    )

    app.state.settings = settings
    app.state.collection = collection
    app.state.llm_client = llm_client
    app.state.chroma_client = chroma_client

    logger.info(
        "GhostContext ready — upstream=%s collection=%s",
        settings.upstream_base_url,
        settings.collection_name,
    )
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="GhostContext",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(openai_router)
    return application


app = create_app()
