from dataclasses import dataclass

from radiant_chacha.core.neighbor_base import NeighborBase


@dataclass
class Point(NeighborBase):
    """
    A Point:
    - Has only 1 neighbor (a single parent link)
    - Moves freely
    - Has the simplest role in the network
    """

    max_degree: int = 1
    is_anchor: bool = False

    def degree_limit(self) -> int:
        return self.max_degree
