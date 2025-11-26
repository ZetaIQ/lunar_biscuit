from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
from radiant_chacha.core.protocol import NeighborProtocol, Vec3
from radiant_chacha.methods.tick import tick


@dataclass
class NeighborBase(NeighborProtocol, ABC):
    id: int
    data: Any

    # --- Identity Hash ---
    addr: str = ""  # SHA-256 string (set at init)

    # --- Spatial Position ---
    pos: Vec3 = field(default_factory=lambda: np.zeros(3, dtype=float))

    # --- Physics ---
    velocity: Vec3 = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    gravity: float = np.float64(0.0)

    # --- Neighbors list ---
    neighbors: list["NeighborProtocol"] = field(default_factory=list)

    # Spheres are anchors, blocks and points are not
    is_anchor: bool = False

    # --- Snapshots of states after changes ---
    history: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])

    # Max number of positions to reference when calculating stability
    STABILITY_WINDOW: int = 10

    # Floating point number of seconds between ticks
    tick_interval: float = 1.0

    # Token initialized as None to enforce factory construction
    _token: Optional[object] = None

    # ------------------------------------------------------------------

    async def run(self, print_stats=False) -> None:
        tick(obj=self, dt=self.tick_interval, print_stats=print_stats)
        await asyncio.sleep(self.tick_interval)
        try:
            while True:
                tick(obj=self, dt=self.tick_interval, print_stats=print_stats)
                await asyncio.sleep(self.tick_interval)
        except asyncio.CancelledError:
            return

    @abstractmethod
    def degree_limit(self) -> int | float:
        """Maximum allowable neighbors. float('inf') means unlimited."""
        ...

    def __post_init__(self) -> None:
        self.type: str = self.__class__.__name__
        if getattr(self, "_token", None) is None:
            raise RuntimeError(
                "Use NeighborFactory to create instances, do not instantiate directly."
            )
