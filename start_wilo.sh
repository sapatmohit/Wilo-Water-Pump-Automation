#!/bin/bash
echo "🧹 Cleaning up any old ghost processes..."
pkill -f "src/controller/pump_controller.py"
pkill -f "src/dashboard/server.py"
sleep 1

# Catch Ctrl+C and kill all background jobs automatically!
trap 'echo -e "\n🛑 Stopping all Wilo systems cleanly..."; kill $(jobs -p) 2>/dev/null; exit' SIGINT SIGTERM EXIT

echo "🚀 Starting Pump Controller..."
python3 src/controller/pump_controller.py &

echo "🚀 Starting Flask API on port 5050..."
python3 src/dashboard/server.py --port 5050 &
sleep 2

echo "🚀 Starting React Dashboard on port 8080 (http://0.0.0.0:8080)..."
cd dashboard
if [ -d "dist" ]; then
    echo "📦 Using built production dashboard (vite preview)..."
    npm run preview -- --host 0.0.0.0 --port 8080
else
    echo "⚡ Running development dashboard (vite dev)..."
    npm run dev -- --host 0.0.0.0 --port 8080
fi
