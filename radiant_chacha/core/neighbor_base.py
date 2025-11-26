from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

import numpy as np

from radiant_chacha.core.protocol import NeighborProtocol, Vec3
from radiant_chacha.methods.tick import tick

if TYPE_CHECKING:
    from radiant_chacha.core import NeighborFactory


@dataclass
class NeighborBase(NeighborProtocol, ABC):
    """
    NeighborBase: Base class for all neighbor types (Block, Point, Sphere)
    Provides common attributes and methods.
    Enforces factory-based construction.


    :param id: Integer ID granted by NeighborFactory
    :type id: int
    :param data: Arbitrary data payload
    :type data: Any
    :param factory: Reference to the NeighborFactory that created this node
    :type factory: NeighborFactory
    :param addr: SHA-256 address string
    :type addr: str
    :param attempts: Integer count of connection attempts that have exceeded degree limit
    :type attempts: int
    :param connection_threshold: Float [0,1] for connection acceptance
    :type connection_threshold: float
    :param influence_radius: Float [0,1]|inf(experimental) for influence calculations
    :type influence_radius: float
    :param pos: 3D position vector (numpy ndarray)
    :type pos: Vec3
    :param velocity: 3D velocity vector (numpy ndarray)
    :type velocity: Vec3
    :param gravity: Scalar gravity value
    :type gravity: float
    :param neighbors: List of connected NeighborProtocol instances
    :type neighbors: list[NeighborProtocol]
    :param is_anchor: Boolean indicating if node is an anchor
    :type is_anchor: bool
    :param history: List of state snapshots for history tracking
    :type history: list[dict[str, Any]]
    :param STABILITY_WINDOW: Max history length for stability calculations
    :type STABILITY_WINDOW: int
    :param tick_interval: Float seconds between ticks
    :type tick_interval: float
    """

    id: int
    data: Any
    factory: "NeighborFactory"

    # --- Identity Hash ---
    addr: str = ""  # SHA-256 string (set at init)

    # --- Attempt Counter ---
    attempts: int = 0

    # --- Connection Threshold (should be a float from 0-1, lower is more permissive) ---
    connection_threshold: float = field(default_factory=float)

    # ---
    # Influence Radius (should be a float from 0-1, high is more influential, inf is experiemental)
    # ---
    influence_radius: float = field(default_factory=float)

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
