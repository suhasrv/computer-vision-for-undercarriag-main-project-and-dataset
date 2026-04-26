"""
Configuration module for environment variables and application settings.
"""
# CRITICAL: Patch torch.load BEFORE any other imports to handle PyTorch 2.6+ weights_only restrictions
import torch

_original_torch_load = torch.load

def _patched_torch_load(f, *args, **kwargs):
    """Attempt to load with weights_only=False if strict loading fails."""
    if 'weights_only' not in kwargs:
        try:
            return _original_torch_load(f, *args, weights_only=True, **kwargs)
        except (RuntimeError, Exception) as e:
            if "was not an allowed global" in str(e) or "Weights only load failed" in str(e):
                return _original_torch_load(f, *args, weights_only=False, **kwargs)
            raise
    return _original_torch_load(f, *args, **kwargs)

torch.load = _patched_torch_load

# NOW safe to import other modules
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# Database table and storage bucket names
DETECTIONS_TABLE = os.getenv("DETECTIONS_TABLE", "inspections")
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "detection-images")



# Model Configuration
MODEL_PATH = os.getenv("MODEL_PATH", "models/yolov8m.torchscript")
MODEL_FORMAT = os.getenv("MODEL_FORMAT", "torchscript")  # pt, torchscript, onnx

# API Configuration
API_TITLE = os.getenv("API_TITLE", "YOLOv8 Undercarriage Detection API")
API_VERSION = os.getenv("API_VERSION", "1.0.0")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# File Upload Configuration
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10485760))  # 10MB
ALLOWED_IMAGE_FORMATS = os.getenv("ALLOWED_IMAGE_FORMATS", "jpg,jpeg,png,webp").split(",")

# Model Classes (from data.yaml)
MODEL_CLASSES = {
    0: "corrosion",
    1: "dents"
}
CLASS_NAMES_REVERSE = {v: k for k, v in MODEL_CLASSES.items()}

# CORS Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")



# Jobs table for batch processing
JOBS_TABLE = "jobs"

# Rate limiting (per-user key) - default 10 images per minute
RATE_LIMIT = os.getenv("RATE_LIMIT", "10/minute")

# Metrics
PROMETHEUS_METRICS_ENABLED = os.getenv("PROMETHEUS_METRICS_ENABLED", "True").lower() == "true"

# Validation Settings
CONFIDENCE_THRESHOLD_DEFAULT = 0.25
CONFIDENCE_THRESHOLD_MIN = 0.0
CONFIDENCE_THRESHOLD_MAX = 1.0
