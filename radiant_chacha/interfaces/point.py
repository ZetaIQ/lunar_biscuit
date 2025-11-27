import asyncio
from dataclasses import dataclass

from radiant_chacha.config import (
    POINT_CONNECTION_THRESHOLD,
    POINT_INFLUENCE_RADIUS,
    POINT_STABILITY_WINDOW,
    POINT_TICK_INTERVAL,
)
from radiant_chacha.core.neighbor_base import NeighborBase


@dataclass
class Point(NeighborBase):
    """
    A Point:
    - Has only 1 neighbor (a single parent link)
    - Moves freely
    - Has the simplest role in the network

    Configuration Parameters (from radiant_chacha.config):
        POINT_INFLUENCE_RADIUS (default: 3.0)
            Geometric reach for proximity decay in connection scoring (minimal reach as leaf node).
        POINT_CONNECTION_THRESHOLD (default: 0.8)
            Similarity score threshold required to form connections (high = selective).
        POINT_STABILITY_WINDOW (default: 10)
            Number of historical positions to use for stability calculations.

    Instance Parameters:
        :param influence_radius: Override geometric reach (default: 3.0, minimal reach)
        :type influence_radius: float
        :param connection_threshold: Override connection threshold (default: 0.8)
        :type connection_threshold: float
        :param max_degree: Maximum number of neighbors (default: 1, leaf node)
        :type max_degree: int
        :param is_anchor: Indicates if the Point is anchored/immobile (default: False)
        :type is_anchor: bool

    Example Usage (via factory):
        factory.create(Point, data={...}, pos=[1,2,3])  # uses config defaults
        factory.create(Point, data={...}, connection_threshold=0.7)  # override threshold
    """

    influence_radius: float = float(3)
    connection_threshold: float = 0.8
    max_degree: int = 1
    is_anchor: bool = False

    def degree_limit(self) -> int:
        return self.max_degree

    def __post_init__(self) -> None:
        super().__post_init__()
        # Apply config defaults if not overridden
        if self.connection_threshold == 0.8:
            self.connection_threshold = POINT_CONNECTION_THRESHOLD
        if self.influence_radius == 3.0:
            self.influence_radius = POINT_INFLUENCE_RADIUS
        self.STABILITY_WINDOW = POINT_STABILITY_WINDOW
        self.tick_interval = POINT_TICK_INTERVAL
        # Start the run loop as an asyncio task
        try:
            asyncio.get_running_loop()
            asyncio.create_task(self.run())
        except RuntimeError:
            # No event loop running, create one if needed
            pass
