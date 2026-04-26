#!/usr/bin/env python3
"""Benchmark /v1/detect endpoint (HTTP) for best-case latency.
Sends N sequential requests with a small test image and reports min/avg/median.
"""
import time
import requests
from pathlib import Path
import statistics

# Config
URL = "http://127.0.0.1:8000/v1/detect"
TOKEN = "Bearer eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAidGVzdC11c2VyIiwgImlhdCI6IDEyMzQ1Njc4OTAsICJleHAiOiA5OTk5OTk5OTk5fQ.dGVzdF9zaWduYXR1cmU"
ITERATIONS = 10
TIMEOUT = 60

# Locate a small test image (search for jpg/png)
images = list(Path('../test/images').glob('*.*'))
if not images:
    print("No test images found in ../test/images")
    raise SystemExit(1)

test_image = images[0]
print(f"Using image: {test_image.name} ({test_image.stat().st_size/1024:.1f} KB)")

headers = {"Authorization": TOKEN}

latencies = []
processing_times = []

for i in range(ITERATIONS):
    with open(test_image, 'rb') as f:
        files = {"file": (test_image.name, f, 'image/jpeg')}
        start = time.perf_counter()
        resp = requests.post(URL, files=files, headers=headers, timeout=TIMEOUT)
        elapsed = (time.perf_counter() - start) * 1000.0

    print(f"Iteration {i+1}: status={resp.status_code}, rtt={elapsed:.1f}ms")

    if resp.status_code == 200:
        try:
            data = resp.json()
            proc = data.get('processing_time_ms')
            if proc is not None:
                processing_times.append(proc)
            latencies.append(elapsed)
        except Exception:
            latencies.append(elapsed)
    else:
        latencies.append(elapsed)

# Report
if latencies:
    print('\nLatency summary (ms):')
    print(f"  - min: {min(latencies):.1f}")
    print(f"  - mean: {statistics.mean(latencies):.1f}")
    print(f"  - median: {statistics.median(latencies):.1f}")
    print(f"  - max: {max(latencies):.1f}")

if processing_times:
    print('\nServer processing_time_ms summary (ms):')
    print(f"  - min: {min(processing_times):.1f}")
    print(f"  - mean: {statistics.mean(processing_times):.1f}")
    print(f"  - median: {statistics.median(processing_times):.1f}")

print('\nBest-case (min) RTT:', f"{min(latencies):.1f}ms")
print('Done')
