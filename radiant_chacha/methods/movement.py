from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from radiant_chacha.core.neighbor_base import NeighborBase, Vec3


def distance_to(obj: "NeighborBase", other: "NeighborBase") -> float:
    """
    Compute the Euclidean distance between two nodes.

    Parameters
    ----------
    obj, other : NeighborBase
        Objects that expose a numeric pos attribute (numpy array-like of shape (3,)).

    Returns
    -------
    float
        Euclidean distance between obj.pos and other.pos. Raises or propagates errors
        if positions are not valid numeric arrays.
    """
    return float(np.linalg.norm(obj.pos - other.pos))


def can_accept_more_neighbors(obj: "NeighborBase") -> bool:
    """
    Check whether a node can accept additional neighbors.

    This consults the node's degree_limit() method and compares it to the current
    neighbor list length.

    Parameters
    ----------
    obj : NeighborBase
        Node exposing neighbors (list-like) and degree_limit().

    Returns
    -------
    bool
        True if len(obj.neighbors) < obj.degree_limit(), False otherwise.
    """
    lim = obj.degree_limit()
    return len(obj.neighbors) < lim


def add_neighbor(obj: "NeighborBase", other: "NeighborBase") -> bool:
    """
    Attempt to add `other` to `obj`'s neighbor list.

    Performs safety checks:
      - rejects adding self
      - rejects duplicates
      - rejects if the receiver has reached its degree_limit()

    If the checks pass, `other` is appended to obj.neighbors.

    Parameters
    ----------
    obj : NeighborBase
        Receiver node.
    other : NeighborBase
        Candidate neighbor.

    Returns
    -------
    bool
        True if neighbor was added, False if not (for any reason).
    """
    if other is obj:
        return False

    if other in obj.neighbors:
        return False

    if not can_accept_more_neighbors(obj=obj):
        return False

    obj.neighbors.append(other)
    return True


def move(obj: "NeighborBase", delta: "Vec3", dt: float = 1.0) -> None:
    """
    Move a node by `delta` and update its velocity.

    The node's position is advanced by `delta.astype(float)`. Velocity is computed
    as (new_pos - old_pos) / dt. Anchored nodes (obj.is_anchor == True) are not moved.

    Parameters
    ----------
    obj : NeighborBase
        Node with pos and velocity attributes.
    delta : Vec3
        A numpy array-like 3-vector representing displacement.
    dt : float, optional
        Time step used to compute velocity (default 1.0).

    Notes
    -----
    This function mutates obj.pos and obj.velocity in-place.
    """
    if obj.is_anchor:
        return

    new_pos = obj.pos + delta.astype(float)
    obj.velocity = (new_pos - obj.pos) / dt
    obj.pos = new_pos


def stability(obj: "NeighborBase") -> float:
    """
    Returns average movement between historical positions.

    Lower values indicate more stable nodes (less movement between history entries).

    The function inspects obj.history for entries containing a 'pos' key with
    a numpy.ndarray of shape (3,). It uses only the last obj.STABILITY_WINDOW
    entries (if present) to compute mean pairwise displacement.

    Parameters
    ----------
    obj : NeighborBase
        Node exposing a history iterable and STABILITY_WINDOW int.

    Returns
    -------
    float
        Average Euclidean distance between consecutive stored positions.
        Returns 0.0 if insufficient history entries exist.
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
    Measure how much the node exceeds its allowed neighbor degree.

    Positive values indicate the node currently has more neighbors than its
    degree_limit(); zero indicates it is within its limit.

    Parameters
    ----------
    obj : NeighborBase
        Node exposing neighbors (list-like) and degree_limit().

    Returns
    -------
    float
        max(0, len(obj.neighbors) - obj.degree_limit()) as float.
    """
    active = len(obj.neighbors)
    limit = obj.degree_limit()
    return float(max(0, active - limit))
