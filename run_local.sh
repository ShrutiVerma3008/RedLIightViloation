# #!/bin/bash
# # ... (previous lines of run_local.sh remain the same for setup) ...
# set -e
# # --- Load Environment Variables ---
# if [ -f .env ]; then
#     export $(grep -v '^#' .env | xargs)
#     echo "Environment variables loaded from .env"
# fi
# # ... (Other setup logic) ...

# # --- Start Flask Development Server ---
# echo "Starting Flask Development Server on http://0.0.0.0:5000"
# # *** CRITICAL CHANGE HERE: Specify the factory function name 'create_app' ***
# export FLASK_APP="app:create_app"
# export FLASK_ENV=development
# flask run --host 0.0.0.0 --port 5000



#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

echo "Starting Red-Light Violation Detection System Setup and Run..."

# --- 1. Setup Virtual Environment and Dependencies ---

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    # Use 'python' for MINGW/Windows compatibility
    python -m venv venv
fi

echo "Activating virtual environment..."
# CRITICAL: Use 'Scripts' directory for Windows/MINGW activation
source venv/Scripts/activate

echo "Installing/updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# --- 2. Load Environment Variables and Set Python Path ---

if [ -f .env ]; then
    # Use xargs to correctly export all variables in the .env file
    export $(grep -v '^#' .env | xargs)
    echo "Environment variables loaded from .env"
else
    echo "WARNING: .env file not found. Using default environment or exported vars."
fi

# CRITICAL: Explicitly add the project root to PYTHONPATH for correct module imports (e.g., 'app' package)
export PYTHONPATH=$PYTHONPATH:$(pwd)
echo "PYTHONPATH set to include project root."

# --- 3. Database Initialization ---

echo "Initializing/Migrating PostgreSQL Database..."
# This script runs a helper to ensure all SQLAlchemy models are created/synced
# This must run successfully BEFORE the Flask app tries to connect
python -c "from app.models.db import init_db; init_db()"

# --- 4. Start Flask Development Server ---

echo "Starting Flask Development Server on http://0.0.0.0:5000"
# CRITICAL: Specify the factory function 'create_app'
export FLASK_APP="app:create_app"
export FLASK_ENV=development
# Use the specified host and port
flask run --host 0.0.0.0 --port 5000