from dataclasses import dataclass

from radiant_chacha.core.neighbor_base import NeighborBase


@dataclass
class Block(NeighborBase):
    """
    A Block has:
    - Exactly 6 canonical neighbor slots (±x, ±y, ±z)
    - Movement allowed
    - No special anchoring


    :param influence_radius: Influence radius for connection strength (default: 10)
    :type influence_radius: float
    :param connection_threshold: Threshold for forming connections (default: 0.4)
    :type connection_threshold: float
    :param max_degree: Maximum number of neighbors (default: 6)
    :type max_degree: int
    :param is_anchor: Indicates if the Block is an anchor (default: False)
    :type is_anchor: bool
    """

    influence_radius: float = float(10)  # experimental: could be infinite influence
    connection_threshold: float = 0.4
    max_degree: int = 6
    is_anchor: bool = False

    def degree_limit(self) -> int:
        return self.max_degree
