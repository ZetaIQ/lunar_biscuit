# ------------------------------------------------------------------
# History Snapshot
# ------------------------------------------------------------------

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from radiant_chacha.methods.address import update_addr

if TYPE_CHECKING:
    from radiant_chacha.core.neighbor_base import NeighborBase


def snapshot(obj: "NeighborBase") -> None:
    """Save full state snapshot into history dict."""
    ts = datetime.now(timezone.utc).isoformat()

    obj.history.append(
        {
            "idx": len(obj.history),  # initial snapshot is index 0
            "timestamp": ts,
            "addr": obj.addr,
            "neighbors": obj.neighbors,
            "pos": obj.pos.copy(),
            "data": obj.data,
            "gravity": obj.gravity,
            "type": obj.type,
            "velocity": obj.velocity.copy(),
        }
    )


def record_history(obj: "NeighborBase") -> None:
    """Record a new history snapshot if state has changed."""
    if len(obj.history) == 0:
        snapshot(obj)  # initial snapshot

    def _has_changed() -> bool:
        if obj.neighbors != obj.history[-1]["neighbors"]:
            print("neighbors not equal")
            return True

        if (obj.pos != obj.history[-1]["pos"]).all():
            print("pos not equal")
            return True

        if obj.gravity != obj.history[-1]["gravity"]:
            print("gravity not equal")
            return True

        if obj.type != obj.history[-1]["type"]:
            print("type not equal")
            return True

        if (obj.velocity != obj.history[-1]["velocity"]).all():
            print("velocity not equal")
            return True

        return False

    if _has_changed():
        update_addr(obj=obj)
        snapshot(obj=obj)
