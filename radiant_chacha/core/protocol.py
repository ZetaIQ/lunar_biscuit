from typing import TYPE_CHECKING, Any, Protocol

import numpy as np

Vec3 = np.ndarray  # 3D position vector

if TYPE_CHECKING:
    from radiant_chacha.core.factory import NeighborFactory


class DegreeLimited(Protocol):
    def degree_limit(self) -> int | float: ...


class NeighborProtocol(Protocol):
    """
    A NeighborProtocol is the protocol all neighbor types must follow.


    :param id: Integer ID granted by NeighborFactory
    :type id: int
    :param data: Arbitrary data payload
    :type data: Any
    :param addr: SHA-256 address string
    :type addr: str
    :param pos: 3D position vector (numpy ndarray)
    :type pos: Vec3
    :param neighbors: List of connected NeighborProtocol instances
    :type neighbors: list[NeighborProtocol]
    :param factory: Reference to the NeighborFactory that created this node
    :type factory: NeighborFactory
    :param is_anchor: Boolean indicating if node is an anchor
    :type is_anchor: bool
    :param tick_interval: Float seconds between ticks
    :type tick_interval: float
    """

    id: int
    data: Any
    addr: str  # identity hash and lineage tracing
    pos: Vec3  # spatial position in 3D
    neighbors: list["NeighborProtocol"]
    factory: "NeighborFactory"
    type: str

    is_anchor: bool

    tick_interval: float

    async def run(self, print_stats) -> None: ...
