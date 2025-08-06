#!/bin/bash
# Discogs Collection Lab Startup Script (PostgreSQL Version)

set -e

echo "🎵 Discogs Collection Lab (PostgreSQL Version)"
echo "=============================================="

# Check if Docker is available
if command -v docker-compose &> /dev/null; then
    echo "✅ Docker Compose found"
    
    # Start PostgreSQL with Docker
    echo "🐘 Starting PostgreSQL with Docker..."
    docker-compose up -d postgres
    
    # Wait for PostgreSQL to be ready
    echo "⏳ Waiting for PostgreSQL to be ready..."
    sleep 10
    
    # Check if PostgreSQL is responding
    if docker-compose exec postgres pg_isready -U discogs_user -d discogs_collection &> /dev/null; then
        echo "✅ PostgreSQL is ready!"
    else
        echo "❌ PostgreSQL is not responding. Check Docker logs:"
        docker-compose logs postgres
        exit 1
    fi
    
elif command -v psql &> /dev/null; then
    echo "✅ PostgreSQL CLI found - assuming local installation"
else
    echo "❌ Neither Docker nor PostgreSQL CLI found"
    echo "Please install PostgreSQL or Docker first"
    exit 1
fi

# Check Python and dependencies
echo ""
echo "🐍 Checking Python environment..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $python_version found"

# Check if virtual environment should be created
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "💡 Tip: Consider using a virtual environment:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo ""
fi

# Install requirements if needed
if ! python3 -c "import psycopg2" &> /dev/null; then
    echo "📦 Installing Python dependencies..."
    pip3 install -r requirements.txt
else
    echo "✅ Python dependencies already installed"
fi

# Test connection
echo ""
echo "🧪 Testing database connection..."
python3 test_connection.py

# Check for configuration
echo ""
echo "⚙️  Checking configuration..."

if [[ -f "discogs_config.json" ]]; then
    echo "✅ Configuration file found: discogs_config.json"
elif [[ -n "$DISCOGS_TOKEN" ]]; then
    echo "✅ Configuration via environment variables"
else
    echo "⚠️  No configuration found. Please:"
    echo "   1. Copy example_config.json to discogs_config.json"
    echo "   2. Add your Discogs API token"
    echo "   3. Update PostgreSQL credentials if needed"
    echo ""
    echo "Or set environment variables:"
    echo "   export DISCOGS_TOKEN='your_token_here'"
    echo "   export POSTGRES_USER='discogs_user'"
    echo "   export POSTGRES_PASSWORD='discogs_password'"
fi

echo ""
echo "🚀 Ready to start! Next steps:"
echo ""
echo "1. Configure your Discogs API token (see above)"
echo "2. Download your collection:"
echo "   python3 discogs_downloader.py --max-releases 10"
echo ""
echo "3. Launch the dashboard:"
echo "   streamlit run streamlit_app.py"
echo ""
echo "4. Access your collection at: http://localhost:8501"
echo ""

# Optional: Start pgAdmin
if command -v docker-compose &> /dev/null; then
    echo "💡 Optional: Start pgAdmin for database management:"
    echo "   docker-compose up -d pgadmin"
    echo "   Then visit: http://localhost:8080"
    echo "   Login: admin@discogs.local / admin123"
    echo ""
fi

echo "📊 Database tools:"
echo "   - View logs: docker-compose logs postgres"
echo "   - Connect to DB: docker-compose exec postgres psql -U discogs_user -d discogs_collection"
echo "   - Stop services: docker-compose down"
echo ""
echo "Happy collecting! 🎵"