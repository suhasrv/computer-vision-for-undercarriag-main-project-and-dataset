# Lightweight stub for ultralytics to allow running tests without heavy deps
import importlib.util
import importlib
import sys
import os
import traceback

def _load_real_ultralytics():
    this_file = os.path.abspath(__file__)
    pkg_dir = os.path.dirname(this_file)

    # First attempt: temporarily remove this package directory from sys.path
    # so a standard import can find an installed 'ultralytics' package.
    orig_sys_path = list(sys.path)
    try:
        sys.path = [p for p in sys.path if p and os.path.abspath(p) != pkg_dir]
        try:
            mod = importlib.import_module("ultralytics")
            mod_file = getattr(mod, "__file__", None)
            if mod_file and os.path.abspath(mod_file) != this_file:
                return mod
        except Exception as e:
            sys.stderr.write("[ultralytics stub] import_module('ultralytics') failed:\n")
            sys.stderr.write("".join(traceback.format_exception(type(e), e, e.__traceback__)))
            # fall through to file scan fallback
            pass
    finally:
        sys.path = orig_sys_path

    # Fallback: scan sys.path for an alternative ultralytics __init__.py
    for p in sys.path:
        try:
            candidate = os.path.join(p, "ultralytics", "__init__.py")
            if not os.path.isfile(candidate):
                continue
            candidate_abspath = os.path.abspath(candidate)
            if candidate_abspath == this_file:
                continue
            spec = importlib.util.spec_from_file_location("ultralytics", candidate)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                # ensure absolute imports inside the package resolve to this module
                sys.modules["ultralytics"] = mod
                try:
                    spec.loader.exec_module(mod)
                    return mod
                except Exception as e:
                    # remove any partially loaded module
                    sys.modules.pop("ultralytics", None)
                    raise
        except Exception as e:
            sys.stderr.write(f"[ultralytics stub] loading candidate {candidate} failed:\n")
            sys.stderr.write("".join(traceback.format_exception(type(e), e, e.__traceback__)))
            continue
    return None

_real = _load_real_ultralytics()
if _real is not None and hasattr(_real, "YOLO"):
    YOLO = _real.YOLO
else:
    class YOLO:
        def __init__(self, model_path=None):
            raise RuntimeError("Ultralytics library not available in test environment (stub).")
