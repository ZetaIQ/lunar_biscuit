import asyncio
from dataclasses import dataclass

from radiant_chacha.config import (
    BLOCK_CONNECTION_THRESHOLD,
    BLOCK_INFLUENCE_RADIUS,
    BLOCK_STABILITY_WINDOW,
    BLOCK_TICK_INTERVAL,
)
from radiant_chacha.core.neighbor_base import NeighborBase


@dataclass
class Block(NeighborBase):
    """
    A Block has:
    - Exactly 6 canonical neighbor slots (±x, ±y, ±z)
    - Movement allowed
    - No special anchoring

    Configuration Parameters (from radiant_chacha.config):
        BLOCK_INFLUENCE_RADIUS (default: 8.0)
            Geometric reach for proximity decay in connection scoring.
        BLOCK_CONNECTION_THRESHOLD (default: 0.4)
            Similarity score threshold required to form connections (lower = more permissive).
        BLOCK_STABILITY_WINDOW (default: 10)
            Number of historical positions to use for stability calculations.

    Instance Parameters:
        :param influence_radius: Override geometric reach (default: 8.0, medium reach)
        :type influence_radius: float
        :param connection_threshold: Override connection threshold (default: 0.4)
        :type connection_threshold: float
        :param max_degree: Maximum number of neighbors (default: 6, canonical cube)
        :type max_degree: int
        :param is_anchor: Indicates if the Block is anchored/immobile (default: False)
        :type is_anchor: bool

    Example Usage (via factory):
        factory.create(Block, data={...}, pos=[1,2,3])  # uses config defaults
        factory.create(Block, data={...}, connection_threshold=0.5)  # override threshold
    """

    influence_radius: float = float(8)
    connection_threshold: float = 0.4
    max_degree: int = 6
    is_anchor: bool = False

    def degree_limit(self) -> int:
        return self.max_degree

    def __post_init__(self) -> None:
        super().__post_init__()
        # Apply config defaults if not overridden
        if self.connection_threshold == 0.4:  # default value, not explicitly set
            self.connection_threshold = BLOCK_CONNECTION_THRESHOLD
        if self.influence_radius == 8.0:
            self.influence_radius = BLOCK_INFLUENCE_RADIUS
        self.STABILITY_WINDOW = BLOCK_STABILITY_WINDOW
        self.tick_interval = BLOCK_TICK_INTERVAL
        # Start the run loop as an asyncio task
        try:
            asyncio.get_running_loop()
            asyncio.create_task(self.run())
        except RuntimeError:
            # No event loop running, create one if needed
            pass
