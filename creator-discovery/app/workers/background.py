"""Lightweight background task helpers (MVP uses FastAPI BackgroundTasks at route level)."""

from typing import Callable

from fastapi import BackgroundTasks


def enqueue(background_tasks: BackgroundTasks, fn: Callable, *args, **kwargs) -> None:
    background_tasks.add_task(fn, *args, **kwargs)
