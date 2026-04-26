"""
Launch script for running the FastAPI application locally.
"""
import sys
import os

# Change to backend directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)

print(f"Working directory: {os.getcwd()}")
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print()

# Run uvicorn directly
print("Starting FastAPI server...")
print("=" * 60)
print("API available at: http://127.0.0.1:8000")
print("API Docs at: http://127.0.0.1:8000/docs")
print("Press Ctrl+C to stop")
print("=" * 60)
print()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )
