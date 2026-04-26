"""
Utility functions for image validation, mask encoding/decoding, and helper operations.
"""
import base64
import io
from typing import Tuple, Optional
import numpy as np
from PIL import Image
from app.config import ALLOWED_IMAGE_FORMATS, MAX_FILE_SIZE


def validate_image_file(
    content_type: str,
    file_size: int,
    max_size: int = MAX_FILE_SIZE
) -> Tuple[bool, Optional[str]]:
    """
    Validate image file type and size.
    
    Args:
        content_type: MIME type from file upload
        file_size: Size of file in bytes
        max_size: Maximum allowed file size in bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Handle missing content_type
    if not content_type:
        return False, "File content type not detected. Please ensure file has proper extension"
    
    if not content_type.startswith("image/"):
        return False, "File must be an image"
    
    # Extract format from content type (e.g., "image/jpeg" -> "jpeg")
    try:
        format_from_mime = content_type.split("/")[1].lower()
        if format_from_mime == "jpg":
            format_from_mime = "jpeg"
    except IndexError:
        return False, "Invalid content type"
    
    # Check if format is allowed
    allowed_formats_normalized = [fmt.lower() for fmt in ALLOWED_IMAGE_FORMATS]
    if format_from_mime not in allowed_formats_normalized:
        allowed_str = ", ".join(ALLOWED_IMAGE_FORMATS)
        return False, f"Unsupported image format. Allowed: {allowed_str}"
    
    # Check file size
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"File size exceeds maximum of {max_mb:.1f}MB"
    
    return True, None


def load_image_as_rgb(file_bytes: bytes) -> Tuple[Image.Image, Optional[str]]:
    """
    Load image from bytes and convert to RGB.
    
    Args:
        file_bytes: Image file content as bytes
        
    Returns:
        Tuple of (PIL Image in RGB mode, error message)
    """
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image_rgb = image.convert("RGB")
        return image_rgb, None
    except Exception as e:
        return None, f"Failed to load image: {str(e)}"


def encode_mask_to_rle(mask: np.ndarray) -> str:
    """
    Encode binary segmentation mask to run-length encoding (RLE) as base64 string.
    
    This approach minimizes JSON payload size compared to storing raw mask data.
    
    Args:
        mask: Binary numpy array (0s and 1s) with shape (H, W)
        
    Returns:
        Base64-encoded RLE string
    """
    # Vectorized RLE using numpy to avoid Python loops over pixels
    mask_flat = mask.flatten().astype(np.uint8)

    if mask_flat.size == 0:
        return ""

    # Find boundaries where value changes
    diffs = np.diff(mask_flat)
    if diffs.size == 0:
        # Single-value mask
        vals = [int(mask_flat[0])]
        counts = [int(mask_flat.size)]
    else:
        idx = np.where(diffs != 0)[0] + 1
        # include start and end
        idx = np.concatenate(([0], idx, [mask_flat.size]))
        vals = []
        counts = []
        for i in range(len(idx) - 1):
            start = idx[i]
            end = idx[i + 1]
            vals.append(int(mask_flat[start]))
            counts.append(int(end - start))

    rle_bytes = bytearray()
    for value, count in zip(vals, counts):
        rle_bytes.append(value)
        # variable-length encoding for count
        while count > 255:
            rle_bytes.append(255)
            count -= 255
        rle_bytes.append(count)

    return base64.b64encode(bytes(rle_bytes)).decode('utf-8')


def decode_rle_to_mask(
    rle_string: str,
    height: int,
    width: int
) -> Optional[np.ndarray]:
    """
    Decode RLE (base64) back to binary mask.
    
    Args:
        rle_string: Base64-encoded RLE string
        height: Expected mask height
        width: Expected mask width
        
    Returns:
        Binary numpy array (shape: H, W) or None if decoding fails
    """
    try:
        rle_bytes = base64.b64decode(rle_string)
        
        mask_flat = []
        i = 0
        while i < len(rle_bytes):
            value = rle_bytes[i]
            i += 1
            
            # Read count (supports variable-length encoding)
            count = 0
            while i < len(rle_bytes) and (count == 0 or rle_bytes[i-1] == 255):
                count += rle_bytes[i]
                i += 1
                if count > 0 and rle_bytes[i-1] != 255:
                    break
            
            mask_flat.extend([value] * count)
        
        mask_flat = np.array(mask_flat, dtype=np.uint8)
        expected_size = height * width
        
        if len(mask_flat) != expected_size:
            return None
        
        return mask_flat.reshape((height, width))
    except Exception:
        return None


def calculate_mask_area(mask: np.ndarray) -> int:
    """
    Calculate the number of pixels in a binary mask.
    
    Args:
        mask: Binary numpy array
        
    Returns:
        Number of True/non-zero pixels
    """
    return int(np.sum(mask > 0))


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: Dividend
        denominator: Divisor
        default: Value to return if denominator is zero
        
    Returns:
        Result of division or default value
    """
    if denominator == 0:
        return default
    return numerator / denominator
