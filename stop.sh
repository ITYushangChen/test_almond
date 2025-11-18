#!/bin/bash

echo "🛑 Stopping Corporate Culture Monitor..."
echo ""

docker-compose down

echo ""
echo "✓ All services stopped"
echo ""
echo "To start again, run: ./start.sh"
echo "To remove all data, run: docker-compose down -v"

