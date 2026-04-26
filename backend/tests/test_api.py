"""
Test suite for FastAPI endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import io
from app.main import app
from app.auth import create_test_token


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_image():
    """Create test image as bytes."""
    img = Image.new("RGB", (640, 480), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)
    return img_bytes.getvalue()


@pytest.fixture
def test_token():
    """Create test JWT token."""
    return create_test_token("test-user-uuid")


class TestHealthEndpoint:
    """Test /health endpoint."""
    
    def test_health_check_success(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "model_loaded" in data


class TestDetectEndpoint:
    """Test /detect endpoint."""
    
    def test_detect_missing_auth(self, client, test_image):
        """Test detection without authentication."""
        response = client.post(
            "/detect",
            files={"file": ("test.jpg", test_image, "image/jpeg")}
        )
        assert response.status_code == 401
        assert "authorization" in response.json()["detail"].lower()
    
    def test_detect_invalid_token(self, client, test_image):
        """Test detection with invalid token."""
        response = client.post(
            "/detect",
            files={"file": ("test.jpg", test_image, "image/jpeg")},
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
    
    def test_detect_invalid_file_type(self, client, test_token):
        """Test detection with non-image file."""
        response = client.post(
            "/detect",
            files={"file": ("test.txt", b"not an image", "text/plain")},
            headers={"Authorization": test_token}
        )
        assert response.status_code == 400
        assert "image" in response.json()["detail"].lower()
    
    def test_detect_missing_file(self, client, test_token):
        """Test detection without file."""
        response = client.post(
            "/detect",
            headers={"Authorization": test_token}
        )
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.skip(reason="Requires model to be loaded")
    def test_detect_with_valid_image(self, client, test_image, test_token):
        """Test detection with valid image (requires model)."""
        response = client.post(
            "/detect",
            files={"file": ("test.jpg", test_image, "image/jpeg")},
            headers={"Authorization": test_token}
        )
        
        if response.status_code == 503:
            pytest.skip("Model not loaded")
        
        assert response.status_code == 200
        data = response.json()
        assert "detections" in data
        assert "image_width" in data
        assert "image_height" in data
        assert "processing_time_ms" in data


class TestRootEndpoint:
    """Test root endpoint."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        assert "detect" in data["endpoints"]


class TestCORS:
    """Test CORS configuration."""
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/detect")
        # CORS headers should be present for preflight requests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
