# API Testing Guide

Quick reference for testing the YOLOv8 Detection API locally.

## Prerequisites

- Virtual environment activated: `.\venv\Scripts\activate.bat`
- Server running: `python -m uvicorn app.main:app --reload`
- Server accessible at: `http://localhost:8000`

## Method 1: Swagger UI (Easiest!)

1. Open browser: `http://localhost:8000/docs`
2. Click **Authorize** button (top right)
3. Generate test token:
   ```python
   # In Python interpreter:
   from app.auth import create_test_token
   token = create_test_token("test-user")
   print(token)
   ```
4. Copy the `eyJ...` part (everything after "Bearer ")
5. Paste in Authorize dialog and click "Authorize"
6. Click **POST /detect**
7. Click "Try it out"
8. Upload an image file
9. Optionally set `confidence_threshold` (default 0.25)
10. Click "Execute"
11. View response in "Response body"

## Method 2: curl (Command Line)

```bash
# Generate token (one-time)
for /f "tokens=*" %i in ('python -c "from app.auth import create_test_token; print(create_test_token(\"test-user\"))"') do set TOKEN=%i

# Test detection
curl -X POST http://localhost:8000/detect \
  -H "Authorization: %TOKEN%" \
  -F "file=@C:\path\to\test_image.jpg" \
  -F "confidence_threshold=0.25"
```

### Expected Response (200 OK)

```json
{
  "detections": [
    {
      "bbox": [100.5, 150.2, 300.8, 400.1],
      "class_id": 0,
      "class_name": "corrosion",
      "confidence": 0.92,
      "mask_rle": "eJwDAAAAAAE=",
      "area": 15000
    },
    {
      "bbox": [350.0, 200.0, 500.0, 350.0],
      "class_id": 1,
      "class_name": "dents",
      "confidence": 0.88,
      "mask_rle": "eJwDAAAAAAE=",
      "area": 12000
    }
  ],
  "image_width": 640,
  "image_height": 480,
  "image_path": "detection-images/test-user/2026-04-09/image.timestamp.jpg",
  "image_url": null,
  "processing_time_ms": 127.3,
  "detection_count": 2,
  "confidence_threshold": 0.25
}
```

## Method 3: Python Requests

```python
import requests
from app.auth import create_test_token

BASE_URL = "http://localhost:8000"
TOKEN = create_test_token("test-user")

# Prepare headers and data
headers = {
    "Authorization": TOKEN
}

# Test 1: Health check (no auth needed)
response = requests.get(f"{BASE_URL}/health")
print("Health:", response.json())

# Test 2: Detection with image
with open("test_image.jpg", "rb") as f:
    files = {"file": f}
    data = {"confidence_threshold": 0.25}
    response = requests.post(
        f"{BASE_URL}/detect",
        headers=headers,
        files=files,
        data=data
    )
    
print("Detection Response:")
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
```

## Method 4: Postman

1. Create new POST request
2. URL: `http://localhost:8000/detect`
3. **Headers tab:**
   - Add: `Authorization` = `Bearer <your-test-token>`
4. **Body tab:**
   - Select `form-data`
   - Key: `file` → Type: `File` → Select image
   - Key: `confidence_threshold` → Type: `text` → Value: `0.25`
5. Click **Send**

## Testing Different Scenarios

### Scenario 1: Valid Image with Detection

**File:** Any JPG/PNG of undercarriage area with damage  
**Expected:** 200 with detections array

```json
{
  "detections": [/* detected objects */],
  "detection_count": 1,
  ...
}
```

### Scenario 2: Valid Image with No Detections

**File:** Clean undercarriage image (no damage)  
**Expected:** 200 with empty detections

```json
{
  "detections": [],
  "detection_count": 0,
  ...
}
```

### Scenario 3: Missing Authorization

**Request:** POST /detect without header  
**Expected:** 401 Unauthorized

```json
{
  "detail": "Missing authorization header",
  "error_code": "HTTP_ERROR"
}
```

### Scenario 4: Invalid File Type

**File:** Text file or non-image  
**Expected:** 400 Bad Request

```json
{
  "detail": "File must be an image",
  "error_code": "HTTP_ERROR"
}
```

### Scenario 5: File Too Large (>10MB)

**File:** Large video or data file  
**Expected:** 413 Payload Too Large

```json
{
  "detail": "File size exceeds maximum of 10.0MB",
  "error_code": "HTTP_ERROR"
}
```

### Scenario 6: Invalid Confidence Threshold

**Request:** POST with `confidence_threshold=1.5` (outside 0-1 range)  
**Expected:** 422 Validation Error (from Pydantic)

```json
{
  "detail": [
    {
      "loc": ["body", "confidence_threshold"],
      "msg": "less than or equal to 1"
    }
  ]
}
```

## API Endpoint Reference

### POST /detect

Runs YOLOv8 inference on image.

**Request:**
- `file`: Image file (required)
- `confidence_threshold`: 0.0-1.0 (optional, default 0.25)
- `Authorization`: Bearer token (required)

**Response:** 200 OK
- Returns DetectionResponse with detections, image metadata, processing time

**Error Responses:**
- 400: Invalid file
- 401: Missing/invalid token
- 413: File too large
- 503: Model not loaded
- 500: Server error

### GET /health

Health check - no auth needed.

**Response:** 200 OK

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model_loaded": true,
  "supabase_connected": false
}
```

### GET /detections

User detection history (placeholder for Phase 2).

**Response:** 501 Not Implemented

### GET /docs

Interactive Swagger UI documentation.

### GET /redoc

ReDoc API documentation.

## Response Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Detection completed |
| 400 | Bad Request | Invalid file format |
| 401 | Unauthorized | Missing/invalid token |
| 413 | Payload Too Large | File >10MB |
| 422 | Validation Error | Invalid parameter |
| 500 | Server Error | Unexpected error |
| 503 | Service Unavailable | Model not loaded |

## Debugging Tips

### Check Server Logs

Watch terminal where uvicorn is running. You'll see:

```
INFO:app.inference:Loading YOLO model from models/yolov8m.torchscript (format: torchscript)
INFO:app.inference:Model loaded successfully
INFO:uvicorn.access:{"method": "POST", "status_code": 200, ...}
```

### Verify Model File Exists

```bash
# From backend directory
dir models\yolov8m.torchscript
# Or Python:
import os
print(os.path.exists("models/yolov8m.torchscript"))
```

### Check Environment Variables

```python
from app.config import MODEL_PATH, MODEL_FORMAT
print(f"Model: {MODEL_PATH} (format: {MODEL_FORMAT})")
```

### Test Token Generation

```python
from app.auth import create_test_token
token = create_test_token("my-user-id")
print(token)
# Output: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### Manual Model Loading Test

```python
from app.inference import YOLODetector
from app.config import MODEL_PATH, MODEL_FORMAT

try:
    detector = YOLODetector(MODEL_PATH, MODEL_FORMAT)
    print(f"Model loaded: {detector.is_loaded()}")
except Exception as e:
    print(f"Error: {e}")
```

## Performance Benchmarks

**On typical laptop (CPU):**

| Operation | Time |
|-----------|------|
| Image validation | 1-5ms |
| Image loading | 2-10ms |
| YOLO inference | 100-150ms |
| Mask encoding | 5-20ms |
| **Total** | **110-185ms** |

If you have CUDA GPU:
- Inference: 20-50ms
- Total: 30-80ms

## Common Issues & Fixes

### Issue: "Model not loaded" (503)

**Cause:** MODEL_PATH incorrect or file doesn't exist

**Fix:**
1. Verify file exists: `dir models\yolov8m.torchscript`
2. Check .env: `MODEL_PATH=models/yolov8m.torchscript`
3. Check format: `MODEL_FORMAT=torchscript`
4. Restart server

### Issue: "Connection refused"

**Cause:** Server not running

**Fix:**
```bash
cd backend
python -m uvicorn app.main:app --reload
# Should show: Uvicorn running on http://127.0.0.1:8000
```

### Issue: "Invalid token"

**Cause:** Token format wrong or expired

**Fix:** Re-generate:
```python
from app.auth import create_test_token
print(create_test_token("test-user"))
```

### Issue: Slow inference (>500ms)

**Cause:** Running on CPU (normal!)

**Solution:**
1. For GPU: Add `device="cuda"` in YOLO init (if CUDA installed)
2. Use smaller model: `yolov8s` instead of `yolov8m`
3. Accept normal speed for development

---

**Happy testing!** 🎯

For more info, see `backend/README.md`
