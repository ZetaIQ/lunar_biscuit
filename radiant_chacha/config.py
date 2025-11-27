# ruff: noqa: F401

from logging import (
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    WARNING,
)

LOG_LEVEL = WARNING  # Set default log level to WARNING for less verbose output

# Logging destination: "file", "stdout", or "both"
LOG_DESTINATION = "file"  # Options: "file", "stdout", "both"
# Per-type connection thresholds (lower = more permissive)
BLOCK_CONNECTION_THRESHOLD = 0.4
POINT_CONNECTION_THRESHOLD = 0.8
SPHERE_CONNECTION_THRESHOLD = 0.2

# Per-type influence radii (geometric reach for proximity scoring in should_connect).
# Higher = nodes stay connected over greater distances.
# Ordering by node importance: Sphere (hub) > Block (regular) > Point (leaf)
SPHERE_INFLUENCE_RADIUS = 15.0  # Hub/anchor: largest reach
BLOCK_INFLUENCE_RADIUS = 8.0  # Regular nodes: medium reach
POINT_INFLUENCE_RADIUS = 3.0  # Leaf nodes: minimal reach

# Per-type stability windows (history samples to consider for stability calculation)
BLOCK_STABILITY_WINDOW = 10
POINT_STABILITY_WINDOW = 10
SPHERE_STABILITY_WINDOW = 10

# Per-type tick intervals (seconds between simulation steps for each node type)
# Allows granular testing and tuning per object type
BLOCK_TICK_INTERVAL = 10.0
POINT_TICK_INTERVAL = 2.0
SPHERE_TICK_INTERVAL = 30.0

# Web dashboard streaming interval (seconds between websocket pushes)
STREAM_UPDATE_INTERVAL = 0.25
