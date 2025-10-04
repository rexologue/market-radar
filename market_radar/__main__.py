"""Entrypoint for running the Market Radar API with ``python -m market_radar``."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    """Launch the FastAPI application with Uvicorn."""

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "market_radar.api:create_app",
        host="0.0.0.0",
        port=port,
        factory=True,
        reload=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
