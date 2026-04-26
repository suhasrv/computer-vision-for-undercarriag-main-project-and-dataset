"""
FastAPI application for YOLOv8 Undercarriage Damage Detection.
Main entry point for the API.
"""
import logging
import os
from contextlib import asynccontextmanager
import uuid
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, BackgroundTasks, Request
from fastapi.routing import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.config import (
    API_TITLE,
    API_VERSION,
    CORS_ORIGINS,
    MODEL_PATH,
    MODEL_FORMAT,
    CONFIDENCE_THRESHOLD_DEFAULT,
    CONFIDENCE_THRESHOLD_MIN,
    CONFIDENCE_THRESHOLD_MAX
    ,RATE_LIMIT, PROMETHEUS_METRICS_ENABLED
)
from app.inference import YOLODetector, DummyDetector

# Supabase helpers (storage, auth, db)
from app.supabase_client import (
    init_supabase,
    is_supabase_available,
    verify_token_get_user,
    upload_image_to_storage,
    save_detection_to_database,
    create_job,
    update_job,
    get_job,
)

from app.auth import get_current_user
from app.models import (
    DetectionResponse,
    Detection,
    HealthResponse,
    ErrorResponse,
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    JobCreateResponse,
    JobStatusResponse
)
from app.utils import validate_image_file, load_image_as_rgb
# Optional integrations: Prometheus metrics and slowapi (rate limiting)
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
except Exception:
    # Fallback no-op metrics
    class _NoOpMetric:
        def inc(self, *a, **k):
            return None
        def observe(self, *a, **k):
            return None
        def time(self):
            class DummyCtx:
                def __enter__(self):
                    return None
                def __exit__(self, exc_type, exc, tb):
                    return False
            return DummyCtx()

    def generate_latest():
        return b""

    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    Counter = lambda *a, **k: _NoOpMetric()
    Histogram = lambda *a, **k: _NoOpMetric()

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
except Exception:
    # Dummy limiter when slowapi not installed
    def get_remote_address(request):
        return "anon"

    class RateLimitExceeded(Exception):
        pass

    class SlowAPIMiddleware:
        def __init__(self, app):
            self.app = app
        async def __call__(self, scope, receive, send):
            return await self.app(scope, receive, send)

    class Limiter:
        def __init__(self, key_func=None):
            pass
        def limit(self, *a, **k):
            def _decorator(f):
                return f
            return _decorator

from fastapi.responses import PlainTextResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global detector instance
detector: YOLODetector = None

# API version prefix
API_PREFIX = "/v1"

# Prometheus metrics
IMAGES_PROCESSED = Counter("images_processed_total", "Total images processed")
TOTAL_DETECTIONS = Counter("detections_total", "Total detections made")
INFERENCE_LATENCY = Histogram("inference_latency_seconds", "Model inference latency in seconds")
CONFIDENCE_SUM = Counter("detection_confidence_sum", "Sum of detection confidences")

# Rate limiter (per-user or IP). Key by Bearer token when present, otherwise by IP.
def _user_or_ip_key(request: Request):
    auth = request.headers.get("Authorization")
    if auth:
        parts = auth.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    return get_remote_address(request)

limiter = Limiter(key_func=_user_or_ip_key)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup/shutdown events.
    """
    # Startup
    logger.info("Starting YOLOv8 Detection API...")
    global detector
    
    try:
        # If DEV_MODE enabled, use DummyDetector for fast local testing
        if os.getenv("DEV_MODE", "False").lower() in ("1", "true", "yes"):
            detector = DummyDetector()
            logger.info("✓ DEV_MODE: using DummyDetector")
        else:
            detector = YOLODetector(MODEL_PATH, MODEL_FORMAT)
            logger.info("✓ YOLO model loaded successfully")
    except Exception as e:
        logger.error(f"✗ Failed to load YOLO model: {e}")
        detector = None
    # Initialize Supabase client (if credentials present)
    try:
        init_supabase()
        logger.info("✓ Supabase client initialized")
    except Exception as e:
        logger.warning(f"✗ Supabase initialization warning: {e}")
    logger.info("API startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API...")
    logger.info("API shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description="YOLOv8 instance segmentation API for detecting undercarriage damage (corrosion, dents)",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limit middleware
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


# Rate limit exceeded handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return PlainTextResponse("Rate limit exceeded", status_code=429)


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get(API_PREFIX + "/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring API status.
    
    Returns:
        - status: API health status
        - model_loaded: Whether inference model is ready
        - supabase_connected: Whether Supabase is connected
    """
    return HealthResponse(
        status="healthy",
        version=API_VERSION,
        model_loaded=detector is not None and detector.is_loaded(),
        supabase_connected=is_supabase_available()
    )


# ============================================================================
# Detection Endpoint
# ============================================================================

@limiter.limit(RATE_LIMIT)
@app.post(
    API_PREFIX + "/detect",
    response_model=DetectionResponse,
    tags=["Detection"],
    summary="Run object detection on image",
    responses={
        200: {"description": "Detections successful"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        413: {"model": ErrorResponse, "description": "File too large"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
        500: {"model": ErrorResponse, "description": "Server error"}
    }
)
async def detect(
    request: Request,
    file: UploadFile = File(
        ...,
        description="Image file to process (JPEG, PNG, WebP)"
    ),
    confidence_threshold: float = Form(
        CONFIDENCE_THRESHOLD_DEFAULT,
        ge=CONFIDENCE_THRESHOLD_MIN,
        le=CONFIDENCE_THRESHOLD_MAX,
        description="Confidence threshold (0.0-1.0)"
    ),
    user_id: str = Depends(get_current_user)
):
    """
    Run YOLOv8 instance segmentation on uploaded image.
    
    **Requires Authentication:** Include `Authorization: Bearer <token>` header
    
    Args:
        - file: Image file (multipart/form-data)
        - confidence_threshold: Confidence threshold for detections (default: 0.25)
        - user_id: Extracted from JWT token
    
    Returns:
        - detections: List of detected objects with bounding boxes and segmentation masks
        - image_metadata: Image dimensions, storage path, processing time
    
    Raises:
        - 400: Invalid file or image format
        - 401: Missing or invalid authorization token
        - 413: File exceeds size limit (10MB)
        - 503: Model not loaded
        - 500: Inference or database error
    """
    request_id = str(uuid.uuid4())[:8]
    
    try:
        # ====== Step 1: Validate file ======
        logger.info(f"[{request_id}] Validating file: {file.filename}")
        
        # Read file content for validation
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file type and size
        is_valid, error_msg = validate_image_file(file.content_type, file_size)
        if not is_valid:
            logger.warning(f"[{request_id}] File validation failed: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=error_msg,
                headers={"X-Request-ID": request_id}
            )
        
        # ====== Step 2: Load image ======
        logger.info(f"[{request_id}] Loading image")
        image, error_msg = load_image_as_rgb(file_content)
        if image is None:
            logger.warning(f"[{request_id}] Image loading failed: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=error_msg,
                headers={"X-Request-ID": request_id}
            )
        
        image_width = image.width
        image_height = image.height
        logger.info(f"[{request_id}] Image loaded: {image_width}x{image_height}")

        # Ensure model is loaded before running inference
        if detector is None or not detector.is_loaded():
            logger.error(f"[{request_id}] Model not loaded")
            raise HTTPException(
                status_code=503,
                detail="Detection model not available",
                headers={"X-Request-ID": request_id}
            )

        # ====== Step 3: Run inference ======
        logger.info(f"[{request_id}] Running inference with threshold={confidence_threshold}")
        detections, processing_time_ms = detector.predict(
            image=image,
            conf_threshold=confidence_threshold
        )
        logger.info(
            f"[{request_id}] Inference complete: {len(detections)} detections "
            f"in {processing_time_ms:.1f}ms"
        )
        # Update Prometheus metrics
        IMAGES_PROCESSED.inc()
        TOTAL_DETECTIONS.inc(len(detections))
        CONFIDENCE_SUM.inc(sum([d.get("confidence", 0.0) for d in detections]))
        
        # ====== Step 4: Upload image to storage (best-case optimization)
        # Only upload if there are detections to save. Skipping upload when
        # detections list is empty reduces IO and improves best-case latency.
        image_path = None
        image_url = None

        if len(detections) > 0:
            try:
                logger.info(f"[{request_id}] Uploading image to storage")
                image_path, image_url = await upload_image_to_storage(
                    user_id=user_id,
                    file_content=file_content,
                    original_filename=file.filename,
                    content_type=file.content_type
                )
                if image_path:
                    logger.info(f"[{request_id}] Image uploaded: {image_path}")
            except Exception as e:
                logger.error(f"[{request_id}] Storage upload failed: {e}")
                # Continue even if storage fails - return detections anyway
        
        # ====== Step 5: Save detections to database ======
        detection_id = None
        try:
            if image_path and image_url:  # Only save if image was stored
                logger.info(f"[{request_id}] Saving detections to database")
                detection_id = await save_detection_to_database(
                    user_id=user_id,
                    image_path=image_path,
                    image_url=image_url,
                    detections=detections,
                    image_size=(image_width, image_height),
                    confidence_threshold=confidence_threshold,
                    processing_time_ms=processing_time_ms
                )
                if detection_id:
                    logger.info(f"[{request_id}] Detection saved: {detection_id}")
        except Exception as e:
            logger.error(f"[{request_id}] Database save failed: {e}")
            # Continue even if database save fails
        
        # ====== Step 6: Build response ======
        detection_objects = [Detection(**d) for d in detections]
        
        response = DetectionResponse(
            detections=detection_objects,
            image_width=image_width,
            image_height=image_height,
            image_path=image_path,
            image_url=image_url,
            processing_time_ms=processing_time_ms,
            detection_count=len(detections),
            confidence_threshold=confidence_threshold
        )
        # Attach DB record ID if available
        if detection_id:
            response.inspection_id = detection_id
        
        logger.info(f"[{request_id}] Request completed successfully")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
            headers={"X-Request-ID": request_id}
        )


# ---------------------------------------------------------------------------
# Convenience test route for local development: run detection on a bundled
# test image without requiring multipart upload. This is useful when the
# frontend/proxy setup or terminal POSTs are inconvenient during debugging.
# ---------------------------------------------------------------------------
@app.get(API_PREFIX + "/test-detect", tags=["Detection"], summary="Run detection on bundled test image (DEV)")
async def test_detect():
    """Load a sample image from the repository and run the detector (DEV only)."""
    if detector is None or not detector.is_loaded():
        raise HTTPException(status_code=503, detail="Detection model not available")

    try:
        import pathlib
        sample = pathlib.Path(__file__).resolve().parents[1] / 'test' / 'images' / '2-60-_jpg.rf.70d6f7aedc5629bdcdec1097212540c3.jpg'
        if not sample.exists():
            raise HTTPException(status_code=404, detail="Sample image not found")

        with open(sample, 'rb') as f:
            content = f.read()

        image, err = load_image_as_rgb(content)
        if image is None:
            raise HTTPException(status_code=400, detail=f"Failed to load sample image: {err}")

        detections, processing_time_ms = detector.predict(image=image, conf_threshold=0.25)

        detection_objects = [Detection(**d) for d in detections]
        response = DetectionResponse(
            detections=detection_objects,
            image_width=image.width,
            image_height=image.height,
            image_path=None,
            image_url=None,
            processing_time_ms=processing_time_ms,
            detection_count=len(detections),
            confidence_threshold=0.25
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test detect failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# NOTE: Authentication endpoints (register/login) have been removed
# to allow direct public access to the API. Authentication helpers
# remain in the codebase for optional future re-enabling.


# ============================================================================
# Batch processing endpoints
# ============================================================================


async def _process_batch_job_async(job_id: str, user_id: str, images_payload: list, confidence_threshold: float = CONFIDENCE_THRESHOLD_DEFAULT):
    """Async worker to process batch images and update job status/result."""
    results = []
    try:
        await update_job(job_id, status="processing")

        for item in images_payload:
            # item is dict with 'filename', 'content_bytes', 'content_type'
            filename = item.get("filename")
            content = item.get("content")
            content_type = item.get("content_type", "image/jpeg")

            image, err = load_image_as_rgb(content)
            if image is None:
                results.append({"filename": filename, "error": err})
                continue

            # Run inference
            with INFERENCE_LATENCY.time():
                detections, processing_time_ms = detector.predict(image=image, conf_threshold=confidence_threshold)

            IMAGES_PROCESSED.inc()
            TOTAL_DETECTIONS.inc(len(detections))
            CONFIDENCE_SUM.inc(sum([d.get("confidence", 0.0) for d in detections]))

            # Upload and save (best-case optimization)
            # Only upload/save when there are detections to persist; skipping
            # storage reduces IO for the best-case where no objects are found.
            storage_path, public_url = None, None
            db_id = None
            if len(detections) > 0:
                storage_path, public_url = await upload_image_to_storage(user_id=user_id, file_content=content, original_filename=filename, content_type=content_type)
                if storage_path and public_url:
                    db_id = await save_detection_to_database(user_id=user_id, image_path=storage_path, image_url=public_url, detections=detections, image_size=(image.width, image.height), confidence_threshold=confidence_threshold, processing_time_ms=processing_time_ms)

            results.append({
                "filename": filename,
                "image_url": public_url,
                "db_id": db_id,
                "detection_count": len(detections)
            })

        await update_job(job_id, status="completed", result={"items": results})
    except Exception as e:
        logger.error(f"Batch job {job_id} failed: {e}")
        await update_job(job_id, status="failed", result={"error": str(e)})


@app.post(API_PREFIX + "/detect-batch", tags=["Detection"], summary="Batch detection (async)")
async def detect_batch(request: Request, background_tasks: BackgroundTasks, files: list[UploadFile] = File(None), confidence_threshold: float = Form(CONFIDENCE_THRESHOLD_DEFAULT), user_id: str = Depends(get_current_user)):
    """Accept multiple images (multipart or JSON base64) and process asynchronously."""
    request_id = str(uuid.uuid4())[:8]

    # Build payload
    images_payload = []

    # If multipart files provided
    if files:
        for f in files:
            content = await f.read()
            images_payload.append({"filename": f.filename or "image.jpg", "content": content, "content_type": f.content_type})

    else:
        # Try parse JSON body with base64 list
        try:
            body = await request.json()
            b64_list = body.get("images") or []
            import base64
            for idx, b64 in enumerate(b64_list):
                content = base64.b64decode(b64)
                images_payload.append({"filename": f"image_{idx}.jpg", "content": content, "content_type": "image/jpeg"})
        except Exception:
            raise HTTPException(status_code=400, detail="No files or images provided")

    # Create job
    job_id = str(uuid.uuid4())
    await create_job(job_id, user_id, status="pending", meta={"count": len(images_payload)})

    # Schedule background processing
    background_tasks.add_task(_process_batch_job_async, job_id, user_id, images_payload, confidence_threshold)

    return JobCreateResponse(job_id=job_id, status="pending")


@app.get(API_PREFIX + "/job/{job_id}", tags=["Jobs"], summary="Get job status")
async def get_job_status(job_id: str, user_id: str = Depends(get_current_user)):
    """Poll a previously submitted batch job for status and results."""
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": job}


@app.get(API_PREFIX + "/metrics", tags=["Metrics"])
async def metrics():
    """Prometheus-style metrics endpoint."""
    if not PROMETHEUS_METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    data = generate_latest()
    return PlainTextResponse(data.decode("utf-8"), media_type=CONTENT_TYPE_LATEST)


# ============================================================================
# For future enhancement: Detection History Endpoint
# ============================================================================

@app.get(
    API_PREFIX + "/detections",
    tags=["History"],
    summary="Get user's detection history (future enhancement)"
)
async def get_detection_history(
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user)
):
    """
    Retrieve user's past detection records (pagination supported).
    
    **This endpoint is reserved for Phase 2 implementation.**
    
    Args:
        - limit: Number of records to return (max 100)
        - offset: Number of records to skip
        - user_id: Extracted from JWT token
    
    Returns:
        - List of past detection records with results
    """
    return {
        "message": "This endpoint will be implemented in Phase 2",
        "status": "not-yet-implemented"
    }


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get(API_PREFIX + "/", tags=["Info"])
async def root():
    """API information and available endpoints."""
    return {
        "title": API_TITLE,
        "version": API_VERSION,
        "endpoints": {
            "health": "/health",
            "detect": "/detect (POST)",
            "detections": "/detections (GET, future)",
            "docs": "/docs (Swagger UI)",
            "redoc": "/redoc (ReDoc)"
        },
        "note": "Authentication removed: endpoints are publicly accessible"
    }


# Backwards-compatible root routes (also expose endpoints without /v1 prefix for tests and older clients)
@app.get("/", tags=["Info"])
async def root_alias():
    return await root()


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_alias():
    return await health_check()


@app.post(
    "/detect",
    response_model=DetectionResponse,
    tags=["Detection"],
    summary="Run object detection on image (alias)",
)
async def detect_alias(request: Request, file: UploadFile = File(...), confidence_threshold: float = Form(CONFIDENCE_THRESHOLD_DEFAULT), user_id: str = Depends(get_current_user)):
    return await detect(request, file, confidence_threshold, user_id)


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": "HTTP_ERROR",
            "request_id": request.headers.get("X-Request-ID", "unknown")
        },
        headers=exc.headers
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
