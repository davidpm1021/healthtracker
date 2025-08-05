#!/usr/bin/env python3
"""
Start the HealthTracker server with proper imports.
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Now we can import and run
import uvicorn

if __name__ == "__main__":
    print("Starting HealthTracker server...")
    print(f"Dashboard: http://localhost:8000/static/index.html")
    print(f"API docs: http://localhost:8000/docs")
    print(f"Database: {os.path.join(project_root, 'healthtracker.db')}")
    print("\nPress Ctrl+C to stop the server")
    
    uvicorn.run(
        "src.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=[project_root]
    )