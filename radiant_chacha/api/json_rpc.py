"""
JSON-RPC-style API for node management and factory control.
Exposes endpoints to create nodes, query state, and monitor simulation.
"""

from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from radiant_chacha.core.factory import NeighborFactory
from radiant_chacha.interfaces.block import Block
from radiant_chacha.interfaces.point import Point
from radiant_chacha.interfaces.sphere import Sphere
from radiant_chacha.utils.log_handler import get_logger

logger = get_logger(__name__, source_file=__file__)

app = FastAPI(
    title="Lunar Biscuit API",
    description="JSON-RPC style API for node management and simulation control",
    version="0.1.0",
)

# Global factory instance (managed by main.py)
_factory: Optional[NeighborFactory] = None


def set_factory(factory: NeighborFactory) -> None:
    """Set the global factory instance."""
    global _factory
    _factory = factory
    logger.info("[*] Factory instance registered with API")


def get_factory() -> NeighborFactory:
    """Get the global factory instance."""
    if _factory is None:
        raise RuntimeError("Factory not initialized. Call set_factory() first.")
    return _factory


# --- Request/Response Models ---


class CreateNodeRequest(BaseModel):
    """Request to create a new node."""

    node_type: str = Field(
        ..., description="Type of node: 'Block', 'Point', or 'Sphere'"
    )
    data: Any = Field(default=None, description="Arbitrary data payload for the node")
    pos: Optional[List[float]] = Field(
        default=None, description="Initial position [x, y, z]. Defaults to random."
    )


class NodeResponse(BaseModel):
    """Response representing a node's current state."""

    id: int
    type: str
    addr: str
    pos: List[float]
    velocity: List[float]
    gravity: float
    neighbors: List[int]  # list of neighbor IDs
    data: str  # stringified for JSON compatibility
    attempts: int
    is_anchor: bool


class SimulationStatusResponse(BaseModel):
    """Response with simulation status."""

    running: bool
    node_count: int
    nodes: List[NodeResponse]


# --- Endpoints ---


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    logger.debug("[-] Health check requested")
    return {"status": "ok"}


@app.post("/nodes", response_model=NodeResponse)
async def create_node(req: CreateNodeRequest) -> NodeResponse:
    """
    Create a new node and add it to the simulation.

    **Example:**
    ```json
    {
      "node_type": "Block",
      "data": {"key": "value"},
      "pos": [1.0, 2.0, 3.0]
    }
    ```
    """
    factory = get_factory()

    node_type_map = {"Block": Block, "Point": Point, "Sphere": Sphere}
    if req.node_type not in node_type_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid node_type '{req.node_type}'. Must be one of: {list(node_type_map.keys())}",
        )

    cls = node_type_map[req.node_type]
    pos = np.array(req.pos) if req.pos else np.random.rand(3) * 10

    try:
        node = factory.create(cls=cls, data=req.data, pos=pos)
        logger.info(
            f"[*] Created {req.node_type} node {node.id} ({node.addr[:8]}...) at pos {pos}"
        )
        return _node_to_response(node)
    except Exception as e:
        logger.exception(f"[!!] Failed to create node: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create node: {str(e)}")


@app.get("/nodes/{node_id}", response_model=NodeResponse)
async def get_node(node_id: int) -> NodeResponse:
    """Retrieve a specific node's state by ID."""
    factory = get_factory()

    for node in factory.nodes:
        if node.id == node_id:
            return _node_to_response(node)

    raise HTTPException(status_code=404, detail=f"Node {node_id} not found")


@app.get("/nodes", response_model=List[NodeResponse])
async def list_nodes() -> List[NodeResponse]:
    """List all nodes in the simulation."""
    factory = get_factory()
    logger.debug(f"[-] Listing {len(factory.nodes)} nodes")
    return [_node_to_response(node) for node in factory.nodes]


@app.get("/simulation/status", response_model=SimulationStatusResponse)
async def get_simulation_status() -> SimulationStatusResponse:
    """Get overall simulation status."""
    factory = get_factory()
    return SimulationStatusResponse(
        running=True,
        node_count=len(factory.nodes),
        nodes=[_node_to_response(node) for node in factory.nodes],
    )


# --- Helper functions ---


def _node_to_response(node) -> NodeResponse:
    """Convert a NeighborBase node to a NodeResponse."""
    return NodeResponse(
        id=node.id,
        type=node.type,
        addr=node.addr,
        pos=node.pos.tolist(),
        velocity=node.velocity.tolist(),
        gravity=float(node.gravity),
        neighbors=[nb.id for nb in node.neighbors],
        data=str(node.data)[:256],  # truncate for display
        attempts=node.attempts,
        is_anchor=node.is_anchor,
    )
