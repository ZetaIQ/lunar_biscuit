#!/bin/bash
# Start the main simulation server and dashboard

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Start main.py in the background
echo "[*] Starting Lunar Biscuit API server..."
python main.py &
MAIN_PID=$!

# Wait a moment for the server to start
sleep 2

# Start the Streamlit dashboard
echo "[*] Starting Streamlit dashboard..."
streamlit run dashboard.py 

# Clean up on exit
trap "kill $MAIN_PID 2>/dev/null || true" EXIT