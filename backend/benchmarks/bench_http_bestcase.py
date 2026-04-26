#!/usr/bin/env python3
"""Benchmark /v1/detect endpoint (HTTP) for latency and concurrency.

Supports sequential runs and concurrent workers. Writes a JSON report when --out is provided.

Examples:
  python bench_http_bestcase.py --url http://127.0.0.1:8000/v1/detect --iterations 20
  python bench_http_bestcase.py --url http://127.0.0.1:8000/v1/detect --duration 30 --workers 8 --out results/http-bench.json
"""
import time
import requests
from pathlib import Path
import statistics
import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed


def percentile(sorted_list, p):
    if not sorted_list:
        return None
    k = (len(sorted_list) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_list) - 1)
    if f == c:
        return sorted_list[int(k)]
    d0 = sorted_list[f] * (c - k)
    d1 = sorted_list[c] * (k - f)
    return d0 + d1


def send_request(url, token, image_path, timeout):
    headers = {"Authorization": token} if token else {}
    with open(image_path, 'rb') as f:
        files = {"file": (Path(image_path).name, f, 'image/jpeg')}
        start = time.perf_counter()
        resp = requests.post(url, files=files, headers=headers, timeout=timeout)
        elapsed = (time.perf_counter() - start) * 1000.0
    processing = None
    try:
        data = resp.json()
        processing = data.get('processing_time_ms')
    except Exception:
        pass
    return elapsed, resp.status_code, processing


def sequential_run(url, token, image, iterations, timeout):
    latencies = []
    processing_times = []
    for i in range(iterations):
        elapsed, status, proc = send_request(url, token, image, timeout)
        print(f"Iteration {i+1}: status={status}, rtt={elapsed:.1f}ms")
        latencies.append(elapsed)
        if proc is not None:
            processing_times.append(proc)
    return latencies, processing_times


def concurrent_run(url, token, image, duration, workers, timeout):
    latencies = []
    processing_times = []
    start_time = time.time()
    futures = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        while time.time() - start_time < duration:
            futures.append(ex.submit(send_request, url, token, image, timeout))
        for fut in as_completed(futures):
            try:
                elapsed, status, proc = fut.result()
                latencies.append(elapsed)
                if proc is not None:
                    processing_times.append(proc)
            except Exception as e:
                print('Request error:', e)
    return latencies, processing_times


def summarize(latencies, processing_times):
    latencies_sorted = sorted(latencies)
    out = {}
    if latencies:
        out['count'] = len(latencies)
        out['min_ms'] = min(latencies)
        out['mean_ms'] = statistics.mean(latencies)
        out['median_ms'] = statistics.median(latencies)
        out['max_ms'] = max(latencies)
        out['p50_ms'] = percentile(latencies_sorted, 50)
        out['p90_ms'] = percentile(latencies_sorted, 90)
        out['p95_ms'] = percentile(latencies_sorted, 95)
    if processing_times:
        out['processing_count'] = len(processing_times)
        out['processing_mean_ms'] = statistics.mean(processing_times)
        out['processing_median_ms'] = statistics.median(processing_times)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000/v1/detect')
    parser.add_argument('--token', default='')
    parser.add_argument('--image', default='../test/images')
    parser.add_argument('--iterations', type=int, default=10)
    parser.add_argument('--workers', type=int, default=1, help='concurrent workers; set >1 to run concurrent mode (requires --duration)')
    parser.add_argument('--duration', type=int, default=0, help='duration in seconds for concurrent mode')
    parser.add_argument('--timeout', type=int, default=60)
    parser.add_argument('--out', default=None, help='output JSON path')
    args = parser.parse_args()

    # locate image
    img_path = None
    p = Path(args.image)
    if p.is_file():
        img_path = str(p)
    else:
        imgs = list(Path(args.image).glob('*.*'))
        if not imgs:
            print('No images found at', args.image)
            raise SystemExit(1)
        img_path = str(imgs[0])

    print('Using image:', Path(img_path).name)

    if args.workers > 1 and args.duration > 0:
        print(f'Running concurrent benchmark: workers={args.workers}, duration={args.duration}s')
        latencies, processing_times = concurrent_run(args.url, args.token, img_path, args.duration, args.workers, args.timeout)
    else:
        print(f'Running sequential benchmark: iterations={args.iterations}')
        latencies, processing_times = sequential_run(args.url, args.token, img_path, args.iterations, args.timeout)

    summary = summarize(latencies, processing_times)
    print('\nSummary:')
    print(json.dumps(summary, indent=2))

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        report = {
            'url': args.url,
            'image': Path(img_path).name,
            'summary': summary,
            'latencies_samples': latencies[:200],
        }
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print('Wrote JSON report to', args.out)


if __name__ == '__main__':
    main()
