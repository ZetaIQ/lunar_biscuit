# ------------------------------------------------------------------
# History Snapshot
# ------------------------------------------------------------------

from datetime import datetime, timezone
from pprint import pformat
from typing import TYPE_CHECKING

from radiant_chacha.methods.address import update_addr
from radiant_chacha.utils.log_handler import get_logger

if TYPE_CHECKING:
    from radiant_chacha.core.neighbor_base import NeighborBase

logger = get_logger(__name__, source_file=__file__)


def snapshot(obj: "NeighborBase") -> None:
    """Save full state snapshot into history dict."""
    ts = datetime.now(timezone.utc).isoformat()

    neighbor_summary = [
        {"id": nb.id, "type": nb.type, "addr": nb.addr} for nb in obj.neighbors
    ]

    obj.history.append(
        {
            "idx": len(obj.history),  # initial snapshot is index 0
            "timestamp": ts,
            "addr": obj.addr,
            "neighbors": neighbor_summary,
            "pos": obj.pos.copy(),
            "data": obj.data,
            "gravity": obj.gravity,
            "type": obj.type,
            "velocity": obj.velocity.copy(),
        }
    )
    logger.debug(f"Snapshot saved for {obj.addr}: {pformat(obj.history[-1], width=80)}")


def record_history(obj: "NeighborBase") -> None:
    """Record a new history snapshot if state has changed."""
    if len(obj.history) == 0:
        snapshot(obj)  # initial snapshot

    def _has_changed() -> bool:
        # compare neighbor summaries (not object lists) to avoid recursion
        current_neighbors = [
            {"id": nb.id, "type": nb.type, "addr": nb.addr} for nb in obj.neighbors
        ]
        last_neighbors = obj.history[-1].get("neighbors", [])

        if current_neighbors != last_neighbors:
            logger.debug(f"Neighbors changed for {obj.addr}")
            return True

        if (obj.pos != obj.history[-1]["pos"]).all():
            logger.debug(f"Position changed for {obj.addr}")
            return True

        if obj.gravity != obj.history[-1]["gravity"]:
            logger.debug(f"Gravity changed for {obj.addr}")
            return True

        if obj.type != obj.history[-1]["type"]:
            logger.debug(f"Type changed for {obj.addr}")
            return True

        if (obj.velocity != obj.history[-1]["velocity"]).all():
            logger.debug(f"Velocity changed for {obj.addr}")
            return True

        return False

    if _has_changed():
        update_addr(obj=obj)
        snapshot(obj=obj)
