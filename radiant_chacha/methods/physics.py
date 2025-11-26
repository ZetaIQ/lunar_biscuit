# ------------------------------------------------------------------
# Gravity Calculation
# ------------------------------------------------------------------

from typing import TYPE_CHECKING

import numpy as np
from radiant_chacha.methods.movement import competition, stability

if TYPE_CHECKING:
    from radiant_chacha.core.neighbor_base import NeighborBase


def compute_gravity(obj: "NeighborBase") -> float:
    s: float = stability(obj=obj)
    c: float = competition(obj=obj)

    gravity: float = c - 0.5 * s

    # Clamp to reasonable bounds
    gravity = max(0.0, min(20.0, gravity))

    return float(gravity)


def local_gravity_vector(obj: "NeighborBase") -> np.ndarray:
    """
    Returns the normalized direction toward the centroid
    of this node's neighbors.
    """
    if not obj.neighbors:
        return np.zeros(3, dtype=float)

    arr = np.array([nb.pos for nb in obj.neighbors])
    centroid = np.mean(arr, axis=0)
    direction = centroid - obj.pos

    norm = np.linalg.norm(direction)
    if norm == 0:
        return np.zeros(3)

    return direction / norm


def apply_gravity(obj: "NeighborBase", dt: float = 1.0) -> None:
    if obj.is_anchor:
        return

    # Compute gravity scalar and update attribute
    obj.gravity = compute_gravity(obj)

    # Get normalized direction vector
    direction = local_gravity_vector(obj)

    if np.linalg.norm(direction) == 0:
        return  # No movement if no direction

    # Calculate movement delta vector
    delta = direction * obj.gravity * dt

    # Update position and velocity
    obj.pos = obj.pos + delta
    obj.velocity = delta / dt
