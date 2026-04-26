from ultralytics import YOLO
import torch
import ultralytics.nn.tasks as _ul_tasks


def main():

    # Allowlist ultralytics model class for torch.safe loading of checkpoints
    try:
        torch.serialization.add_safe_globals([
            _ul_tasks.SegmentationModel,
            torch.nn.modules.container.Sequential,
            torch.nn.Module,
        ])
    except Exception:
        pass

    # As a last resort allow full unpickling for this trusted local checkpoint
    try:
        _orig_torch_load = torch.load
        def _force_load(*args, **kwargs):
            kwargs.setdefault('weights_only', False)
            return _orig_torch_load(*args, **kwargs)
        torch.load = _force_load
    except Exception:
        pass

    model = YOLO("runs/weights/best.pt")

    results = model.val(
        data="data.yaml",
        workers=0
    )

    print("\n--- Instance Segmentation Metrics ---")

    metrics = results.seg   # correct attribute

    print(f"mAP50-95: {metrics.map:.4f}")
    print(f"mAP50: {metrics.map50:.4f}")
    print(f"Precision: {metrics.p.mean():.4f}")
    print(f"Recall: {metrics.r.mean():.4f}")

    print("\n--- Class-wise mAP ---")

    for i, name in model.names.items():
        print(f"{name}: {results.maps[i]:.4f}")

if __name__ == "__main__":
    main()