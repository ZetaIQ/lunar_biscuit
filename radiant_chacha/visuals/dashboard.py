"""
Real-time visualization dashboard using Streamlit and Plotly.
Displays node positions in 3D, connections, and live metrics.
"""

from typing import List

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from radiant_chacha.core.factory import NeighborFactory
from radiant_chacha.utils.log_handler import get_logger

logger = get_logger(__name__, source_file=__file__)


def run_dashboard(factory: NeighborFactory, refresh_interval: int = 1) -> None:
    """
    Run the Streamlit dashboard for real-time visualization.

    Parameters
    ----------
    factory : NeighborFactory
        The simulation's node factory.
    refresh_interval : int
        Refresh interval in seconds (Streamlit's auto-refresh).
    """
    st.set_page_config(
        page_title="Lunar Biscuit — Node Visualization",
        page_icon="🌙",
        layout="wide",
    )

    st.title("🌙 Lunar Biscuit: Node Visualization")
    st.write("Real-time 3D visualization of node positions, connections, and metrics.")

    # Sidebar controls
    with st.sidebar:
        st.header("Controls")
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        if auto_refresh:
            st.write(f"Refreshing every {refresh_interval}s")

    # Fetch current state
    nodes = factory.nodes
    if not nodes:
        st.warning("No nodes in simulation yet. Create some via the API!")
        return

    # Build 3D scatter plot
    fig = _build_3d_scatter(nodes)

    # Display plot
    st.plotly_chart(fig, use_container_width=True)

    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Nodes", len(nodes))
    with col2:
        total_edges = sum(len(n.neighbors) for n in nodes) // 2
        st.metric("Total Connections", total_edges)
    with col3:
        avg_gravity = np.mean([n.gravity for n in nodes])
        st.metric("Avg Gravity", f"{avg_gravity:.3f}")

    # Display node table
    st.subheader("Node Details")
    node_data = []
    for node in nodes:
        node_data.append(
            {
                "ID": node.id,
                "Type": node.type,
                "Address": node.addr[:16] + "...",
                "Neighbors": len(node.neighbors),
                "Gravity": f"{node.gravity:.3f}",
                "Pos X": f"{node.pos[0]:.2f}",
                "Pos Y": f"{node.pos[1]:.2f}",
                "Pos Z": f"{node.pos[2]:.2f}",
                "Anchor": "✓" if node.is_anchor else "✗",
            }
        )
    st.dataframe(node_data, use_container_width=True)

    # Auto-refresh logic
    if auto_refresh:
        import time

        time.sleep(refresh_interval)
        st.rerun()


def _build_3d_scatter(nodes: List) -> go.Figure:
    """
    Build a 3D scatter plot of node positions with connection lines.

    Parameters
    ----------
    nodes : List
        List of NeighborBase nodes.

    Returns
    -------
    plotly.graph_objects.Figure
        3D scatter plot with connections.
    """
    # Extract node positions, types, and IDs
    positions = np.array([node.pos for node in nodes])
    types = np.array([node.type for node in nodes])
    ids = np.array([node.id for node in nodes])
    colors_map = {"Block": "blue", "Point": "green", "Sphere": "red"}

    fig = go.Figure()

    # Add connection lines (edges)
    for node in nodes:
        for neighbor in node.neighbors:
            x = [node.pos[0], neighbor.pos[0]]
            y = [node.pos[1], neighbor.pos[1]]
            z = [node.pos[2], neighbor.pos[2]]
            fig.add_trace(
                go.Scatter3d(
                    x=x,
                    y=y,
                    z=z,
                    mode="lines",
                    line=dict(color="rgba(125, 125, 125, 0.5)", width=1),
                    hoverinfo="none",
                    showlegend=False,
                )
            )

    # Add nodes as scatter points
    for node_type in set(types):
        mask = types == node_type
        fig.add_trace(
            go.Scatter3d(
                x=positions[mask, 0],
                y=positions[mask, 1],
                z=positions[mask, 2],
                mode="markers",
                marker=dict(
                    size=8,
                    color=colors_map.get(node_type, "gray"),
                    opacity=0.8,
                    line=dict(width=0),
                ),
                text=[f"ID: {ids[i]}" for i in range(len(ids)) if mask[i]],
                hoverinfo="text",
                name=node_type,
            )
        )

    # Update layout
    fig.update_layout(
        title="3D Node Positions",
        scene=dict(
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z",
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.3),
            ),
        ),
        hovermode="closest",
        height=700,
    )

    return fig
