"""
Test suite for inference module.
"""
import pytest
import numpy as np
from PIL import Image
from app.inference import YOLODetector
from app.utils import encode_mask_to_rle, decode_rle_to_mask, calculate_mask_area


class TestMaskEncoding:
    """Test mask RLE encoding/decoding round-trip."""
    
    def test_encode_decode_simple_mask(self):
        """Test encoding and decoding a simple binary mask."""
        # Create simple test mask: vertical stripe
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[:, 40:60] = 1
        
        # Encode
        rle_string = encode_mask_to_rle(mask)
        assert isinstance(rle_string, str)
        assert len(rle_string) > 0
        
        # Decode
        decoded_mask = decode_rle_to_mask(rle_string, height=100, width=100)
        assert decoded_mask is not None
        assert decoded_mask.shape == (100, 100)
        
        # Verify round-trip
        assert np.array_equal(mask, decoded_mask)
    
    def test_encode_decode_complex_mask(self):
        """Test with more complex mask (circle)."""
        # Create circular mask
        h, w = 200, 200
        mask = np.zeros((h, w), dtype=np.uint8)
        y, x = np.ogrid[:h, :w]
        mask[((x - w//2)**2 + (y - h//2)**2) <= (w//4)**2] = 1
        
        # Encode and decode
        rle_string = encode_mask_to_rle(mask)
        decoded = decode_rle_to_mask(rle_string, h, w)
        
        assert decoded is not None
        assert np.array_equal(mask, decoded)
    
    def test_encode_empty_mask(self):
        """Test encoding all-zero mask."""
        mask = np.zeros((50, 50), dtype=np.uint8)
        rle_string = encode_mask_to_rle(mask)
        decoded = decode_rle_to_mask(rle_string, 50, 50)
        assert np.array_equal(mask, decoded)
    
    def test_encode_full_mask(self):
        """Test encoding all-ones mask."""
        mask = np.ones((50, 50), dtype=np.uint8)
        rle_string = encode_mask_to_rle(mask)
        decoded = decode_rle_to_mask(rle_string, 50, 50)
        assert np.array_equal(mask, decoded)
    
    def test_calculate_mask_area(self):
        """Test mask area calculation."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[:, 40:60] = 1
        
        area = calculate_mask_area(mask)
        assert area == 100 * 20  # 100 rows * 20 columns
    
    def test_invalid_rle_size_mismatch(self):
        """Test decoding with wrong dimensions."""
        mask = np.zeros((50, 50), dtype=np.uint8)
        mask[:25, :25] = 1
        
        rle_string = encode_mask_to_rle(mask)
        
        # Try to decode with wrong dimensions
        decoded = decode_rle_to_mask(rle_string, height=100, width=100)
        assert decoded is None


class TestImageLoading:
    """Test image loading utilities."""
    
    def test_create_test_image(self):
        """Verify test image creation for other tests."""
        img = Image.new("RGB", (640, 480), color="red")
        assert img.width == 640
        assert img.height == 480
        assert img.mode == "RGB"


# Integration tests (requires actual model - optional)
class TestYOLODetector:
    """Test YOLO detector initialization."""
    
    @pytest.mark.skip(reason="Requires model file to be present")
    def test_detector_initialization(self):
        """Test detector can be initialized (requires model)."""
        # This test is skipped unless model file exists
        try:
            detector = YOLODetector("models/yolov8m.torchscript", "torchscript")
            assert detector.is_loaded()
        except RuntimeError:
            pytest.skip("Model file not available")
    
    @pytest.mark.skip(reason="Requires model file to be present")
    def test_predict_shape(self):
        """Test prediction output shape."""
        img = Image.new("RGB", (640, 480), color="blue")
        
        try:
            detector = YOLODetector("models/yolov8m.torchscript", "torchscript")
            detections, time_ms = detector.predict(img, conf_threshold=0.25)
            
            assert isinstance(detections, list)
            assert isinstance(time_ms, float)
            assert time_ms > 0
        except RuntimeError:
            pytest.skip("Model file not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
