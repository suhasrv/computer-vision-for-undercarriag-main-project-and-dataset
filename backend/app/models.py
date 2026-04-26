"""
Pydantic models for request/response schemas.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Detection(BaseModel):
    """Single detection result with bounding box and segmentation mask."""
    bbox: List[float] = Field(
        ..., 
        description="Bounding box [x1, y1, x2, y2] in pixel coordinates"
    )
    class_id: int = Field(..., description="Class ID (0=corrosion, 1=dents)")
    class_name: str = Field(..., description="Class name")
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Confidence score (0-1)"
    )
    mask_rle: Optional[str] = Field(
        None,
        description="Run-length encoded segmentation mask (base64)"
    )
    area: Optional[int] = Field(
        None,
        description="Pixel area of the segmentation mask"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "bbox": [100.5, 150.2, 300.8, 400.1],
                "class_id": 0,
                "class_name": "corrosion",
                "confidence": 0.95,
                "mask_rle": "eJwDAAAAAAE=",
                "area": 15000
            }
        }


class DetectionResponse(BaseModel):
    """Response model for detection endpoint."""
    detections: List[Detection] = Field(..., description="List of detected objects")
    image_width: int = Field(..., description="Image width in pixels")
    image_height: int = Field(..., description="Image height in pixels")
    image_path: Optional[str] = Field(
        None, 
        description="Path to uploaded image in storage"
    )
    image_url: Optional[str] = Field(
        None,
        description="Public URL to uploaded image"
    )
    processing_time_ms: float = Field(
        ...,
        description="Inference processing time in milliseconds"
    )
    detection_count: int = Field(
        ...,
        description="Total number of detections"
    )
    confidence_threshold: float = Field(
        ...,
        description="Confidence threshold used"
    )
    inspection_id: Optional[str] = Field(
        None,
        description="ID of the saved inspection record in the database (if saved)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "detections": [
                    {
                        "bbox": [100.0, 150.0, 300.0, 400.0],
                        "class_id": 0,
                        "class_name": "corrosion",
                        "confidence": 0.92,
                        "mask_rle": "eJwDAAAAAAE=",
                        "area": 15000
                    }
                ],
                "image_width": 640,
                "image_height": 480,
                "image_path": "detection-images/user-uuid/2026-04-09/image.jpg",
                "image_url": "https://project.supabase.co/storage/v1/object/public/...",
                "processing_time_ms": 125.5,
                "detection_count": 1,
                "confidence_threshold": 0.25
            }
        }


class DetectionHistoryItem(BaseModel):
    """Single detection record from user history."""
    id: str = Field(..., description="UUID of detection record")
    created_at: datetime = Field(..., description="Timestamp of detection")
    image_path: str = Field(..., description="Path to image in storage")
    image_url: str = Field(..., description="Public URL to image")
    detection_count: int = Field(..., description="Number of detections")
    image_width: int = Field(..., description="Image width")
    image_height: int = Field(..., description="Image height")
    detections: List[Detection] = Field(..., description="Detection results")


class DetectionHistoryResponse(BaseModel):
    """Response model for getting user's detection history."""
    items: List[DetectionHistoryItem] = Field(..., description="List of detection records")
    total_count: int = Field(..., description="Total number of records (for pagination)")
    limit: int = Field(..., description="Limit used in query")
    offset: int = Field(..., description="Offset used in query")


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code for client handling")
    request_id: Optional[str] = Field(
        None,
        description="Request ID for support/debugging"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "File must be an image",
                "error_code": "INVALID_FILE_TYPE",
                "request_id": "req_12345"
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Health status")
    version: str = Field(..., description="API version")
    model_loaded: bool = Field(..., description="Whether inference model is loaded")
    supabase_connected: bool = Field(..., description="Whether database client is initialized")


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class JobStatusItem(BaseModel):
    id: str
    user_id: Optional[str]
    status: str
    meta: Optional[dict]
    result: Optional[dict]
    created_at: Optional[datetime]


class JobCreateResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job: JobStatusItem
