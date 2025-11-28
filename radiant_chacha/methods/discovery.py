from typing import TYPE_CHECKING

from radiant_chacha.methods import (
    add_neighbor,
    can_accept_more_neighbors,
    evict_weakest_neighbor,
    register_neighbor_attempt_failure,
    remove_neighbor,
    restore_neighbor,
)
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
        node_is_full = not can_accept_more_neighbors(obj=obj)
        if node_is_full and not obj.permissive_mode:
            logger.debug(
                f"{obj.type}: {obj.addr} saturated (neighbors: {[n.addr[:8] for n in obj.neighbors]})"
            )
            register_neighbor_attempt_failure(obj)
            continue

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
        evicted_self = None
        evicted_cand = None

        if node_is_full:
            evicted_self = evict_weakest_neighbor(obj=obj, incoming_score=score)
            if not evicted_self:
                logger.debug(
                    f"{obj.type}: {obj.addr} candidate score {score:.3f} insufficient to replace weakest neighbor"
                )
                continue
            weakest_score, weakest_neighbor = evicted_self
            logger.info(
                f"{obj.type}: {obj.addr} replacing neighbor {weakest_neighbor.type}:{weakest_neighbor.addr[:8]} with candidate {cand.type}:{cand.addr[:8]} (score {score:.3f} > {weakest_score:.3f})"
            )

        cand_is_full = not can_accept_more_neighbors(obj=cand)
        if cand_is_full and not cand.permissive_mode:
            if evicted_self:
                restore_neighbor(obj=obj, other=evicted_self[1], score=evicted_self[0])
            logger.debug(
                f"{obj.type}: {obj.addr} skipping candidate {cand.id} because it cannot reciprocate"
            )
            register_neighbor_attempt_failure(cand)
            continue

        if cand_is_full:
            evicted_cand = evict_weakest_neighbor(obj=cand, incoming_score=score)
            if not evicted_cand:
                if evicted_self:
                    restore_neighbor(
                        obj=obj, other=evicted_self[1], score=evicted_self[0]
                    )
                logger.debug(
                    f"{cand.type}: {cand.addr} failed to free capacity despite permissive mode"
                )
                register_neighbor_attempt_failure(cand)
                continue

        added_self = add_neighbor(obj=obj, other=cand, score=score)
        if not added_self:
            logger.debug(
                f"{obj.type}: {obj.addr} failed to add candidate {cand.type}:{cand.addr[:8]}"
            )
            if evicted_self:
                restore_neighbor(obj=obj, other=evicted_self[1], score=evicted_self[0])
            if evicted_cand:
                restore_neighbor(obj=cand, other=evicted_cand[1], score=evicted_cand[0])
            register_neighbor_attempt_failure(obj)
            continue

        added_cand = add_neighbor(obj=cand, other=obj, score=score)
        if not added_cand:
            logger.debug(
                f"{cand.type}: {cand.addr} failed to accept reciprocal neighbor {obj.type}:{obj.addr[:8]}"
            )
            remove_neighbor(obj=obj, other=cand)
            if evicted_self:
                restore_neighbor(obj=obj, other=evicted_self[1], score=evicted_self[0])
            if evicted_cand:
                restore_neighbor(obj=cand, other=evicted_cand[1], score=evicted_cand[0])
            register_neighbor_attempt_failure(cand)
            continue

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
