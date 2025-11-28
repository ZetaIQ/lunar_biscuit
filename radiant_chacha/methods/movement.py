import math
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


def _permissive_threshold(obj: "NeighborBase") -> float:
    """Return attempts threshold that triggers permissive mode (≈2×degree limit)."""
    try:
        limit = float(obj.degree_limit())
    except Exception:
        return math.inf
    if not math.isfinite(limit) or limit <= 0:
        return math.inf
    return limit * 2.0


def _update_permissive_state(obj: "NeighborBase") -> None:
    """Flip the node into permissive mode once its attempts exceed the threshold."""
    if obj.permissive_mode:
        return
    threshold = _permissive_threshold(obj)
    if obj.attempts >= threshold:
        obj.permissive_mode = True


def register_neighbor_attempt_failure(obj: "NeighborBase") -> None:
    """Increment the attempts counter and re-evaluate permissive mode."""
    obj.attempts += 1
    _update_permissive_state(obj)


def _record_neighbor_similarity(
    obj: "NeighborBase", other: "NeighborBase", score: float | None
) -> None:
    """Append a (score, neighbor) tuple and keep the similarity cache sorted."""
    try:
        numeric_score = float(score) if score is not None else 0.0
    except Exception:
        numeric_score = 0.0
    obj.neighbors_by_similarity.append((numeric_score, other))
    obj.neighbors_by_similarity.sort(key=lambda pair: pair[0])


def lowest_similarity_neighbor(
    obj: "NeighborBase",
) -> tuple[float, "NeighborBase"] | None:
    """Return the weakest neighbor entry (lowest similarity score) if any."""
    if not obj.neighbors_by_similarity:
        return None
    # ensure ordering in case external mutation occurred
    obj.neighbors_by_similarity.sort(key=lambda pair: pair[0])
    return obj.neighbors_by_similarity[0]


def remove_neighbor(obj: "NeighborBase", other: "NeighborBase") -> bool:
    """Remove a neighbor from both adjacency list and similarity cache."""
    removed = False
    if other in obj.neighbors:
        obj.neighbors.remove(other)
        removed = True
    if obj.neighbors_by_similarity:
        obj.neighbors_by_similarity = [
            pair for pair in obj.neighbors_by_similarity if pair[1] is not other
        ]
    return removed


def evict_weakest_neighbor(
    obj: "NeighborBase", incoming_score: float | None
) -> tuple[float, "NeighborBase"] | None:
    """Drop the lowest-similarity neighbor if permissive mode allows replacement."""
    if not obj.permissive_mode:
        return None
    weakest_entry = lowest_similarity_neighbor(obj)
    if not weakest_entry:
        return None
    weakest_score, weakest_neighbor = weakest_entry
    try:
        candidate_score = float(incoming_score) if incoming_score is not None else 0.0
    except Exception:
        candidate_score = 0.0
    if candidate_score <= weakest_score:
        return None
    remove_neighbor(obj=obj, other=weakest_neighbor)
    remove_neighbor(obj=weakest_neighbor, other=obj)
    return weakest_score, weakest_neighbor


def restore_neighbor(
    obj: "NeighborBase", other: "NeighborBase", score: float | None
) -> None:
    """Re-add a previously evicted neighbor (used when swaps fail halfway)."""
    add_neighbor(obj=obj, other=other, score=score)
    add_neighbor(obj=other, other=obj, score=score)


def add_neighbor(
    obj: "NeighborBase", other: "NeighborBase", *, score: float | None = None
) -> bool:
    """
    Attempt to add `other` to `obj`'s neighbor list.

    Performs safety checks:
      - rejects adding self
      - rejects duplicates
      - rejects if the receiver has reached its degree_limit()
      - adds to attempts counter if degree limit is reached

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
        register_neighbor_attempt_failure(obj)
        return False

    obj.neighbors.append(other)
    _record_neighbor_similarity(obj, other, score)
    obj.attempts = 0
    obj.permissive_mode = False
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
    Measure how much an object's connection attempts exceed its degree limit.

    Positive values indicate the node currently has more neighbors than its
    degree_limit(); zero indicates it is within its limit.

    Parameters
    ----------
    obj : NeighborBase
        Node exposing attemps (int) and degree_limit().

    Returns
    -------
    float
        max(0, len(obj.attempts) - obj.degree_limit()) as float.
    """
    limit = obj.degree_limit()
    return float(max(0, obj.attempts - limit))
