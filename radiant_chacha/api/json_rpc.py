"""
JSON-RPC-style API for node management and factory control.
Exposes endpoints to create nodes, query state, monitor simulation,
and stream visualization updates.
"""

import asyncio
import base64
import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np
from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from radiant_chacha.config import STREAM_UPDATE_INTERVAL
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

# Visualizer HTML content (served via /visualizer)
VISUALIZER_HTML_PATH = (
    Path(__file__).resolve().parents[2]
    / "radiant_chacha"
    / "visualization"
    / "static"
    / "visualizer.html"
)
VISUALIZER_STATIC_DIR = VISUALIZER_HTML_PATH.parent

app.mount(
    "/visualizer_static",
    StaticFiles(directory=VISUALIZER_STATIC_DIR),
    name="visualizer_static",
)


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
    data_format: Literal["json", "ndarray", "bytes", "bytearray"] = Field(
        default="json",
        description=(
            "How to interpret the 'data' field. Use 'ndarray' for nested lists, "
            "and base64 strings for bytes/bytearray."
        ),
    )
    connection_threshold: Optional[float] = Field(
        default=None, description="Override node connection threshold"
    )
    influence_radius: Optional[float] = Field(
        default=None, description="Override node influence radius"
    )
    attempts: Optional[int] = Field(
        default=None, description="Seed the attempts counter"
    )
    velocity: Optional[List[float]] = Field(
        default=None, description="Override velocity vector [vx, vy, vz]"
    )
    gravity: Optional[float] = Field(
        default=None, description="Override gravity scalar"
    )
    is_anchor: Optional[bool] = Field(
        default=None, description="Explicitly set anchor status"
    )
    stability_window: Optional[int] = Field(
        default=None, description="Override STABILITY_WINDOW for the node"
    )
    tick_interval: Optional[float] = Field(
        default=None, description="Override tick interval in seconds"
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
    data_serialized: Any | None = None
    attempts: int
    is_anchor: bool
    data_type: str
    connection_threshold: float
    influence_radius: float
    stability_window: int
    tick_interval: float


class SimulationStatusResponse(BaseModel):
    """Response with simulation status."""

    running: bool
    node_count: int
    nodes: List[NodeResponse]


class HistoryNeighbor(BaseModel):
    """Neighbor summary stored in history entries."""

    id: int
    addr: str
    type: str


class HistoryEntryResponse(BaseModel):
    """Serialized history snapshot for a node."""

    idx: int
    timestamp: str
    addr: str
    pos: List[float]
    velocity: List[float]
    gravity: float
    type: str | None = None
    neighbors: List[HistoryNeighbor]
    data_summary: str
    data_type: str


# --- Endpoints ---


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint showing available API endpoints."""
    return {
        "service": "Lunar Biscuit API",
        "version": "0.1.0",
        "endpoints": {
            "documentation": "/docs (Swagger UI) or /redoc (ReDoc)",
            "health": "/health",
            "visualizer": "GET /visualizer",
            "websocket": "WS /ws/nodes",
            "nodes": {
                "list_all": "GET /nodes",
                "create": "POST /nodes",
                "get_one": "GET /nodes/{node_id}",
            },
            "simulation": {
                "status": "GET /simulation/status",
            },
        },
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    logger.debug("[-] Health check requested")
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """Return empty favicon response to avoid 404 noise."""
    return Response(status_code=204)


@app.get("/visualizer", response_class=HTMLResponse)
async def visualizer_page() -> HTMLResponse:
    """Serve the Three.js-based visualizer."""
    if not VISUALIZER_HTML_PATH.exists():
        raise HTTPException(status_code=404, detail="Visualizer asset missing")
    return HTMLResponse(VISUALIZER_HTML_PATH.read_text(encoding="utf-8"))


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
    pos = (
        _vector_from_list(req.pos, "pos")
        if req.pos is not None
        else np.random.rand(3) * 10
    )

    overrides: Dict[str, Any] = {}
    if req.connection_threshold is not None:
        overrides["connection_threshold"] = req.connection_threshold
    if req.influence_radius is not None:
        overrides["influence_radius"] = req.influence_radius
    if req.attempts is not None:
        overrides["attempts"] = req.attempts
    if req.velocity is not None:
        overrides["velocity"] = _vector_from_list(req.velocity, "velocity")
    if req.gravity is not None:
        overrides["gravity"] = req.gravity
    if req.is_anchor is not None:
        overrides["is_anchor"] = req.is_anchor
    if req.stability_window is not None:
        overrides["STABILITY_WINDOW"] = req.stability_window
    if req.tick_interval is not None:
        overrides["tick_interval"] = req.tick_interval

    data_payload = _interpret_data(req.data, req.data_format)

    try:
        node = factory.create(
            cls=cls,
            data=data_payload,
            pos=pos,
            **overrides,
        )
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


@app.get("/nodes/{node_id}/history", response_model=List[HistoryEntryResponse])
async def get_node_history(node_id: int) -> List[HistoryEntryResponse]:
    """Return serialized history snapshots for a node."""
    factory = get_factory()

    for node in factory.nodes:
        if node.id == node_id:
            history = getattr(node, "history", []) or []
            return [_history_entry_to_response(entry) for entry in history]

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


def _summarize_data(value: Any) -> Tuple[str, str]:
    """Return a readable description and python type name."""
    if value is None:
        return ("", "NoneType")

    if isinstance(value, np.ndarray):
        return (
            f"ndarray shape={value.shape}, dtype={value.dtype}",
            "numpy.ndarray",
        )

    if isinstance(value, bytes):
        return (f"bytes len={len(value)}", "bytes")

    if isinstance(value, bytearray):
        return (f"bytearray len={len(value)}", "bytearray")

    text = str(value)
    if len(text) > 256:
        text = text[:253] + "..."
    return (text, type(value).__name__)


def _serialize_data_payload(value: Any) -> Any:
    """Produce a JSON-serializable representation of the node data."""
    if value is None:
        return None

    if isinstance(value, np.ndarray):
        return {
            "format": "ndarray",
            "dtype": str(value.dtype),
            "shape": value.shape,
            "value": value.tolist(),
        }

    if isinstance(value, bytes):
        return {
            "format": "bytes",
            "length": len(value),
            "value": base64.b64encode(value).decode("ascii"),
        }

    if isinstance(value, bytearray):
        raw = bytes(value)
        return {
            "format": "bytearray",
            "length": len(value),
            "value": base64.b64encode(raw).decode("ascii"),
        }

    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _vector_from_list(values: List[float], label: str) -> np.ndarray:
    if len(values) != 3:
        raise HTTPException(
            status_code=400, detail=f"{label} must contain exactly 3 numeric values"
        )
    try:
        return np.array(values, dtype=np.float64)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=400, detail=f"Invalid {label}: {exc}") from exc


def _interpret_data(payload: Any, fmt: str) -> Any:
    if payload is None:
        return None

    if fmt == "json":
        return payload

    if fmt == "ndarray":
        if not isinstance(payload, list):
            raise HTTPException(
                status_code=400,
                detail="ndarray data must be provided as a nested JSON list",
            )
        try:
            return np.array(payload)
        except Exception as exc:  # pragma: no cover - user input validation
            raise HTTPException(
                status_code=400, detail=f"Unable to convert to ndarray: {exc}"
            ) from exc

    if fmt in {"bytes", "bytearray"}:
        if not isinstance(payload, str):
            raise HTTPException(
                status_code=400,
                detail=f"{fmt} data must be a base64-encoded string",
            )
        try:
            decoded = base64.b64decode(payload)
        except Exception as exc:  # pragma: no cover - user input validation
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 payload for {fmt}: {exc}",
            ) from exc
        return decoded if fmt == "bytes" else bytearray(decoded)

    raise HTTPException(status_code=400, detail=f"Unsupported data_format '{fmt}'")


def _node_to_response(node) -> NodeResponse:
    """Convert a NeighborBase node to a NodeResponse."""
    data_summary, data_type = _summarize_data(node.data)
    return NodeResponse(
        id=node.id,
        type=node.type,
        addr=node.addr,
        pos=node.pos.tolist(),
        velocity=node.velocity.tolist(),
        gravity=float(node.gravity),
        neighbors=[nb.id for nb in node.neighbors],
        data=data_summary,
        data_serialized=_serialize_data_payload(node.data),
        attempts=node.attempts,
        is_anchor=node.is_anchor,
        data_type=data_type,
        connection_threshold=float(node.connection_threshold),
        influence_radius=float(node.influence_radius),
        stability_window=int(getattr(node, "STABILITY_WINDOW", 0)),
        tick_interval=float(getattr(node, "tick_interval", 0.0)),
    )


def _node_packet(node) -> Dict[str, Any]:
    """Serialize node state for websocket payloads."""
    data_summary, data_type = _summarize_data(node.data)
    return {
        "id": node.id,
        "type": node.type,
        "addr": node.addr,
        "pos": node.pos.tolist(),
        "velocity": node.velocity.tolist(),
        "gravity": float(node.gravity),
        "neighbors": [nb.id for nb in node.neighbors],
        "is_anchor": node.is_anchor,
        "attempts": node.attempts,
        "connection_threshold": float(node.connection_threshold),
        "influence_radius": float(node.influence_radius),
        "stability_window": int(getattr(node, "STABILITY_WINDOW", 0)),
        "tick_interval": float(getattr(node, "tick_interval", 0.0)),
        "data": data_summary,
        "data_type": data_type,
        "data_serialized": _serialize_data_payload(node.data),
    }


def _vector_like_to_list(value: Any) -> List[float]:
    if value is None:
        return []
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (list, tuple)):
        return [float(v) for v in value]
    try:
        return [float(value)]
    except (TypeError, ValueError):
        return []


def _history_entry_to_response(entry: Dict[str, Any]) -> HistoryEntryResponse:
    data_summary, data_type = _summarize_data(entry.get("data"))
    neighbors_raw = entry.get("neighbors", []) or []
    neighbors = [
        HistoryNeighbor(
            id=int(nb.get("id", -1)),
            addr=str(nb.get("addr", "")),
            type=nb.get("type"),
        )
        for nb in neighbors_raw
        if nb is not None
    ]
    return HistoryEntryResponse(
        idx=int(entry.get("idx", 0)),
        timestamp=str(entry.get("timestamp", "")),
        addr=str(entry.get("addr", "")),
        pos=_vector_like_to_list(entry.get("pos")),
        velocity=_vector_like_to_list(entry.get("velocity")),
        gravity=float(entry.get("gravity", 0.0)),
        type=entry.get("type"),
        neighbors=neighbors,
        data_summary=data_summary,
        data_type=data_type,
    )


@app.websocket("/ws/nodes")
async def websocket_nodes(websocket: WebSocket) -> None:
    """Push live node snapshots to connected visualizers."""
    await websocket.accept()
    logger.info("[*] Visualizer websocket client connected")
    try:
        while True:
            factory = get_factory()
            payload = {
                "node_count": len(factory.nodes),
                "timestamp": asyncio.get_event_loop().time(),
                "nodes": [_node_packet(node) for node in factory.nodes],
            }
            await websocket.send_json(payload)
            await asyncio.sleep(STREAM_UPDATE_INTERVAL)
    except WebSocketDisconnect:
        logger.info("[-] Visualizer websocket client disconnected")
    except Exception as exc:  # pragma: no cover - telemetry/logging focus
        logger.exception(f"[!!] Websocket streaming error: {exc}")
        await websocket.close(code=1011)
