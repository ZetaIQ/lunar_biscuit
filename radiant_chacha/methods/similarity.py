"""
Data similarity utilities used to decide neighbor links.

Provides:
- similarity_score(a, b) -> float in [0,1]
- should_connect(obj, other, threshold=0.5, distance_weight=0.4) -> (bool, score)
"""

import difflib
import math
from typing import TYPE_CHECKING, Any, Tuple

import numpy as np

from radiant_chacha.methods.movement import (
    distance_to,  # reuse existing distance helper
)
from radiant_chacha.utils.log_handler import get_logger

if TYPE_CHECKING:
    from radiant_chacha.core.neighbor_base import NeighborBase

logger = get_logger(__name__, source_file=__file__)


def _cosine_similarity(a: "np.ndarray", b: "np.ndarray") -> float:
    if np is None:
        return 0.0
    a_f = a.astype(float)
    b_f = b.astype(float)
    denom = np.linalg.norm(a_f) * np.linalg.norm(b_f)
    if denom == 0:
        return 0.0
    cosine = np.dot(a_f, b_f) / denom
    # rescale cosine from [-1,1] to [0,1]
    return float((cosine + 1.0) * 0.5)


def _dict_similarity(a: dict, b: dict) -> float:
    if not a and not b:
        return 1.0
    if not isinstance(a, dict) or not isinstance(b, dict):
        return 0.0
    keys_a = set(a.keys())
    keys_b = set(b.keys())
    if not keys_a and not keys_b:
        return 1.0
    shared_keys = keys_a & keys_b
    if not shared_keys:
        return 0.0
    same = 0
    for k in shared_keys:
        if a.get(k) == b.get(k):
            same += 1
    return float(same) / float(len(shared_keys))


def _string_similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    seq = difflib.SequenceMatcher(None, a, b)
    return float(seq.ratio())


def similarity_score(a: Any, b: Any) -> float:
    """
    Return similarity in [0,1] for two pieces of node data.
    Heuristics:
      - numpy arrays -> cosine similarity (rescaled to [0,1])
      - dicts -> fraction of equal values over shared keys
      - str/bytes -> difflib ratio
      - fall back to equality/hash check
    """
    try:
        # numpy vectors
        if np is not None and isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
            if a.shape == b.shape:
                return _cosine_similarity(a, b)
            # different shapes: try flatten
            return _cosine_similarity(a.flatten(), b.flatten())

        # dicts
        if isinstance(a, dict) and isinstance(b, dict):
            return _dict_similarity(a, b)

        # bytes/str
        if isinstance(a, (bytes, bytearray)) and isinstance(b, (bytes, bytearray)):
            return _string_similarity(
                a.decode(errors="ignore"), b.decode(errors="ignore")
            )
        if isinstance(a, str) and isinstance(b, str):
            return _string_similarity(a, b)

        # numbers
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            # normalized closeness: 1 - relative difference (clamped)
            if a == b:
                return 1.0
            denom = max(abs(a), abs(b), 1.0)
            diff = abs(a - b) / denom
            return float(max(0.0, 1.0 - diff))

        # fallback to equality/hash
        if a == b:
            logger.debug(
                msg="Similarity score method must fall back to equality because data from both neighbors is equal"
            )
            return 1.0
        try:
            logger.debug(
                msg="Similarity score method must fall back to hash comparison because data from both neighbors is not equal"
            )
            return 1.0 if hash(a) == hash(b) else 0.0
        except Exception:
            logger.warning(msg="Similarity score method experienced a hash exception")
            return 0.0
    except Exception as e:
        logger.error(
            msg=f"Similarity score method experienced a general exception when comparing type: {type(a)}: {a} and type: {type(b)}: {b}"
        )
        logger.error(msg=f"Similarity score general exception details: {e}")
        return 0.0


def should_connect(
    obj: "NeighborBase",
    other: "NeighborBase",
    threshold: float = 0.5,
    distance_weight: float = 0.4,
) -> Tuple[bool, float]:
    """
    Decide whether `obj` should attempt to connect to `other`.

    Combines data similarity and spatial proximity:
      final_score = (1 - distance_weight) * data_sim + distance_weight * proximity_score

    proximity_score is 1.0 for zero distance and decays with distance. If either node exposes
    an `influence_radius` attribute it will be used to normalize distance; otherwise a simple
    1/(1+dist) scaling is applied.

    Returns (should_connect: bool, score: float)
    """
    # Prefer the formal protocol attribute 'data' but fall back to common legacy names
    data_a = obj.data

    data_b = other.data

    data_sim = similarity_score(data_a, data_b)

    # compute a proximity score in [0,1]
    try:
        dist = distance_to(obj, other)
    except Exception:
        dist = math.inf

    # choose normalization radius
    radius_a = obj.influence_radius
    radius_b = other.influence_radius
    radius = None
    if isinstance(radius_a, (int, float)) and isinstance(radius_b, (int, float)):
        radius = max(1.0, (radius_a + radius_b) / 2.0)
    elif isinstance(radius_a, (int, float)):
        radius = max(1.0, radius_a)
    elif isinstance(radius_b, (int, float)):
        radius = max(1.0, radius_b)

    if math.isfinite(dist):
        if radius:
            proximity = max(
                0.0, 1.0 - (dist / (radius * 2.0))
            )  # decay over twice the radius
        else:
            proximity = 1.0 / (1.0 + dist)
    else:
        proximity = 0.0

    score = (1.0 - distance_weight) * float(data_sim) + float(distance_weight) * float(
        proximity
    )
    score = float(max(0.0, min(1.0, score)))

    should = score >= float(threshold)
    return should, score
