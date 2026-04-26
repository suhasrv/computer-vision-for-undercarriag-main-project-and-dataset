"""
YOLO inference module for running YOLOv8 model on images.
Supports PyTorch, TorchScript, and ONNX model formats.

This module supports a lightweight development mode (`DEV_MODE`) where a
`DummyDetector` is used so detection can be tested without a GPU or a real
model. It also imports the real `YOLO` class from `ultralytics` when
available.
"""
import time
from typing import List, Tuple, Optional
import os
import numpy as np
from PIL import Image
import logging

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None

from app.config import MODEL_PATH, MODEL_FORMAT, MODEL_CLASSES
from app.utils import encode_mask_to_rle, calculate_mask_area

logger = logging.getLogger(__name__)


class DummyDetector:
    """Simple deterministic detector used for development/testing.

    Returns a single high-confidence detection covering the center of the
    image. This allows exercising the HTTP stack and response formatting
    without requiring a real model.
    """
    def __init__(self):
        pass

    def is_loaded(self) -> bool:
        return True

    def predict(self, image: Image.Image, conf_threshold: float = 0.25, iou_threshold: float = 0.45):
        h, w = image.height, image.width
        x1, y1, x2, y2 = w * 0.1, h * 0.1, w * 0.9, h * 0.9
        detection = {
            "bbox": [x1, y1, x2, y2],
            "class_id": 0,
            "class_name": MODEL_CLASSES.get(0, "class_0"),
            "confidence": 0.95,
            "mask_rle": "",
            "area": int((x2 - x1) * (y2 - y1))
        }
        # Simulate small processing time
        return [detection], 10.0


class YOLODetector:
    """
    Wrapper around Ultralytics YOLO model for instance segmentation.
    Handles model loading and inference with configurable formats.
    """

    def __init__(self, model_path: str, model_format: str = "pt"):
        self.model_path = model_path
        self.model_format = model_format
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        """Load YOLO model from file or fall back to DummyDetector in DEV_MODE."""
        try:
            logger.info(f"Loading YOLO model from {self.model_path} (format: {self.model_format})")

            # DEV_MODE allows using the dummy detector for fast local testing
            if os.getenv("DEV_MODE", "False").lower() in ("1", "true", "yes"):
                logger.info("DEV_MODE enabled: using DummyDetector")
                self.model = DummyDetector()
                return

            if YOLO is None:
                raise RuntimeError("Ultralytics library not available")

            self.model = YOLO(self.model_path)
            logger.info("Model loaded successfully")

        except Exception as e:
            error_msg = f"Failed to load YOLO model: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def is_loaded(self) -> bool:
        return self.model is not None

    def predict(self, image: Image.Image, conf_threshold: float = 0.25, iou_threshold: float = 0.45) -> Tuple[List[dict], float]:
        if not self.is_loaded():
            raise RuntimeError("Model not loaded")

        if not isinstance(image, Image.Image):
            raise ValueError("Image must be PIL Image object")

        # If using DummyDetector, delegate directly
        if isinstance(self.model, DummyDetector):
            return self.model.predict(image, conf_threshold, iou_threshold)

        # Convert PIL to numpy array (RGB) and run real inference
        img_np = np.array(image)
        start_time = time.time()
        results = self.model(img_np, conf=conf_threshold, iou=iou_threshold, verbose=False)
        processing_time_ms = (time.time() - start_time) * 1000

        result = results[0]
        detections = []

        if result.boxes is not None and len(result.boxes) > 0:
            for i, box in enumerate(result.boxes):
                detection = self._extract_detection(box=box, result=result, box_index=i, image_height=image.height, image_width=image.width)
                if detection is not None:
                    detections.append(detection)

        logger.info(f"Inference complete: {len(detections)} detections in {processing_time_ms:.1f}ms")
        return detections, processing_time_ms

    def _extract_detection(self, box, result, box_index: int, image_height: int, image_width: int) -> Optional[dict]:
        try:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            class_id = int(box.cls[0])
            class_name = MODEL_CLASSES.get(class_id, f"unknown_{class_id}")
            confidence = float(box.conf[0])

            mask_rle = None
            area = None
            if result.masks is not None and result.masks.data is not None:
                try:
                    mask_tensor = result.masks.data[box_index]
                    mask_np = mask_tensor.cpu().numpy().astype(np.uint8)

                    if mask_np.shape != (image_height, image_width):
                        mask_np = np.array(Image.fromarray(mask_np).resize((image_width, image_height), resample=Image.BILINEAR))
                        mask_np = (mask_np > 0.5).astype(np.uint8)

                    mask_rle = encode_mask_to_rle(mask_np)
                    area = calculate_mask_area(mask_np)
                except Exception as e:
                    logger.warning(f"Failed to extract mask for detection {box_index}: {e}")

            detection = {"bbox": [x1, y1, x2, y2], "class_id": class_id, "class_name": class_name, "confidence": confidence, "mask_rle": mask_rle, "area": area}
            return detection

        except Exception as e:
            logger.error(f"Error extracting detection {box_index}: {e}")
            return None
