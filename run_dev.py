#!/usr/bin/env python3
"""Development server runner for World Journey AI."""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from world_journey_ai import create_app
except ImportError as e:
    print(f"Error importing application: {e}")
    print("Make sure you've installed the requirements: pip install -r requirements.txt")
    sys.exit(1)


def main():
    """Run the development server."""
    # Load environment variables if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✓ Environment variables loaded from .env file")
    except ImportError:
        print("⚠ python-dotenv not installed, using system environment variables only")
    
    try:
        app = create_app()
        
        # Configuration
        port = int(os.getenv("PORT", 5000))
        debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
        host = os.getenv("FLASK_HOST", "127.0.0.1")
        
        print(f"🚀 Starting World Journey AI on http://{host}:{port}")
        print(f"📝 Debug mode: {debug}")
        print("🛑 Press Ctrl+C to stop the server")
        
        app.run(
            host=host,
            port=port,
            debug=debug
        )
        
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()