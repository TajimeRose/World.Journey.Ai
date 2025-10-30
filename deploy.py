#!/usr/bin/env python3
"""Production deployment script for World Journey AI."""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description=""):
    """Run a system command and handle errors."""
    print(f"📋 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return None

def check_requirements():
    """Check if all requirements are met."""
    print("🔍 Checking deployment requirements...")
    
    # Check if .env file exists
    if not Path(".env").exists():
        print("⚠ Warning: .env file not found. Copy .env.example to .env and configure it.")
        return False
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("❌ Python 3.8+ is required")
        return False
    
    print("✓ All requirements met")
    return True

def install_dependencies():
    """Install Python dependencies."""
    return run_command("pip install -r requirements.txt", "Installing dependencies")

def run_tests():
    """Run application tests if available."""
    if Path("tests").exists():
        return run_command("python -m pytest tests/", "Running tests")
    else:
        print("ℹ No tests directory found, skipping tests")
        return True

def start_production_server():
    """Start the production server using Gunicorn."""
    print("🚀 Starting production server...")
    
    # Install gunicorn if not present
    run_command("pip install gunicorn", "Installing Gunicorn")
    
    # Start server
    port = os.getenv("PORT", "8000")
    workers = os.getenv("WORKERS", "4")
    
    command = f"gunicorn --bind 0.0.0.0:{port} --workers {workers} --timeout 120 app:app"
    print(f"🌐 Server will be available at: http://localhost:{port}")
    print("🛑 Press Ctrl+C to stop the server")
    
    os.system(command)

def main():
    """Main deployment function."""
    print("🌍 World Journey AI - Production Deployment")
    print("=" * 50)
    
    if not check_requirements():
        sys.exit(1)
    
    if install_dependencies() is None:
        sys.exit(1)
    
    if run_tests() is None:
        print("⚠ Tests failed, but continuing with deployment...")
    
    start_production_server()

if __name__ == "__main__":
    main()