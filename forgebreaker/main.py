import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version as pkg_version

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from forgebreaker.api import (
    assumptions_router,
    chat_router,
    collection_router,
    decks_router,
    distance_router,
    health_router,
    stress_router,
)
from forgebreaker.config import settings
from forgebreaker.db.database import init_db
from forgebreaker.models.failure import (
    ApiResponse,
    FailureKind,
    KnownError,
    RefusalError,
)
from forgebreaker.services.card_name_guard import CardNameLeakageError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=pkg_version("forgebreaker"),
    lifespan=lifespan,
)

app.include_router(assumptions_router)
app.include_router(chat_router)
app.include_router(collection_router)
app.include_router(decks_router)
app.include_router(distance_router)
app.include_router(health_router)
app.include_router(stress_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers — classify all failures


@app.exception_handler(KnownError)
async def known_error_handler(_request: Request, exc: KnownError) -> JSONResponse:
    """Handle known, explainable errors."""
    response = exc.to_response()
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(),
    )


@app.exception_handler(RefusalError)
async def refusal_error_handler(_request: Request, exc: RefusalError) -> JSONResponse:
    """Handle constraint-based refusals."""
    response = exc.to_response()
    return JSONResponse(
        status_code=422,  # Unprocessable Entity
        content=response.model_dump(),
    )


@app.exception_handler(CardNameLeakageError)
async def card_name_leakage_handler(_request: Request, exc: CardNameLeakageError) -> JSONResponse:
    """Handle card name invariant violations."""
    response = ApiResponse.refusal(
        kind=FailureKind.CARD_NAME_LEAKAGE,
        message=(
            "The system attempted to produce an invalid card reference. "
            "This request has been refused to maintain output integrity."
        ),
        detail=f"Detected unvalidated card: '{exc.leaked_name}'",
        suggestion="Please try a different request.",
    )
    return JSONResponse(
        status_code=422,
        content=response.model_dump(),
    )


@app.exception_handler(Exception)
async def unknown_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all unexpected exceptions.

    This is the catch-all that ensures no raw 500 reaches the frontend.
    The system explicitly admits it does not know why it failed.
    """
    logger.exception("Unexpected error: %s", exc)
    response = ApiResponse.unknown_failure(
        detail=f"{type(exc).__name__}: {exc!s}"[:200],  # Truncate for safety
    )
    return JSONResponse(
        status_code=500,
        content=response.model_dump(),
    )
