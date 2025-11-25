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
    """

    max_degree: float = float("inf")  # unlimited
    is_anchor: bool = True  # does not move by default

    def degree_limit(self) -> float:
        return self.max_degree
