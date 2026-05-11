import uvicorn
import os
import sys

# Ensure the root directory of the project is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if __name__ == "__main__":
    print("Launching Swayam-Admin Backend Engine on http://127.0.0.1:8000...")
    print("Static assets will be served on http://127.0.0.1:8000/assets/... ")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
