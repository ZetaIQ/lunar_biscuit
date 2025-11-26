from typing import TYPE_CHECKING

import numpy as np

from radiant_chacha.methods.movement import competition, stability

if TYPE_CHECKING:
    from radiant_chacha.core.neighbor_base import NeighborBase


def compute_gravity(obj: "NeighborBase") -> float:
    """
    Compute a scalar "gravity" value for a node based on internal heuristics.
    Gravity is a values which represents how strongly a node attracts other nodes.

    The gravity is a simple heuristic combining:
      - competition (positive when the node has more neighbors than allowed)
      - stability (average recent movement; higher stability reduces gravity)
      - deficit_score (positive when the node has fewer neighbors than desired to encourage movement to find neighbors)

    Formula implemented:
      gravity = competition - 0.5 * stability + 0.5 * deficit_score
    The logic of this formula is that high competition indicates that many nodes are attempting to connect to the subject node.
    High stability indicates that the node has a stable position. The combination of high competition and high stability suggests high "gravitational pull".
    Low competition and high stability suggest a stable node with few connections "interested" in attaching to the subject node, resulting in lower gravity.
    High competition and low stability suggest a node that is attracting connections but is unstable, leading to moderate gravity.
    Low competition and low stability suggest a node that is neither attracting connections nor stable, resulting in low gravity.
    The deficit_score encourages nodes with neighbors below their degree limit to have a compensatory increase in gravity, as all nodes should have more than 0 gravity.
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

    # desired neighbors heuristic: prefer up to min(5, degree_limit) to avoid inflating
    try:
        limit = obj.degree_limit()
        if limit == float("inf"):
            desired = (
                10.0  # Any node with infinite degree limit should desire many neighbors
            )
        if obj.type == "Block":
            desired = min(5.0, float(max(0.0, float(limit))))
        if obj.type == "Point":
            desired = 1.0  # Points should only have one neighbor, and so they should not desire more
    except Exception:
        # I cannot think of the edge case that would cause this except block to be hit, but just in case
        desired = 3.0

    deficit = max(0.0, desired - float(len(obj.neighbors)))

    gravity: float = c - 0.5 * s + 0.5 * deficit

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
