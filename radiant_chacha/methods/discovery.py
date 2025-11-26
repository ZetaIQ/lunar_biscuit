from typing import TYPE_CHECKING

from radiant_chacha.methods import add_neighbor, can_accept_more_neighbors
from radiant_chacha.methods.similarity import should_connect
from radiant_chacha.utils.log_handler import get_logger

if TYPE_CHECKING:
    from radiant_chacha.core.neighbor_base import NeighborBase

logger = get_logger(__name__, source_file=__file__)


def discover_and_negotiate(obj: "NeighborBase") -> None:
    """Obtain candidate list heuristically from the node or its factory"""
    # --- Neighbor discovery / negotiation (basic) ---
    candidates = []
    factory = obj.factory
    if factory is not None and hasattr(factory, "nodes"):
        try:
            candidates = list(factory.nodes)
            logger.debug(f"Discovered {len(candidates)} candidates from factory")
        except Exception:
            candidates = []

    # run a simple one-pass discovery (stop early if this node is full)
    for cand in candidates:
        if cand is obj:
            logger.debug(f"{obj.type}: {obj.addr} skipping self")
            continue
        if cand in obj.neighbors:
            logger.debug(
                f"{obj.type}: {obj.addr} skipping existing neighbor: {cand.type}: {cand.addr}"
            )
            continue
        # stop if this node can't accept more neighbors
        if not can_accept_more_neighbors(obj=obj):
            logger.info(f"{obj.type}: {obj.addr} full, stop discovery")
            logger.debug(
                f"{obj.type}: {obj.addr} neighbors: {[n.addr[:8] for n in obj.neighbors]}"
            )
            logger.debug(f"{obj.type}: {obj.addr} total attempt count: {obj.attempts}")
            break

        ok, score = should_connect(
            obj=obj, other=cand, threshold=obj.connection_threshold
        )
        if not ok:
            logger.debug(
                f"{obj.type}: {obj.addr} rejected candidate: {cand.type}: {cand.addr} with score {score:.3f}"
            )
            logger.debug(
                f"threshold={obj.connection_threshold}, score={score:.3f}, ok={ok}"
            )
            continue

        # add neighbor, allow attempts to increment if needed
        logger.info(
            f"Attempting to connect {obj.type}: {obj.addr} to candidate: {cand.type}: {cand.addr} with score {score:.3f}"
        )
        add_neighbor(obj=obj, other=cand)
        add_neighbor(obj=cand, other=obj)
        # record negotiation result in history
        try:
            obj.history[-1]["neighbor_event"] = {
                "event": "connected",
                "peer": cand.id,
                "score": score,
            }
        except Exception:
            logger.exception(f"{obj.type}: {obj.addr}: failed to record history event")
    # --- end neighbor discovery ---
