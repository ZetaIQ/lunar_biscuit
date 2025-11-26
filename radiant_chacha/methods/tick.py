# ...existing code...
# ------------------------------------------------------------------
# Default loop step
# ------------------------------------------------------------------

from pprint import pprint
from typing import TYPE_CHECKING

from radiant_chacha.methods.discovery import discover_and_negotiate
from radiant_chacha.methods.history import record_history
from radiant_chacha.methods.physics import apply_gravity

if TYPE_CHECKING:
    from lunar_biscuit.radiant_chacha.core import NeighborBase


def tick(obj: "NeighborBase", dt: float = 1.0, print_stats: bool = False) -> None:
    """
    Each node runs autonomous logic here:
    - Apply gravity/physics
    - Neighbor negotiation and pruning
    - Position/history updates

    Neighbor discovery:
      - Attempts to find candidates from obj.factory.nodes, obj.all_nodes, or
        obj.discovery_targets (preferred in that order).
      - Uses should_connect(...) to score data+proximity and, if both sides
        can accept more neighbors, links them via add_neighbor on both nodes.
    """
    # Record history snapshot
    record_history(obj=obj)

    # Discover and negotiate neighbors
    discover_and_negotiate(obj=obj)

    # Apply physics-based movement
    apply_gravity(obj=obj, dt=dt)

    # Optionally print positions and gravity
    if print_stats:
        print(
            f"Node {obj.id} ({type(obj).__name__}): Pos={obj.pos} Gravity={obj.gravity:.3f}"
        )
        print("-" * 40)
        print("History:")
        pprint(obj.history, width=80, indent=2, compact=False)
        print("-" * 40)
