#!/usr/bin/env python3
"""Compute dataset counts, run validation (mAP) and measure sample inference latency.

Produces a JSON results file with key metrics and environment info.

Usage examples:
  python scripts/compute_metrics.py --model runs/weights/best.pt --data data.yaml --split val --device cpu --sample 20 --out results/metrics-validation.json

If the model file is missing this script exits with a clear message.
"""
import argparse
import json
import os
import time
import glob
from pathlib import Path
import platform


def parse_data_yaml(path):
    vals = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('train:'):
                vals['train'] = line.split(':', 1)[1].strip()
            elif line.startswith('val:'):
                vals['val'] = line.split(':', 1)[1].strip()
            elif line.startswith('test:'):
                vals['test'] = line.split(':', 1)[1].strip()
    return vals


def count_images(folder):
    if not folder:
        return 0
    folder = os.path.abspath(folder)
    if not os.path.isdir(folder):
        return 0
    patterns = ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.bmp', '*.tif', '*.tiff']
    total = 0
    for p in patterns:
        total += len(glob.glob(os.path.join(folder, p)))
    return total


def percentile(sorted_list, p):
    if not sorted_list:
        return None
    if p <= 0:
        return sorted_list[0]
    if p >= 100:
        return sorted_list[-1]
    k = (len(sorted_list) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_list) - 1)
    if f == c:
        return sorted_list[int(k)]
    d0 = sorted_list[f] * (c - k)
    d1 = sorted_list[c] * (k - f)
    return d0 + d1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='runs/weights/best.pt')
    parser.add_argument('--data', default='data.yaml')
    parser.add_argument('--split', default='val', choices=['train', 'val', 'test'])
    parser.add_argument('--device', default='cpu', help='cpu or cuda (e.g. cuda:0)')
    parser.add_argument('--sample', type=int, default=20, help='how many images to time')
    parser.add_argument('--repeats', type=int, default=1, help='repeats per image')
    parser.add_argument('--out', default=None, help='output JSON path')
    parser.add_argument('--workers', type=int, default=0, help='workers for model.val')
    args = parser.parse_args()

    out_path = args.out
    if out_path is None:
        out_dir = Path('results')
        out_dir.mkdir(exist_ok=True)
        ts = time.strftime('%Y%m%d-%H%M%S')
        out_path = out_dir / f'metrics-{args.split}-{ts}.json'
    else:
        out_path = Path(out_path)

    model_path = Path(args.model)
    if not model_path.exists():
        print('Model file not found:', model_path)
        print('Place your trained model at the given path or pass --model to point to a model file.')
        raise SystemExit(2)

    try:
        from ultralytics import YOLO
    except Exception as e:
        print('ultralytics is required to run validation. Install backend/requirements.txt in your venv.')
        raise

    print('Loading model:', model_path)
    model = YOLO(str(model_path))

    results = None
    try:
        print('Running validation (this may take a while)...')
        results = model.val(data=str(args.data), workers=args.workers, device=args.device)
    except Exception as e:
        print('Validation failed:', e)

    metrics = {}
    if results is not None:
        # Best-effort extraction compatible with ultralytics outputs
        try:
            seg = getattr(results, 'seg', None)
            if seg is not None:
                metrics['mAP50-95'] = float(getattr(seg, 'map', None) or 0.0)
                metrics['mAP50'] = float(getattr(seg, 'map50', None) or 0.0)
                # precision & recall may be arrays
                p = getattr(seg, 'p', None)
                r = getattr(seg, 'r', None)
                metrics['precision_mean'] = float(p.mean()) if p is not None else None
                metrics['recall_mean'] = float(r.mean()) if r is not None else None
        except Exception:
            pass

    # dataset counts
    data_yaml = Path(args.data)
    data_base = data_yaml.parent
    parsed = parse_data_yaml(str(data_yaml))
    split_path = parsed.get(args.split)
    if split_path:
        split_full = os.path.normpath(os.path.join(data_base, split_path))
    else:
        split_full = None

    counts = {}
    counts['train'] = count_images(os.path.normpath(os.path.join(data_base, parsed.get('train', ''))) )
    counts['val'] = count_images(os.path.normpath(os.path.join(data_base, parsed.get('val', ''))) )
    counts['test'] = count_images(os.path.normpath(os.path.join(data_base, parsed.get('test', ''))) )

    latency_stats = None
    if split_full and os.path.isdir(split_full):
        # pick sample images
        imgs = []
        exts = ('*.jpg', '*.jpeg', '*.png', '*.webp', '*.bmp', '*.tif', '*.tiff')
        for e in exts:
            imgs.extend(sorted(glob.glob(os.path.join(split_full, e))))
        imgs = imgs[:args.sample]
        times = []
        if imgs:
            print(f'Measuring latency on {len(imgs)} images (repeats={args.repeats})')
            for p in imgs:
                for _ in range(max(1, args.repeats)):
                    t0 = time.time()
                    try:
                        _ = model.predict(p, device=args.device, conf=0.25)
                    except Exception as e:
                        print('Inference error for', p, e)
                        continue
                    times.append((time.time() - t0) * 1000.0)
            times_sorted = sorted(times)
            latency_stats = {
                'count': len(times_sorted),
                'min_ms': times_sorted[0] if times_sorted else None,
                'p50_ms': percentile(times_sorted, 50) if times_sorted else None,
                'p90_ms': percentile(times_sorted, 90) if times_sorted else None,
                'p95_ms': percentile(times_sorted, 95) if times_sorted else None,
                'mean_ms': (sum(times_sorted) / len(times_sorted)) if times_sorted else None,
            }

    out = {
        'model_path': str(model_path),
        'data_yaml': str(data_yaml),
        'split': args.split,
        'counts': counts,
        'metrics': metrics,
        'latency': latency_stats,
        'environment': {
            'platform': platform.platform(),
            'python': platform.python_version(),
        },
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)

    print('Wrote metrics to', out_path)


if __name__ == '__main__':
    main()
