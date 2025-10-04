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
MODEL_CACHE_ENV = "MARKET_RADAR_MODEL_CACHE"


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


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    default_config_path = os.getenv(DEFAULT_CONFIG_ENV, "config.yaml")

    app = FastAPI(
        title="Market Radar API",
        version="1.0.0",
        description=(
            "HTTP wrapper for the Market Radar pipeline. Provide overrides via query "
            "parameters to adjust the execution on the fly."
        ),
    )

    @app.get("/healthz", summary="Health check")
    async def health_check() -> dict[str, str]:
        """Return a simple health indicator."""

        return {"status": "ok"}

    @app.get(
        "/pipeline",
        summary="Run the Market Radar pipeline",
        response_model=PipelineResponse,
    )
    async def run_pipeline(
        config_path: Optional[str] = Query(
            None,
            description="Path to the YAML configuration (defaults to MARKET_RADAR_CONFIG or config.yaml)",
        ),
        since: Optional[str] = Query(
            None,
            description="Override the time window 'since' value, e.g. '6h'",
        ),
        max_per_source: Optional[int] = Query(
            None,
            ge=1,
            description="Limit the number of articles pulled per source",
        ),
        limit: Optional[int] = Query(
            None,
            ge=1,
            description="Trim the number of articles returned in the response",
        ),
        sources_path: Optional[str] = Query(
            None,
            description="Override the sources JSON path used by the fetcher",
        ),
        output_path: Optional[str] = Query(
            None,
            description="Override the destination JSON file written by the pipeline",
        ),
    ) -> PipelineResponse:
        """Execute the pipeline with optional overrides and return the ranked articles."""

        try:
            response = await run_in_threadpool(
                _execute_pipeline,
                config_path or default_config_path,
                since,
                max_per_source,
                limit,
                sources_path,
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
    config_path_str: str,
    since: Optional[str],
    max_per_source: Optional[int],
    limit: Optional[int],
    sources_path: Optional[str],
    output_path: Optional[str],
) -> PipelineResponse:
    """Load configuration, apply overrides, and run the pipeline synchronously."""

    config_path = _validate_path(config_path_str, "configuration file")
    config = PipelineConfig.from_yaml(config_path)

    if since:
        config.time_window.since = since

    if max_per_source is not None:
        config.fetcher.max_per_source = max_per_source

    if sources_path:
        config.fetcher.sources_path = _validate_path(sources_path, "sources file")

    if output_path:
        config.output.path = _ensure_parent(_validate_path(output_path, "output file", must_exist=False))

    model_cache = os.getenv(MODEL_CACHE_ENV)
    if model_cache and config.density.model_cache_dir is None:
        cache_dir = Path(model_cache).expanduser()
        cache_dir.mkdir(parents=True, exist_ok=True)
        config.density.model_cache_dir = cache_dir

    orchestrator = NewsPipelineOrchestrator(config)
    articles = orchestrator.run()

    if limit is not None:
        articles = articles[:limit]

    generated_at = datetime.now(timezone.utc)
    payload = [ArticlePayload(**article) for article in articles]
    return PipelineResponse(generated_at=generated_at, articles=payload)


def _validate_path(path_str: str, label: str, *, must_exist: bool = True) -> Path:
    """Validate and normalise file paths coming from the request."""

    path = Path(path_str).expanduser()
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
    "create_app",
]
