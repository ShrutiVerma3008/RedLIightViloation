#!/bin/bash
# ... (previous lines of run_local.sh remain the same for setup) ...

# --- Load Environment Variables ---
# ... (Other setup logic) ...

# --- Start Flask Development Server ---
echo "Starting Flask Development Server on http://0.0.0.0:5000"
# *** CRITICAL CHANGE HERE: Specify the factory function name 'create_app' ***
export FLASK_APP="app:create_app"
export FLASK_ENV=development
flask run --host 0.0.0.0 --port 5000