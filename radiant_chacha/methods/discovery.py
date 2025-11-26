from typing import TYPE_CHECKING

from radiant_chacha.methods import add_neighbor, can_accept_more_neighbors
from radiant_chacha.methods.similarity import should_connect

if TYPE_CHECKING:
    from radiant_chacha.core.neighbor_base import NeighborBase


def discover_and_negotiate(obj: "NeighborBase") -> None:
    """Obtain candidate list heuristically from the node or its factory"""
    # --- Neighbor discovery / negotiation (basic) ---
    candidates = []
    factory = obj.factory
    if factory is not None and hasattr(factory, "nodes"):
        try:
            candidates = list(factory.nodes)
            print(f"discovered {len(candidates)} candidates from factory\n")
        except Exception:
            candidates = []

    # run a simple one-pass discovery (stop early if this node is full)
    for cand in candidates:
        if cand is obj:
            print(f"{obj.type}: {obj.addr} skipping self")
            continue
        if cand in obj.neighbors:
            print(
                f"{obj.type}: {obj.addr} skipping existing neighbor: {cand.type}: {cand.addr}\n"
            )
            continue
        # stop if this node can't accept more neighbors
        if not can_accept_more_neighbors(obj=obj):
            print(f"{obj.type}: {obj.addr} full, stop discovery")
            print(
                f"{obj.type}: {obj.addr} neighbors: {[n.addr for n in obj.neighbors]}"
            )
            print(f"{obj.type}: {obj.addr} total attempt count: {obj.attempts}\n")
            break

        ok, score = should_connect(
            obj=obj, other=cand, threshold=obj.connection_threshold
        )
        if not ok:
            print(
                f"{obj.type}: {obj.addr} rejected candidate: {cand.type}: {cand.addr} with score {score:.3f}"
            )
            print(
                f"Because threshold is {obj.connection_threshold}, score is {score}, and ok is {ok}\n"
            )
            continue

        # add neighbor, allow attempts to increment if needed
        print(
            f"attempting to connect {obj.type}: {obj.addr} to candidate: {cand.type}: {cand.addr} with score {score:.3f}\n"
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
        except Exception as e:
            print(f"{obj.type}: {obj.addr}: failed to record history event\n")
            print(f"Exception: {e}\n")
            pass
    # --- end neighbor discovery ---
