"""Utility helpers for batching collections."""

from __future__ import annotations

from typing import Iterable, Iterator, Sequence, TypeVar

T = TypeVar("T")


def chunked(sequence: Sequence[T] | Iterable[T], size: int) -> Iterator[list[T]]:
    """Yield chunks of ``size`` items from ``sequence``."""

    if size <= 0:
        raise ValueError("Chunk size must be positive")

    bucket: list[T] = []
    for item in sequence:
        bucket.append(item)
        if len(bucket) == size:
            yield bucket
            bucket = []

    if bucket:
        yield bucket
