from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List

import numpy as np
from radiant_chacha.core.protocol import NeighborProtocol, Vec3


@dataclass
class NeighborBase(NeighborProtocol, ABC):
    id: int
    data: Any

    # --- Identity Hash ---
    addr: str = ""  # SHA-256 string (set at init)

    # --- Spatial Position ---
    pos: Vec3 = field(default_factory=lambda: np.zeros(3, dtype=float))

    # --- Physics ---
    velocity: Vec3 = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    gravity: float = np.float64(0.0)

    neighbors: List[NeighborProtocol] = field(default_factory=list)

    is_anchor: bool = False

    history: dict[str, dict[str, Any]] = field(default_factory=dict)

    STABILITY_WINDOW: int = 10

    _token: object | None = None

    # ------------------------------------------------------------------

    @abstractmethod
    def degree_limit(self) -> int | float:
        """Maximum allowable neighbors. float('inf') means unlimited."""
        ...

    # ------------------------------------------------------------------
    # Identity Hash Update
    # ------------------------------------------------------------------

    def update_addr(self) -> None:
        """
        Compute SHA-256 hash representing this node's state.
        Does NOT include position.
        """
        h = hashlib.sha256()
        h.update(str(self.id).encode())
        h.update(str(self.data).encode())

        # Incorporate neighbor hashes to maintain lineage
        for nb in sorted(self.neighbors, key=lambda n: n.id):
            if isinstance(nb.addr, str):
                h.update(nb.addr.encode())

        self.addr = h.hexdigest()

    # ------------------------------------------------------------------
    # History Snapshot
    # ------------------------------------------------------------------
    def snapshot(self) -> None:
        """Save full state snapshot into history dict."""
        ts = datetime.now(timezone.utc).isoformat()

        self.history[ts] = {
            "addr": self.addr,
            "pos": self.pos.copy(),
            "data": self.data,
            "gravity": self.gravity,
            "type": self.__class__.__name__,
            "velocity": self.velocity.copy(),
        }

    # ------------------------------------------------------------------
    # Position & Movement
    # ------------------------------------------------------------------

    def distance_to(self, other: NeighborProtocol) -> float:
        return float(np.linalg.norm(self.pos - other.pos))

    def can_accept_more_neighbors(self) -> bool:
        lim = self.degree_limit()
        return len(self.neighbors) < lim

    def add_neighbor(self, other: NeighborProtocol) -> bool:
        if other is self:
            return False

        if other in self.neighbors:
            return False

        if not self.can_accept_more_neighbors():
            return False

        self.neighbors.append(other)
        return True

    def move(self, delta: Vec3, dt: float = 1.0) -> None:
        """Move node and update velocity."""
        if self.is_anchor:
            return

        new_pos = self.pos + delta.astype(float)
        self.velocity = (new_pos - self.pos) / dt
        self.pos = new_pos

    def stability(self) -> float:
        """
        Returns average movement between historical positions.
        Lower = more stable.
        """
        positions = []
        for entry in self.history.values():
            pos = entry.get("pos")
            if isinstance(pos, np.ndarray) and pos.shape == (3,):
                positions.append(pos)

        if len(positions) < 2:
            return 0.0

        # Only take the last N entries
        positions = positions[-self.STABILITY_WINDOW :]

        # Pairwise distances
        deltas = [np.linalg.norm(b - a) for a, b in zip(positions, positions[1:])]

        return float(sum(deltas) / len(deltas))

    def competition(self) -> float:
        """
        Positive if the node has more neighbors than its degree allows.
        Zero otherwise.
        """
        active = len(self.neighbors)
        limit = self.degree_limit()
        return float(max(0, active - limit))

    # ------------------------------------------------------------------
    # Gravity Calculation
    # ------------------------------------------------------------------
    def compute_gravity(self) -> float:
        s = self.stability()
        c = self.competition()

        gravity = c - 0.5 * s

        # Clamp to reasonable bounds
        gravity = max(0.0, min(20.0, gravity))

        return float(gravity)

    def local_gravity_vector(self) -> np.ndarray:
        """
        Returns the normalized direction toward the centroid
        of this node's neighbors.
        """
        if not self.neighbors:
            return np.zeros(3, dtype=float)

        arr = np.array([nb.pos for nb in self.neighbors])
        centroid = np.mean(arr, axis=0)
        direction = centroid - self.pos

        norm = np.linalg.norm(direction)
        if norm == 0:
            return np.zeros(3)

        return direction / norm

    def apply_gravity(self, dt: float = 1.0) -> None:
        if self.is_anchor:
            return

        # Compute gravity scalar and update attribute
        self.gravity = self.compute_gravity()

        # Get normalized direction vector
        direction = self.local_gravity_vector()

        if np.linalg.norm(direction) == 0:
            return  # No movement if no direction

        # Calculate movement delta vector
        delta = direction * self.gravity * dt

        # Update position and velocity
        self.pos = self.pos + delta
        self.velocity = delta / dt

        # Log the new state
        self.snapshot()

    # ------------------------------------------------------------------
    # Default loop step
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> None:
        """
        Each node runs autonomous logic here:
        - Gravity forces
        - Neighbor negotiation
        - Position updates
        - Hash updates (optional timing)
        """
        self.apply_gravity(dt)

    def __post_init__(self):
        if getattr(self, "_token", None) is None:
            raise RuntimeError(
                "Use NeighborFactory to create instances, do not instantiate directly."
            )
