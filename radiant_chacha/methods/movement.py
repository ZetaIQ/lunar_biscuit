# ------------------------------------------------------------------
# Position & Movement
# ------------------------------------------------------------------

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from radiant_chacha.core.neighbor_base import NeighborBase, Vec3


def distance_to(obj: "NeighborBase", other: "NeighborBase") -> float:
    return float(np.linalg.norm(obj.pos - other.pos))


def can_accept_more_neighbors(obj: "NeighborBase") -> bool:
    lim = obj.degree_limit()
    return len(obj.neighbors) < lim


def add_neighbor(obj: "NeighborBase", other: "NeighborBase") -> bool:
    if other is obj:
        return False

    if other in obj.neighbors:
        return False

    if not can_accept_more_neighbors(obj=obj):
        return False

    obj.neighbors.append(other)
    return True


def move(obj: "NeighborBase", delta: "Vec3", dt: float = 1.0) -> None:
    """Move node and update velocity."""
    if obj.is_anchor:
        return

    new_pos = obj.pos + delta.astype(float)
    obj.velocity = (new_pos - obj.pos) / dt
    obj.pos = new_pos


def stability(obj: "NeighborBase") -> float:
    """
    Returns average movement between historical positions.
    Lower = more stable.
    """
    positions = []
    for entry in obj.history:
        pos = entry.get("pos")
        if isinstance(pos, np.ndarray) and pos.shape == (3,):
            positions.append(pos)

    if len(positions) < 2:
        return 0.0

    # Only take the last N entries
    positions = positions[-obj.STABILITY_WINDOW :]

    # Pairwise distances
    deltas = [np.linalg.norm(b - a) for a, b in zip(positions, positions[1:])]

    return float(sum(deltas) / len(deltas))


def competition(obj: "NeighborBase") -> float:
    """
    Positive if the node has more neighbors than its degree allows.
    Zero otherwise.
    """
    active = len(obj.neighbors)
    limit = obj.degree_limit()
    return float(max(0, active - limit))
