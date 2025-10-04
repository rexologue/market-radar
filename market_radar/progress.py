"""Progress bar utilities used across the Market Radar pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)


@dataclass
class StageHandle:
    """Lightweight handle for updating a stage progress bar."""

    progress: "PipelineProgress"
    task_id: TaskID
    description: str
    completed: bool = False

    def set_total(self, total: Optional[int]) -> None:
        self.progress._progress.update(self.task_id, total=total)

    def advance(self, amount: int = 1) -> None:
        if self.completed:
            return
        self.progress._progress.advance(self.task_id, amount)

    def complete(self) -> None:
        if self.completed:
            return
        task = self.progress._progress.get_task(self.task_id)
        remaining = 0.0
        if task.total is not None:
            remaining = max(task.total - task.completed, 0.0)
        if remaining:
            self.progress._progress.advance(self.task_id, remaining)
        self.progress._progress.remove_task(self.task_id)
        self.progress._on_stage_complete()
        self.completed = True

    def __enter__(self) -> "StageHandle":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.complete()


class PipelineProgress:
    """Utility orchestrating progress bars for pipeline stages."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}", justify="left"),
            BarColumn(bar_width=None),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=self.console,
            transient=False,
        )
        self._pipeline_task: Optional[TaskID] = None
        self._active_stage: Optional[StageHandle] = None
        self._total_stages = 0
        self._completed_stages = 0

    def __enter__(self) -> "PipelineProgress":
        self._progress.__enter__()
        self._pipeline_task = self._progress.add_task("Pipeline", total=0)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._active_stage is not None:
            self._active_stage.complete()
        self._progress.__exit__(exc_type, exc, tb)

    def stage(self, description: str, total: Optional[int] = None) -> StageHandle:
        if self._active_stage is not None:
            self._active_stage.complete()
        self._total_stages += 1
        if self._pipeline_task is not None:
            self._progress.update(
                self._pipeline_task,
                total=self._total_stages,
                description=f"Pipeline • {description}",
            )
        task_id = self._progress.add_task(description, total=total)
        handle = StageHandle(progress=self, task_id=task_id, description=description)
        self._active_stage = handle
        return handle

    def _on_stage_complete(self) -> None:
        self._completed_stages += 1
        if self._pipeline_task is not None:
            self._progress.advance(self._pipeline_task, 1)
            if self._completed_stages >= self._total_stages:
                self._progress.update(self._pipeline_task, description="Pipeline • done")
        self._active_stage = None


__all__ = ["PipelineProgress", "StageHandle"]
