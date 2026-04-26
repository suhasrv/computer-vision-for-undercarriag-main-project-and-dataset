# Undercarriage Damage Detection — Product Summary

Automates vehicle undercarriage inspections by detecting corrosion and dents from images. Designed to reduce manual inspection time, lower maintenance costs, and help fleets meet safety and compliance checks.

**Why this matters**
- Cuts manual inspection time and labor cost for fleet operators.
- Improves detection consistency and early identification of corrosion/dents.
- Helps satisfy safety audits and reduce unexpected maintenance downtime.

**Key results (run `scripts/compute_metrics.py` to reproduce)**
**Key results (run `scripts/compute_metrics.py` to reproduce)**
- mAP50-95 (instance segmentation, val): 0.244 (24.4%); mAP50: 0.505 (50.5%)
- Validation set size: 147 images (train: 1,421; test: 71)
- Latency (CPU, inference per image): ~436 ms/image (validation run). Run `scripts/compute_metrics.py --sample` to capture p50/p90/p95

For full technical details and deployment instructions see [backend/README.md](backend/README.md).

### Quick Start (developer)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # On Windows
# or
source venv/bin/activate      # On Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your Supabase credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key
MODEL_FORMAT=torchscript  # or pt, onnx
MODEL_PATH=models/yolov8m.torchscript
```

#### 3. Download/Export Model

The app expects the model in `models/` directory. You have two options:

**Option A: Use existing TorchScript model** (if already exported)
```bash
# Copy the existing model
cp ../runs/weights/best.torchscript models/yolov8m.torchscript
```

**Option B: Export from PyTorch**
```python
from ultralytics import YOLO

model = YOLO("../runs/weights/best.pt")
model.export(format="torchscript")  # Creates best.torchscript
mv best.torchscript models/yolov8m.torchscript
```

#### 4. Run API Locally

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

- **Swagger Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### API Endpoints

#### `POST /detect` - Run Inference

**Authentication:** Required (Bearer token)

**Request:**
```bash
curl -X POST http://localhost:8000/detect \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/image.jpg" \
  -F "confidence_threshold=0.25"
```

**Response:**
```json
{
  "detections": [
    {
      "bbox": [100.5, 150.2, 300.8, 400.1],
      "class_id": 0,
      "class_name": "corrosion",
      "confidence": 0.95,
      "mask_rle": "eJwDAAAAAAE=",
      "area": 15000
    }
  ],
  "image_width": 640,
  "image_height": 480,
  "image_path": "detection-images/user-uuid/2026-04-09/image.jpg",
  "image_url": "https://...",
  "processing_time_ms": 125.5,
  "detection_count": 1,
  "confidence_threshold": 0.25
}
```

#### `GET /health` - Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model_loaded": true,
  "supabase_connected": true
}
```

#### `GET /detections` - Detection History (Future)

Coming in Phase 2. Will retrieve past detections for authenticated user.

#### `GET /docs` - Interactive Documentation

Swagger UI for testing endpoints interactively.

### Testing

#### Run Tests

```bash
# Install pytest
pip install pytest

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_inference.py -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=app
```

#### Manual Testing with Test Token

The `auth.py` module provides `create_test_token()` for development:

```python
from app.auth import create_test_token

# Generate test token
token = create_test_token("test-user-uuid")
print(token)  # "Bearer eyJ..."
```

Use this token in requests:
```bash
curl -X POST http://localhost:8000/detect \
  -H "Authorization: Bearer eyJ..." \
  -F "file=@test.jpg"
```

### Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration & environment variables
│   ├── models.py            # Pydantic request/response schemas
│   ├── inference.py         # YOLODetector class
│   ├── supabase_client.py   # Supabase operations
│   ├── auth.py              # JWT token verification
│   └── utils.py             # Helper functions
├── models/                  # Store model files here
│   └── yolov8m.torchscript
├── tests/
│   ├── test_inference.py    # Inference unit tests
│   └── test_api.py          # API endpoint tests
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
├── .env                    # Your credentials (git-ignored)
├── .gitignore
├── Dockerfile              # Container build file
├── render.yaml             # Render.com deployment config
└── README.md               # This file
```

### Deployment

#### Docker

```bash
# Build image
docker build -t yolo-detection-api .

# Run container
docker run -p 8000:8000 \
  -e SUPABASE_URL="..." \
  -e SUPABASE_SERVICE_ROLE_KEY="..." \
  -e SUPABASE_ANON_KEY="..." \
  yolo-detection-api
```

#### Render.com

1. Push code to GitHub repository
2. Create new Web Service on Render.com
3. Connect GitHub repository
4. Set environment variables in Render dashboard:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_ANON_KEY`
   - `MODEL_FORMAT`
   - `MODEL_PATH`
5. Deploy

#### Railway.app

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and link project
railway login
railway link

# Deploy
railway up

# View logs
railway logs
```

### Model Formats

| Format | Pros | Cons | Speed |
|--------|------|------|-------|
| **PyTorch (.pt)** | Simple, flexible | Slower | Baseline |
| **TorchScript (.torchscript)** | Fast, no deps | Limited dynamic control | 1.2-1.5x faster |
| **ONNX (.onnx)** | Fastest, portable | Extra conversion | 1.5-2x faster |

**Recommendation for MVP:** TorchScript (best balance of speed and simplicity)

### Supabase Setup

#### 1. Create Detections Table

```sql
CREATE TABLE detections (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now(),
  image_path TEXT NOT NULL,
  image_url TEXT,
  image_width INTEGER,
  image_height INTEGER,
  detections JSONB,
  detection_count INTEGER,
  confidence_threshold FLOAT,
  processing_time_ms FLOAT,
  metadata JSONB,
  
  INDEX idx_user_created (user_id, created_at DESC)
);
```

#### 2. Create Storage Bucket

- Bucket name: `detection-images`
- Visibility: Public
- Path: `/user-id/yyyy-mm-dd/filename.jpg`

#### 3. Set Bucket Policies

```sql
-- Allow authenticated users to list their own files
CREATE POLICY "Users can list own detection images"
ON storage.objects FOR SELECT
USING (auth.uid()::text = (storage.foldername(name))[1]);

-- Allow authenticated users to upload their own files
CREATE POLICY "Users can upload own detection images"
ON storage.objects FOR INSERT
WITH CHECK (auth.uid()::text = (storage.foldername(name))[1]);
```

### Troubleshooting

#### Model Loading Error
```
RuntimeError: Failed to load YOLO model
```
- Check MODEL_PATH exists and is correct format
- Verify MODEL_FORMAT matches file type
- Try: `python -c "from ultralytics import YOLO; YOLO('models/yolov8m.torchscript')"`

#### Authentication Error
```
401 Unauthorized: Invalid token
```
- Ensure Authorization header is present
- Format: `Authorization: Bearer <token>`
- Check token is valid

#### Supabase Connection Error
```
Failed to initialize Supabase
```
- Verify SUPABASE_URL is set
- Check SUPABASE_SERVICE_ROLE_KEY is correct
- Try: `curl -H "Authorization: Bearer <key>" https://your-project.supabase.co/rest/v1/`

#### Out of Memory
- If model is too large, consider:
  - Using ONNX format (smaller)
  - Running on GPU (add `device="cuda"` to YOLO)
  - Using smaller model (`yolov8s` instead of `yolov8m`)

### Development Notes

- **Async Supabase:** The Supabase client is synchronous. Used `asyncio.to_thread()` wrapper in Pydantic models for non-blocking behavior if needed.
- **Mask Encoding:** Masks are stored as RLE (Run-Length Encoding) encoded base64 strings to minimize JSON payload
- **Logging:** Structured logging with request IDs for debugging
- **Error Handling:** Returns request_id in all error responses for support purposes

### Next Steps

**Phase 2:**
- GET /detections endpoint with pagination
- Batch processing endpoint
- WebSocket for real-time progress

**Phase 3:**
- User dashboard
- Analytics (class distribution, avg confidence)
- Detection filtering

### Support

For issues or questions:
1. Check `/docs` for endpoint documentation
2. Review logs with request_id
3. Test with `/health` endpoint
4. Verify environment variables in .env

### License

[Your License Here]
