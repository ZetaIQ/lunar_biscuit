from dataclasses import dataclass

from radiant_chacha.core.neighbor_base import NeighborBase


@dataclass
class Block(NeighborBase):
    """
    A Block has:
    - Exactly 6 canonical neighbor slots (±x, ±y, ±z)
    - Movement allowed
    - No special anchoring
    """

    max_degree: int = 6
    is_anchor: bool = False

    def degree_limit(self) -> int:
        return self.max_degree
