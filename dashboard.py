"""
Streamlit dashboard for real-time visualization.
Run with: streamlit run dashboard.py
"""

from radiant_chacha.core.factory import NeighborFactory
from radiant_chacha.visuals.dashboard import run_dashboard

if __name__ == "__main__":
    factory = NeighborFactory()
    run_dashboard(factory, refresh_interval=1)
