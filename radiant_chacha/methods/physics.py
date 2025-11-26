from typing import TYPE_CHECKING

import numpy as np
from radiant_chacha.methods.movement import competition, stability

if TYPE_CHECKING:
    from radiant_chacha.core.neighbor_base import NeighborBase


def compute_gravity(obj: "NeighborBase") -> float:
    """
    Compute a scalar "gravity" value for a node based on internal heuristics.

    The gravity is a simple heuristic combining:
      - competition (positive when the node has more neighbors than allowed)
      - stability (average recent movement; higher stability reduces gravity)

    Formula implemented:
      gravity = competition - 0.5 * stability
    The result is clamped to [0.0, 20.0] to avoid extreme steps.

    Parameters
    ----------
    obj : NeighborBase
        Node exposing stability() window and neighbors; this function calls
        movement.stability(obj) and movement.competition(obj).

    Returns
    -------
    float
        Non-negative gravity scalar used to scale movement in apply_gravity.
    """
    s: float = stability(obj=obj)
    c: float = competition(obj=obj)

    gravity: float = c - 0.5 * s

    # Clamp to reasonable bounds
    gravity = max(0.0, min(20.0, gravity))

    return float(gravity)


def local_gravity_vector(obj: "NeighborBase") -> np.ndarray:
    """
    Return the normalized direction vector pointing toward the centroid of neighbors.

    If the node has no neighbors, or the centroid equals the node position, this
    returns a zero vector of shape (3,).

    Parameters
    ----------
    obj : NeighborBase
        Node exposing a sequence of neighbors where each neighbor has a .pos attribute.

    Returns
    -------
    numpy.ndarray
        A length-3 normalized vector (float dtype). Zero vector when no preferred direction.
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
    """
    Apply computed gravity to mutate the node's position and velocity.

    Steps:
      - If obj.is_anchor is True, no changes are made.
      - Compute and store obj.gravity via compute_gravity(obj).
      - Obtain direction with local_gravity_vector(obj). If zero, no movement.
      - Compute delta = direction * obj.gravity * dt.
      - Update obj.pos and obj.velocity accordingly.

    Parameters
    ----------
    obj : NeighborBase
        Node with pos, velocity and is_anchor attributes (and writable gravity).
    dt : float, optional
        Time-step scale for position/velocity updates (default 1.0).

    Notes
    -----
    This function mutates obj.pos and obj.velocity in-place.
    """
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
