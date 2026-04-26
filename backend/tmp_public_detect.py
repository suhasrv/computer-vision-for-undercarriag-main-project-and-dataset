import requests
import json
import os

img_path = os.path.join(os.path.dirname(__file__), '..', 'test', 'images', '2-60-_jpg.rf.70d6f7aedc5629bdcdec1097212540c3.jpg')
img_path = os.path.normpath(img_path)
print('Using image:', img_path)
with open(img_path, 'rb') as f:
    files = {'file': ('test.jpg', f, 'image/jpeg')}
    r = requests.post('http://127.0.0.1:8001/v1/detect', files=files, timeout=120)
    print('Status:', r.status_code)
    print('Content-Type:', r.headers.get('content-type'))
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)
