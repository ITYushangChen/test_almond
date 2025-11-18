#!/bin/bash

echo "🏢 Corporate Culture Monitor - Starting Application..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker Desktop first."
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Check if .env file exists
if [ ! -f "backend/.env" ]; then
    echo "❌ Error: backend/.env file not found!"
    echo ""
    echo "Please create backend/.env file with your Supabase credentials:"
    echo "  1. Copy the example file: cp backend/.env.example backend/.env"
    echo "  2. Edit backend/.env and add your Supabase connection string"
    echo "  3. See SUPABASE_SETUP.md for detailed instructions"
    echo ""
    exit 1
fi

echo "✓ Environment file found"
echo ""

# Check if ports are available
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  Warning: Port $1 is already in use"
        echo "   Please stop the service using this port or change the port in docker-compose.yml"
        return 1
    fi
    return 0
}

echo "Checking port availability..."
PORTS_OK=true
check_port 3000 || PORTS_OK=false
check_port 5000 || PORTS_OK=false

if [ "$PORTS_OK" = false ]; then
    echo ""
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "🚀 Starting Docker containers..."
echo "   This may take a few minutes on first run..."
echo ""

docker-compose up --build -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
if docker ps | grep -q corporate_culture_frontend; then
    echo "✓ Frontend is running"
else
    echo "❌ Frontend failed to start"
fi

if docker ps | grep -q corporate_culture_backend; then
    echo "✓ Backend is running"
else
    echo "❌ Backend failed to start"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Application is ready!"
echo ""
echo "📱 Frontend:  http://localhost:3000"
echo "🔌 Backend:   http://localhost:5000"
echo "🗄️  Database:  Supabase (cloud-hosted)"
echo ""
echo "👤 First time? Create an account at http://localhost:3000"
echo ""
echo "📋 Useful commands:"
echo "   - View logs:  docker-compose logs -f"
echo "   - Stop app:   docker-compose down"
echo "   - Restart:    docker-compose restart"
echo ""
echo "📚 Documentation:"
echo "   - README.md - Full documentation"
echo "   - SETUP_GUIDE.md - Detailed setup instructions"
echo "   - ARCHITECTURE.md - System architecture"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

