import pytest

from app.utils import validate_image_file, MAX_FILE_SIZE


def test_validate_image_missing_content_type():
    valid, msg = validate_image_file(None, 100)
    assert not valid
    assert "content type" in msg.lower() or "must be an image" in msg.lower()


def test_validate_image_wrong_type():
    valid, msg = validate_image_file("text/plain", 100)
    assert not valid
    assert "must be an image" in msg.lower()


def test_validate_image_size_exceeded():
    valid, msg = validate_image_file("image/jpeg", MAX_FILE_SIZE + 1)
    assert not valid
    assert "exceeds" in msg.lower()
