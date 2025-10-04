"""Pipeline orchestrator tying together fetching, density, summarization and hotness."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence

from .config import PipelineConfig
from .density_estimator import DensityEstimator
from .fetching import NewsFetcher
from .hotness import HotnessCalculator
from .models import Article
from .summarizer import Summarizer


class NewsPipelineOrchestrator:
    """High-level orchestrator that runs the Market Radar pipeline."""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.start_time = datetime.now(timezone.utc)
        self.time_window_delta = NewsFetcher.parse_since(config.time_window.since)

        self.fetcher = NewsFetcher(config.fetcher, config.time_window)
        self.density_estimator = DensityEstimator(config.density)
        self.summarizer = Summarizer(config.summarizer)
        self.hotness = HotnessCalculator(config.hotness, self.start_time, self.time_window_delta)

    def run(self) -> List[Dict[str, object]]:
        articles = self.fetcher.fetch(self.start_time)
        if not articles:
            self._write_output([])
            return []

        density_scores = self.density_estimator.estimate(articles)
        for idx, art in enumerate(articles):
            art.density_coef = density_scores.get(idx, 0.0)

        self.summarizer.summarize(articles)
        self.hotness.apply(articles)

        output = self._build_output(articles)
        self._write_output(output)
        return output

    def _build_output(self, articles: Sequence[Article]) -> List[Dict[str, object]]:
        def _to_iso(dt: datetime) -> str:
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        payload: List[Dict[str, object]] = []
        for art in articles:
            published = art.published_at or art.crawled_at
            payload.append(
                {
                    "source": art.source_id,
                    "source_domain": art.source_domain,
                    "published_at": _to_iso(published),
                    "url": art.url,
                    "title": art.title,
                    "summary": art.summary,
                    "time_coef": round(float(art.time_coef or 0.0), 6),
                    "density_coef": round(float(art.density_coef or 0.0), 6),
                    "domain_coef": round(float(art.domain_coef or 0.0), 6),
                    "hotness": round(float(art.hotness or 0.0), 6),
                }
            )

        payload.sort(key=lambda item: item["hotness"], reverse=True)
        return payload

    def _write_output(self, data: Sequence[Dict[str, object]]) -> None:
        path = self.config.output.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_from_config(path: Path) -> List[Dict[str, object]]:
    config = PipelineConfig.from_yaml(path)
    orchestrator = NewsPipelineOrchestrator(config)
    return orchestrator.run()


if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="Market Radar pipeline orchestrator")
    parser.add_argument("--config", required=True, help="Path to YAML configuration")
    args = parser.parse_args()

    config_path = Path(args.config)
    run_from_config(config_path)
