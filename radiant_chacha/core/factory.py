import asyncio
import hashlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional, Set, Type, Union

import numpy as np

from radiant_chacha.interfaces.block import Block
from radiant_chacha.interfaces.point import Point
from radiant_chacha.interfaces.sphere import Sphere
from radiant_chacha.utils.log_handler import get_logger

if TYPE_CHECKING:
    from radiant_chacha.core.neighbor_base import NeighborBase

logger = get_logger(__name__, source_file=__file__)

_factory_token = object()

NeighborType = Union[Type[Block], Type[Point], Type[Sphere]]


class NeighborFactory:
    """Neighbor Factory for creating NeighborBase objects.
    Ensures unique IDs and addresses for each created object.
    Each node spawns its own async task to self-tick.

    :param _counter: Internal counter for unique IDs
    :type _counter: int
    :param nodes: List of all created NeighborBase objects
    :type nodes: list[NeighborBase]
    :param _tasks: Set of running asyncio tasks for node ticking
    :type _tasks: Set[asyncio.Task]
    :param _event_loop: Optional asyncio event loop for spawning tasks
    :type _event_loop: Optional[asyncio.AbstractEventLoop]
    """

    def __init__(self):
        self._counter = 0
        self.nodes: list["NeighborBase"] = []
        self._tasks: Set[asyncio.Task] = set()
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the event loop for spawning node tasks."""
        self._event_loop = loop
        logger.info("[*] Factory event loop set for node self-ticking")

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
        **overrides: Any,
    ) -> Block | Point | Sphere:
        if not issubclass(cls, (Block, Point, Sphere)):
            raise TypeError(
                f"Factory can only create Block, Point, Sphere subclasses, not {cls}"
            )

        obj_id = self._next_id()
        birth = datetime.now(timezone.utc).isoformat()
        addr = self._generate_addr(birth)
        position = pos if pos is not None else np.random.rand(3) * 10

        # Construct the object with the internal token and all needed args
        init_kwargs = {
            "id": obj_id,
            "data": data,
            "factory": self,
            "pos": position,
            "addr": addr,
            "_token": _factory_token,  # enforce factory-only construction
        }
        init_kwargs.update(overrides)

        obj: Block | Point | Sphere = cls(**init_kwargs)
        self.nodes.append(obj)
        logger.info(
            f"[*] Created {cls.__name__} node {obj_id} ({addr[:8]}...) at pos {position}"
        )

        # Spawn async task for this node to self-tick
        if self._event_loop:
            task = self._event_loop.create_task(obj.run())
            self._tasks.add(task)
            task.add_done_callback(lambda t: self._tasks.discard(t))
            logger.debug(f"[-] Node {obj_id} spawned self-tick task")

        return obj

    async def cancel_all_tasks(self) -> None:
        """Cancel all node ticking tasks."""
        logger.info("[*] Cancelling all node tasks...")
        for task in list(self._tasks):
            task.cancel()
        # Wait for all tasks to finish cancellation
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
