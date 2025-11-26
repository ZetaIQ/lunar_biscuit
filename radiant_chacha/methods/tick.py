# ------------------------------------------------------------------
# Default loop step
# ------------------------------------------------------------------

from pprint import pprint
from typing import TYPE_CHECKING

from radiant_chacha.methods.history import record_history
from radiant_chacha.methods.physics import apply_gravity

if TYPE_CHECKING:
    from lunar_biscuit.radiant_chacha.core import NeighborBase


def tick(obj: "NeighborBase", dt: float = 1.0, print_stats: bool = False) -> None:
    """
    Each node runs autonomous logic here:
    - Gravity forces
    - Neighbor negotiation
    - Position updates
    - Hash updates (optional timing)
    """
    # Apply physics-based movement
    apply_gravity(obj=obj, dt=dt)

    # Placeholder: future neighbor negotiation, pruning, etc.

    # Record history snapshot
    record_history(obj=obj)

    # Optionally print positions and gravity
    if print_stats:
        print(
            f"Node {obj.id} ({type(obj).__name__}): Pos={obj.pos} Gravity={obj.gravity:.3f}\n"
            f"{'-' * 40}\n"
            f"Node {obj.id} ({type(obj).__name__}): History={pprint(object=obj.history, width=80, indent=2, compact=False, depth=2)}\n"
            f"{'-' * 40}\n"
        )
