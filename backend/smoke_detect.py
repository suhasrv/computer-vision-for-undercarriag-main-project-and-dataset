"""Smoke test: POST a sample image to /v1/detect with a test JWT.

Run from the workspace root with the backend venv Python:
  backend\venv\Scripts\python.exe backend\smoke_detect.py
"""
import os
import sys
import json
import base64
import httpx


def create_test_token(user_id: str) -> str:
    payload = {"sub": user_id, "iat": 1234567890, "exp": 9999999999}
    payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    header_encoded = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    signature_encoded = base64.urlsafe_b64encode(b"test_signature").decode().rstrip("=")
    token = f"{header_encoded}.{payload_encoded}.{signature_encoded}"
    return f"Bearer {token}"


def main():
    # File path (relative to backend/ since this script lives there)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_rel = os.path.join("..", "test", "images", "1-1-_webp.rf.dc462978d56556f6268045711eba9aff.jpg")
    image_path = os.path.abspath(os.path.join(script_dir, image_rel))

    if not os.path.exists(image_path):
        print("ERROR: sample image not found:", image_path)
        sys.exit(2)

    token = create_test_token("smoke-test-user")
    headers = {"Authorization": token}

    url = "http://127.0.0.1:8000/v1/detect"
    print(f"Posting {image_path} -> {url}")

    with open(image_path, "rb") as f:
        files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
        data = {"confidence_threshold": "0.25"}
        try:
            with httpx.Client(timeout=60.0) as client:
                r = client.post(url, headers=headers, data=data, files=files)
        except Exception as e:
            print("Request failed:", e)
            sys.exit(3)

    print("Status:", r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)


if __name__ == "__main__":
    main()
