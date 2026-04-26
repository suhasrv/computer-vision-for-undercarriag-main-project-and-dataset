#!/usr/bin/env python3
"""Test the detection API endpoint"""
import json
import requests
from pathlib import Path

# Token generated earlier
token = "Bearer eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAidGVzdC11c2VyIiwgImlhdCI6IDEyMzQ1Njc4OTAsICJleHAiOiA5OTk5OTk5OTk5fQ.dGVzdF9zaWduYXR1cmU"

# Select first test image
test_images = list(Path('../test/images').glob('*jpg'))
if test_images:
    test_image = test_images[0]
    print(f"Testing with image: {test_image.name}")
    print(f"Image size: {test_image.stat().st_size / 1024:.1f} KB")
    print()
    
    # Prepare request with proper MIME type
    headers = {"Authorization": token}
    # Open file and explicitly set MIME type
    file_obj = open(test_image, "rb")
    files = {"file": ("test_image.jpg", file_obj, "image/jpeg")}
    
    # Send POST request
    print("Sending request to http://127.0.0.1:8000/v1/detect")
    try:
        response = requests.post(
            "http://127.0.0.1:8000/v1/detect",
            files=files,
            headers=headers,
            timeout=120
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print()
        
        # Parse and display response
        if response.status_code == 200:
            data = response.json()
            print("✅ Detection Successful!")
            print(f"\nResponse Summary:")
            print(f"  - Request ID: {data.get('request_id')}")
            print(f"  - User ID: {data.get('user_id')}")
            print(f"  - Processed At: {data.get('processed_at')}")
            print(f"  - Number of detections: {len(data.get('detections', []))}")
            
            if data.get('detections'):
                print(f"\nFirst detection details:")
                det = data['detections'][0]
                print(f"  - Class: {det.get('class_name')} (ID: {det.get('class_id')})")
                print(f"  - Confidence: {det.get('confidence'):.2%}")
                print(f"  - BBox: {det.get('bbox')}")
                print(f"  - Mask RLE: {det.get('mask_rle', 'N/A')[:50]}...")
            
            print(f"\nFull response (first 1000 chars):")
            print(json.dumps(data, indent=2)[:1000])
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except requests.ConnectionError as e:
        print(f"❌ Connection Error: {e}")
        print("Server may not be running on http://127.0.0.1:8001")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        file_obj.close()
else:
    print("No test images found")
