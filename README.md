# Lunar Biscuit (Prototype)

Lunar Biscuit is an experimental simulation that treats spatially distributed Python objects as if they were a self-organizing "3D blockchain." The heart of the project is the Python engine inside `main.py`, the neighbor factory implementation in `radiant_chacha/core/factory.py`, and a suite of behaviors that move, negotiate, and log each node. Parameters still require manual tuning—especially connection thresholds, influence radii, and tick cadence—so expect to iterate when exploring behaviors.

A modern WebGL visualizer (served from `radiant_chacha/api/json_rpc.py` and implemented in `radiant_chacha/visualization/static/visualizer.html`) provides a convenient way to inspect nodes, but the simulation does not depend on it.

---

## Status

- **Prototype**: the physics, heuristics, and factory abstractions are evolving rapidly.
- **Parameter-sensitive**: useful outcomes often require tweaking constants in `radiant_chacha/config.py` or overriding values per-node.
- **Single-factory**: today’s build assumes one active `NeighborFactory`; support for multiple factories is part of the roadmap.

---

## Features

### Core Simulation (Python-first)
- **NeighborFactory**: `radiant_chacha/core/factory.py` mints Blocks, Points, and Spheres with unique IDs, addresses, and initial state.
- **Self-ticking nodes**: Each node derives from `radiant_chacha/core/neighbor_base.py` and runs the shared tick routine in `radiant_chacha/methods/tick.py`, which handles gravity, discovery, and history.
- **Physics + heuristics**: Gravity comes from `radiant_chacha/methods/physics.py`; neighbor negotiation lives in `radiant_chacha/methods/discovery.py` and `radiant_chacha/methods/similarity.py`.

### API Layer
- **FastAPI service**: `radiant_chacha/api/json_rpc.py` exposes REST endpoints to create nodes, query state, stream history, and publish WebSocket snapshots.
- **Configurable payloads**: Node creation accepts different data formats (JSON, ndarray, bytes) and allows overriding thresholds, influence radii, velocity vectors, etc.

### Visualizer (Optional Add-on)
- **WebGL dashboard**: `radiant_chacha/visualization/static/visualizer.html` + `/ws/nodes` show live positions, connectors, and metadata without forcing camera resets.
- **Control surface**: The overlay supports node creation, connector tuning, history browsing, and snapshot tables. It is meant as a companion tool, not a core requirement.

---

## Installation

### Python environment
1. **Install dependencies**
	 - Using [uv](https://github.com/astral-sh/uv) (reads `pyproject.toml`):
		 ```sh
		 uv pip install .
		 ```
	 - Using pip with the pinned requirements file:
		 ```sh
		 pip install -r requirements.txt
		 ```

2. **Configure parameters**
	- Edit `radiant_chacha/config.py` to adjust:
	  - Connection thresholds (`BLOCK_CONNECTION_THRESHOLD`, etc.)
	  - Influence radii
	  - Stability windows
	  - Tick intervals
	  - WebSocket streaming cadence (`STREAM_UPDATE_INTERVAL`)
	- These defaults are intentionally conservative; expect to fine-tune for each experiment.

### Front-end assets (optional)
If you plan to rebuild the visualizer bundle:

```sh
npm install
npm run build:visualizer
```

This emits `visualizer.js` into `radiant_chacha/visualization/static/dist/`.

---

## Usage

1. **Start the simulation service**
	If you are using a virtual environment, activate it first:
	```sh
	source .venv/bin/activate  # adjust path/name as needed
	```
	Then run the service:
	```sh
	python main.py
	```
    - If running the main python function and visualizer is desired:
    ```sh
    ./run
    ```

2. **Interact with the API**
	- OpenAPI docs: `http://localhost:8401/docs`
	- Create nodes:
	  ```sh
	  curl -X POST http://localhost:8401/nodes \
		 -H "Content-Type: application/json" \
		 -d '{"node_type": "Block", "data": {"payload": 42}}'
	  ```
	- Inspect state:
	  ```sh
	  curl http://localhost:8401/simulation/status
	  ```

3. **Open the visualizer (optional)**
	- Visit `http://localhost:8401/visualizer`
	- The page connects to `ws://localhost:8401/ws/nodes` and streams updates at the interval defined in config.
	- Use the control panel to create nodes, pause rendering, adjust connectors, and review history per node.

---

## Tuning & Experimentation

- **Per-type overrides**: When creating a node via API, you can supply `connection_threshold`, `influence_radius`, `tick_interval`, `velocity`, and more to override the defaults injected in each interface (`block.py`, `point.py`, `sphere.py`).
- **History inspection**: Each node keeps snapshots in memory. Fetch `/nodes/{id}/history` to review stabilized positions, neighbor sets, and payload summaries.
- **Logging**: Configure handlers and verbosity in `radiant_chacha/utils/log_handler.py`. Logs are written to `logs/app/` and `logs/tests/` with timestamped filenames.

---

## Roadmap

1. **Multi-factory ecosystems**  
	- Ability to run multiple `NeighborFactory` instances concurrently, potentially with cross-factory negotiation or federation rules.

2. **Parameter orchestration**  
	- Dynamic profiles that adjust thresholds, radii, and tick spans at runtime.
	- Configurable heuristics per node type or per cluster.

3. **Batch data ingestion**  
	- Script-driven import format to define nodes, payload types, and parameter overrides in bulk (e.g., YAML/JSON job files).
	- Useful for replaying recorded datasets or staging complex topologies.

4. **Enhanced analytics**  
	- Persisted history streams, replay tools, and richer telemetry (gravity distributions, similarity heatmaps, etc.).

5. **Visualizer improvements**  
	- Secondary views (e.g., timeline charts, force diagrams) while keeping Three.js as the primary scene graph.

---

## Contributing

Because this is an active prototype, expect large API changes. If you want to experiment:

- Fork and adjust `radiant_chacha/core/factory.py` or the method modules to explore new behaviors.
- Keep the config-driven ethos; wiring new constants through `radiant_chacha/config.py` makes the tuning story easier.
- When editing the visualizer, run `npm run dev:visualizer` to load the Vite dev server (see `package.json`).

---

## License

GPLv3 — see [LICENSE](LICENSE).