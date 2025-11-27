import asyncio
from dataclasses import dataclass

from radiant_chacha.config import (
    SPHERE_CONNECTION_THRESHOLD,
    SPHERE_INFLUENCE_RADIUS,
    SPHERE_STABILITY_WINDOW,
    SPHERE_TICK_INTERVAL,
)
from radiant_chacha.core.neighbor_base import NeighborBase


@dataclass
class Sphere(NeighborBase):
    """
    A Sphere:
    - Represents a stable hub/focal data region
    - Infinite (or very large) degree
    - Typically acts as an anchor
    - Usually does NOT move

    Configuration Parameters (from radiant_chacha.config):
        SPHERE_INFLUENCE_RADIUS (default: 15.0)
            Geometric reach for proximity decay in connection scoring (largest reach as hub).
        SPHERE_CONNECTION_THRESHOLD (default: 0.2)
            Similarity score threshold required to form connections (low = permissive, attracts connections).
        SPHERE_STABILITY_WINDOW (default: 10)
            Number of historical positions to use for stability calculations.

    Instance Parameters:
        :param influence_radius: Override geometric reach (default: 15.0, largest reach as hub)
        :type influence_radius: float
        :param connection_threshold: Override connection threshold (default: 0.2)
        :type connection_threshold: float
        :param max_degree: Maximum number of neighbors (default: inf, unlimited)
        :type max_degree: float
        :param is_anchor: Indicates if the Sphere is anchored/immobile (default: True)
        :type is_anchor: bool

    Example Usage (via factory):
        factory.create(Sphere, data={...}, pos=[0,0,0])  # uses config defaults, is_anchor=True by default
        factory.create(Sphere, data={...}, is_anchor=False)  # movable hub
    """

    influence_radius: float = float(15)
    connection_threshold: float = 0.2
    max_degree: float = float("inf")  # unlimited
    is_anchor: bool = True  # does not move by default

    def degree_limit(self) -> float:
        return self.max_degree

    def __post_init__(self) -> None:
        super().__post_init__()
        # Apply config defaults if not overridden
        if self.connection_threshold == 0.2:
            self.connection_threshold = SPHERE_CONNECTION_THRESHOLD
        if self.influence_radius == 15.0:
            self.influence_radius = SPHERE_INFLUENCE_RADIUS
        self.STABILITY_WINDOW = SPHERE_STABILITY_WINDOW
        self.tick_interval = SPHERE_TICK_INTERVAL
        # Start the run loop as an asyncio task
        try:
            asyncio.get_running_loop()
            asyncio.create_task(self.run())
        except RuntimeError:
            # No event loop running, create one if needed
            pass
