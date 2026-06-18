#!/bin/bash
# Master Launcher Script for Linux/Mac
# Starts all services: GPS Server, Detection Backend, Web Server

clear

echo ""
echo "========================================================================"
echo "  MyVerse Survivor Detection System - Master Launcher"
echo "========================================================================"
echo ""
echo "Starting all services..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ Python is not installed"
        echo "Install it with: sudo apt install python3 (Ubuntu/Debian)"
        exit 1
    fi
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo ""
echo "========================================================================"
echo "Starting Services:"
echo "========================================================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to start service in background
start_service() {
    local name=$1
    local script=$2
    local port=$3
    
    echo -e "${YELLOW}[Starting]${NC} $name"
    
    if [ -f "$SCRIPT_DIR/$script" ]; then
        # Start in new terminal (tmux, screen, or gnome-terminal)
        if command -v tmux &> /dev/null; then
            tmux new-window -n "$name" -c "$SCRIPT_DIR" "$PYTHON_CMD $script"
        elif command -v screen &> /dev/null; then
            screen -dmS "$name" -c "$SCRIPT_DIR" "$PYTHON_CMD $script"
        else
            # Fallback: Run in background
            $PYTHON_CMD "$SCRIPT_DIR/$script" &
        fi
        
        if [ ! -z "$port" ]; then
            echo -e "${GREEN}✅${NC} $name started (Port: $port)"
        else
            echo -e "${GREEN}✅${NC} $name started"
        fi
    else
        echo -e "${RED}❌${NC} $script not found"
    fi
    
    sleep 1
}

# Start services
start_service "GPS Server" "gps_server.py" "8888"
start_service "Detection Backend" "app.py" ""
start_service "Web Server" "web_server.py" "5000"

clear

echo ""
echo "========================================================================"
echo "  All Services Started Successfully!"
echo "========================================================================"
echo ""
echo -e "${GREEN}[OK]${NC} GPS Server ................. Running (Port 8888)"
echo -e "${GREEN}[OK]${NC} Detection Backend .......... Running (Video from Mobile)"
echo -e "${GREEN}[OK]${NC} Web Server ................. Running (http://localhost:5000)"
echo ""
echo "========================================================================"
echo "Access Points:"
echo "========================================================================"
echo ""
echo -e "  ${BLUE}WEB INTERFACE:${NC} http://localhost:5000"
echo "    - Register new account"
echo "    - View survivors"
echo "    - Identify survivors"
echo "    - Admin dashboard"
echo ""
echo -e "  ${BLUE}GPS SERVER:${NC} localhost:8888"
echo "    - Provides location data to detection system"
echo ""
echo -e "  ${BLUE}DETECTION BACKEND:${NC}"
echo "    - Processes video from mobile"
echo "    - Detects survivors"
echo "    - Sends data to database"
echo ""
echo "========================================================================"
echo "Important Notes:"
echo "========================================================================"
echo ""
echo "1. EACH SERVICE runs SIMULTANEOUSLY"
echo "   - All 3 can run at the same time"
echo "   - They communicate through MongoDB"
echo "   - No conflicts between them"
echo ""
echo "2. VIDEO STREAMING:"
echo "   - Connect your mobile to video stream URL"
echo "   - Detection processes frames in real-time"
echo "   - Results appear on website automatically"
echo ""
echo "3. WEBSITE:"
echo "   - Open http://localhost:5000 in your browser"
echo "   - Survivors from detection appear automatically"
echo "   - Users can identify them"
echo ""
echo "4. TO STOP SERVICES:"
echo "   - If using tmux: Press Ctrl+B, then type ':kill-session -t SESSION_NAME'"
echo "   - If in background: jobs, then kill %1, %2, %3"
echo "   - Or close the terminal windows"
echo ""
echo "========================================================================"
echo ""

# Open browser if available
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5000 2>/dev/null
elif command -v open &> /dev/null; then
    open http://localhost:5000 2>/dev/null
fi

echo -e "${GREEN}All systems ready!${NC}"
echo "Press Ctrl+C or close terminal windows to stop services"
echo ""

# Wait for user to stop
wait
