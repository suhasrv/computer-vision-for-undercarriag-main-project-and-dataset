from app.auth import create_test_token
import requests
from PIL import Image
import io, sys

# Create test token
token = create_test_token("test-user-uuid")
print("TEST_TOKEN:", token)

# Create small in-memory JPEG
img = Image.new('RGB', (640, 480), color='red')
buf = io.BytesIO()
img.save(buf, format='JPEG')
buf.seek(0)

files = {'file': ('test.jpg', buf.read(), 'image/jpeg')}
headers = {'Authorization': token}

try:
    r = requests.post('http://127.0.0.1:8000/v1/detect', files=files, headers=headers, timeout=60)
    print('STATUS_CODE:', r.status_code)
    print('RESPONSE_LEN:', len(r.text))
    print('RESPONSE_PREVIEW:', r.text[:1000])
except Exception as e:
    print('ERROR:', type(e).__name__, e)
    sys.exit(2)
