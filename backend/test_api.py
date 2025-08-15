#!/usr/bin/env python3
"""
Simple test to verify FastAPI app structure is correct
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.main import app
    print("✅ FastAPI app imported successfully!")
    print(f"   App title: {app.title}")
    print(f"   App version: {app.version}")
    
    # Check routes
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append(route.path)
    
    print(f"   Routes: {', '.join(routes)}")
    print("\n✅ Backend structure is valid!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Make sure to install dependencies: pip install fastapi")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)