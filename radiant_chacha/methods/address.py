# ------------------------------------------------------------------
# Identity Hash Update
# ------------------------------------------------------------------

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from radiant_chacha.core.neighbor_base import NeighborBase


def update_addr(obj: "NeighborBase") -> None:
    """
    Compute SHA-256 hash representing this node's state.
    """
    h = hashlib.sha256()
    h.update(str(obj.id).encode())
    h.update(str(obj.data).encode())
    h.update(obj.pos.tobytes())

    # Incorporate neighbor hashes to maintain lineage
    if obj.neighbors:
        for nb in sorted(obj.neighbors, key=lambda n: n.id):
            if isinstance(nb.addr, str):
                h.update(nb.addr.encode())

    obj.addr = h.hexdigest()
