import hashlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional, Type, Union

import numpy as np
from radiant_chacha.interfaces.block import Block
from radiant_chacha.interfaces.point import Point
from radiant_chacha.interfaces.sphere import Sphere

if TYPE_CHECKING:
    from radiant_chacha.core.neighbor_base import NeighborBase

_factory_token = object()

NeighborType = Union[Type[Block], Type[Point], Type[Sphere]]


class NeighborFactory:
    """Neighbor Factory for creating NeighborBase objects.
    Ensures unique IDs and addresses for each created object.


    :param _counter: Internal counter for unique IDs
    :type _counter: int
    :param nodes: List of all created NeighborBase objects
    :type nodes: list[NeighborBase]
    """

    def __init__(self):
        self._counter = 0
        self.nodes: list["NeighborBase"] = []

    def _next_id(self) -> int:
        self._counter += 1
        return self._counter

    def _generate_addr(self, birth: str) -> str:
        return hashlib.sha256(birth.encode("utf-8")).hexdigest()

    def create(
        self,
        cls: NeighborType,
        *,
        data: Optional[Any] = None,
        pos: Optional[np.ndarray] = None,
    ) -> Block | Point | Sphere:
        if not issubclass(cls, (Block, Point, Sphere)):
            raise TypeError(
                f"Factory can only create Block, Point, Sphere subclasses, not {cls}"
            )

        obj_id = self._next_id()
        birth = datetime.now(timezone.utc).isoformat()
        addr = self._generate_addr(birth)
        position = pos if pos is not None else np.zeros(3, dtype=float)

        # Construct the object with the internal token and all needed args
        obj: Block | Point | Sphere = cls(
            id=obj_id,
            data=data,
            factory=self,
            pos=position,
            addr=addr,
            _token=_factory_token,  # if you want to enforce factory-only construction
        )
        self.nodes.append(obj)
        return obj
