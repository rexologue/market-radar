"""FastAPI application exposing the Market Radar pipeline over HTTP."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from .config import PipelineConfig
from .orchestrator import NewsPipelineOrchestrator

DEFAULT_CONFIG_ENV = "MARKET_RADAR_CONFIG"
DEFAULT_CONFIG_FALLBACK = "config.example.yaml"
MODEL_CACHE_ENV = "MARKET_RADAR_MODEL_CACHE"

_DEFAULT_CONFIG_PATH: Path | None = None


class ArticlePayload(BaseModel):
    """Schema returned for every ranked article."""

    source: str = Field(..., description="Identifier of the RSS source")
    source_domain: str = Field(..., description="Domain extracted from the source URL")
    published_at: str = Field(..., description="UTC ISO timestamp of publication")
    url: str = Field(..., description="Canonical article URL")
    title: str = Field(..., description="Article title")
    summary: str = Field(..., description="LLM-generated or heuristic summary")
    time_coef: float = Field(..., description="Normalised time coefficient")
    density_coef: float = Field(..., description="Normalised density coefficient")
    domain_coef: float = Field(..., description="Domain/category weight")
    hotness: float = Field(..., description="Final hotness score in [0, 1]")


class PipelineResponse(BaseModel):
    """Response returned by the pipeline endpoint."""

    generated_at: datetime = Field(..., description="UTC timestamp when the run completed")
    articles: List[ArticlePayload] = Field(..., description="Ranked articles with coefficients")


def configure_default_config_path(path: Path | str) -> None:
    """Set the default configuration file path used by the API factory."""

    global _DEFAULT_CONFIG_PATH
    _DEFAULT_CONFIG_PATH = Path(path).expanduser()


def create_app(config_path: Path | str | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    default_config_path = _determine_config_path(config_path)

    app = FastAPI(
        title="Market Radar API",
        version="1.0.0",
        description=(
            "HTTP wrapper for the Market Radar pipeline. Runtime overrides are limited "
            "to the 'since' window and required output destination."
        ),
    )

    @app.get("/healthz", summary="Health check")
    async def health_check() -> dict[str, str]:
        """Return a simple health indicator."""

        return {"status": "ok"}

    @app.post(
        "/pipeline",
        summary="Run the Market Radar pipeline",
        response_model=PipelineResponse,
    )
    async def run_pipeline(
        since: Optional[str] = Query(
            None,
            description="Override the time window 'since' value, e.g. '6h'",
        ),
        output_path: str = Query(
            ...,
            description="Destination JSON file written by the pipeline",
        ),
    ) -> PipelineResponse:
        """Execute the pipeline with optional overrides and return the ranked articles."""

        try:
            response = await run_in_threadpool(
                _execute_pipeline,
                default_config_path,
                since,
                output_path,
            )
        except FileNotFoundError as exc:  # pragma: no cover - simple mapping
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:  # pragma: no cover - validation mapping
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive catch-all
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return response

    return app


def _execute_pipeline(
    default_config_path: Path,
    since: Optional[str],
    output_path: str,
) -> PipelineResponse:
    """Load configuration, apply overrides, and run the pipeline synchronously."""

    config = _load_config(default_config_path)

    if since:
        config.time_window.since = since

    if not output_path:
        raise ValueError("The 'output_path' query parameter is required")

    config.output.path = _ensure_parent(
        _validate_path(output_path, "output file", must_exist=False)
    )

    model_cache = os.getenv(MODEL_CACHE_ENV)
    if model_cache and config.density.model_cache_dir is None:
        cache_dir = Path(model_cache).expanduser()
        cache_dir.mkdir(parents=True, exist_ok=True)
        config.density.model_cache_dir = cache_dir

    orchestrator = NewsPipelineOrchestrator(config)
    articles = orchestrator.run()

    generated_at = datetime.now(timezone.utc)
    payload = [ArticlePayload(**article) for article in articles]
    return PipelineResponse(generated_at=generated_at, articles=payload)


def _determine_config_path(config_path: Path | str | None) -> Path:
    """Resolve the configuration path from CLI, module, or environment."""

    candidates: List[Path] = []
    if config_path is not None:
        candidates.append(Path(config_path).expanduser())
    if _DEFAULT_CONFIG_PATH is not None:
        candidates.append(_DEFAULT_CONFIG_PATH)

    env_path = os.getenv(DEFAULT_CONFIG_ENV)
    if env_path:
        candidates.append(Path(env_path).expanduser())

    if not candidates:
        candidates.append(Path(DEFAULT_CONFIG_FALLBACK).expanduser())

    return candidates[0]


def _load_config(default_config_path: Path) -> PipelineConfig:
    """Load configuration from the default path defined at application startup."""

    config_path = _validate_path(default_config_path, "configuration file")
    return PipelineConfig.from_yaml(config_path)


def _validate_path(path_input: Path | str, label: str, *, must_exist: bool = True) -> Path:
    """Validate and normalise file paths coming from the request."""

    path = Path(path_input).expanduser()
    if not path.is_absolute():
        path = path.resolve()
    if must_exist and not path.exists():
        raise FileNotFoundError(f"{label.capitalize()} not found: {path}")
    return path


def _ensure_parent(path: Path) -> Path:
    """Ensure the parent directory exists before writing output files."""

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


__all__ = [
    "configure_default_config_path",
    "create_app",
]
