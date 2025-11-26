from dataclasses import dataclass

from radiant_chacha.core.neighbor_base import NeighborBase


@dataclass
class Point(NeighborBase):
    """
    A Point:
    - Has only 1 neighbor (a single parent link)
    - Moves freely
    - Has the simplest role in the network


    :param influence_radius: Influence radius for connection strength (default: 5)
    :type influence_radius: float
    :param connection_threshold: Threshold for forming connections (default: 0.8)
    :type connection_threshold: float
    :param max_degree: Maximum number of neighbors (default: 1)
    :type max_degree: int
    :param is_anchor: Indicates if the Point is an anchor (default: False)
    :type is_anchor: bool
    """

    influence_radius: float = float(5)  # experimental: could be infinite influence
    connection_threshold: float = 0.8
    max_degree: int = 1
    is_anchor: bool = False

    def degree_limit(self) -> int:
        return self.max_degree
