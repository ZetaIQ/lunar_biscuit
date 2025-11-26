from typing import Any, Protocol

import numpy as np

Vec3 = np.ndarray  # 3D position vector


class DegreeLimited(Protocol):
    def degree_limit(self) -> int | float: ...


class NeighborProtocol(Protocol):
    id: int
    data: Any
    addr: str  # identity hash and lineage tracing
    pos: Vec3  # spatial position in 3D
    neighbors: list["NeighborProtocol"]

    is_anchor: bool

    tick_interval: float

    async def run(self, print_stats) -> None: ...
