from dataclasses import dataclass

from radiant_chacha.core.neighbor_base import NeighborBase


@dataclass
class Sphere(NeighborBase):
    """
    A Sphere:
    - Represents a stable hub/focal data region
    - Infinite (or very large) degree
    - Typically acts as an anchor
    - Usually does NOT move


    :param influence_radius: Influence radius for connection strength (default: 1)
    :type influence_radius: float
    :param connection_threshold: Threshold for forming connections (default: 0.2)
    :type connection_threshold: float
    :param max_degree: Maximum number of neighbors (default: infinite)
    :type max_degree: float
    :param is_anchor: Indicates if the Sphere is an anchor (default: True)
    :type is_anchor: bool
    """

    influence_radius: float = float(1)  # experimental: could be infinite influence
    connection_threshold: float = 0.2
    max_degree: float = float("inf")  # unlimited
    is_anchor: bool = True  # does not move by default

    def degree_limit(self) -> float:
        return self.max_degree
