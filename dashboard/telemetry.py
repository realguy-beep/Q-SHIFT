"""Best-effort local CPU/RAM/NVIDIA telemetry with useful failure diagnostics."""
from __future__ import annotations

import importlib.util
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import psutil

_nvml = None
_nvml_error = None
_logger = logging.getLogger("qshift.telemetry")


def _log_provider_error(provider: str, operation: str, exc: BaseException) -> str:
    """Log a full traceback once a provider fails; return a readable UI detail."""
    if not _logger.handlers:
        log_path = Path(__file__).resolve().parent / "run_data" / "telemetry_errors.log"
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            _logger.addHandler(handler)
            _logger.setLevel(logging.ERROR)
            _logger.propagate = False
        except Exception:
            logging.basicConfig(level=logging.ERROR)
    detail = f"{type(exc).__name__}: {str(exc) or repr(exc)}"
    _logger.error("GPU telemetry provider=%s operation=%s failed: %s", provider, operation, detail,
                  exc_info=(type(exc), exc, exc.__traceback__))
    return detail


def _empty_gpu(source="unavailable", reason=None, errors=None):
    return {"available": False, "name": None, "utilization_percent": None,
            "memory_used_bytes": None, "memory_total_bytes": None, "memory_percent": None,
            "temperature_c": None, "power_watts": None, "source": source,
            "unavailable_reason": reason, "provider_errors": errors or []}


def _nvml_snapshot() -> tuple[dict, list[str]]:
    global _nvml, _nvml_error
    errors: list[str] = []
    if _nvml is None and _nvml_error is None:
        try:
            import pynvml as nvml
            nvml.nvmlInit()
            _nvml = nvml
        except Exception as exc:
            _nvml_error = _log_provider_error("NVML", "initialization", exc)
    if _nvml is None:
        return _empty_gpu("NVML unavailable", _nvml_error), errors

    result = _empty_gpu("NVML")
    try:
        handle = _nvml.nvmlDeviceGetHandleByIndex(0)
    except Exception as exc:
        errors.append("NVML handle: " + _log_provider_error("NVML", "device handle", exc))
        return result, errors

    def read(field, operation, convert=lambda value: value):
        try:
            result[field] = convert(operation())
        except Exception as exc:
            errors.append(f"NVML {field}: " + _log_provider_error("NVML", field, exc))

    read("name", lambda: _nvml.nvmlDeviceGetName(handle),
         lambda value: value.decode(errors="replace") if isinstance(value, bytes) else str(value))
    read("utilization_percent", lambda: _nvml.nvmlDeviceGetUtilizationRates(handle).gpu, int)
    read("memory_used_bytes", lambda: _nvml.nvmlDeviceGetMemoryInfo(handle).used, int)
    read("memory_total_bytes", lambda: _nvml.nvmlDeviceGetMemoryInfo(handle).total, int)
    read("temperature_c", lambda: _nvml.nvmlDeviceGetTemperature(handle, _nvml.NVML_TEMPERATURE_GPU), float)
    read("power_watts", lambda: _nvml.nvmlDeviceGetPowerUsage(handle) / 1000.0, float)
    if result["memory_used_bytes"] is not None and result["memory_total_bytes"]:
        result["memory_percent"] = 100.0 * result["memory_used_bytes"] / result["memory_total_bytes"]
    core_values = ("name", "utilization_percent", "memory_used_bytes", "memory_total_bytes")
    result["available"] = any(result[key] is not None for key in core_values)
    result["provider_errors"] = errors
    return result, errors


def _nvidia_smi_snapshot() -> tuple[dict, list[str]]:
    fields = ("name", "utilization.gpu", "memory.used", "memory.total", "temperature.gpu", "power.draw")
    exe = shutil.which("nvidia-smi")
    if not exe:
        return _empty_gpu("nvidia-smi unavailable", "nvidia-smi was not found on PATH"), []
    try:
        proc = subprocess.run([exe, "--query-gpu=" + ",".join(fields), "--format=csv,noheader,nounits"],
                              capture_output=True, text=True, timeout=3, check=True)
        row = next(line for line in proc.stdout.splitlines() if line.strip())
        values = [value.strip() for value in row.split(",")]
        if len(values) != len(fields):
            raise ValueError(f"Expected {len(fields)} CSV values from nvidia-smi, received {len(values)}")

        def optional_float(value):
            return None if value.upper() in {"N/A", "[NOT SUPPORTED]", "NOT SUPPORTED", ""} else float(value)

        mem_used_mb, mem_total_mb = optional_float(values[2]), optional_float(values[3])
        gpu = {"available": True, "name": values[0] or None,
               "utilization_percent": optional_float(values[1]),
               "memory_used_bytes": int(mem_used_mb * 1024 * 1024) if mem_used_mb is not None else None,
               "memory_total_bytes": int(mem_total_mb * 1024 * 1024) if mem_total_mb is not None else None,
               "memory_percent": 100.0 * mem_used_mb / mem_total_mb if mem_used_mb is not None and mem_total_mb else None,
               "temperature_c": optional_float(values[4]), "power_watts": optional_float(values[5]),
               "source": "nvidia-smi", "provider_errors": []}
        return gpu, []
    except Exception as exc:
        detail = _log_provider_error("nvidia-smi", "query", exc)
        return _empty_gpu("nvidia-smi unavailable", detail), ["nvidia-smi: " + detail]


def gpu_snapshot() -> dict:
    nvml, errors = _nvml_snapshot()
    # nvidia-smi is queried whenever NVML is incomplete so unsupported or
    # transient NVML fields do not erase metrics available through the driver.
    if not nvml["available"] or any(nvml.get(key) is None for key in
            ("utilization_percent", "memory_used_bytes", "memory_total_bytes", "temperature_c", "power_watts")):
        smi, smi_errors = _nvidia_smi_snapshot()
        errors.extend(smi_errors)
        if smi["available"]:
            merged = dict(nvml)
            for key in ("name", "utilization_percent", "memory_used_bytes", "memory_total_bytes",
                        "memory_percent", "temperature_c", "power_watts"):
                if merged.get(key) is None:
                    merged[key] = smi.get(key)
            merged["available"] = bool(merged.get("name") or merged.get("utilization_percent") is not None
                                        or merged.get("memory_used_bytes") is not None)
            merged["source"] = "NVML + nvidia-smi" if nvml["available"] else "nvidia-smi fallback"
            merged["provider_errors"] = errors
            merged["unavailable_reason"] = "; ".join(errors) if errors else None
            return merged
        if not nvml["available"]:
            return _empty_gpu("providers unavailable", "; ".join(errors) or
                              nvml.get("unavailable_reason") or smi.get("unavailable_reason"), errors)
    nvml["provider_errors"] = errors
    nvml["unavailable_reason"] = "; ".join(errors) if errors else None
    return nvml


def system_snapshot() -> dict:
    vm = psutil.virtual_memory()
    return {"cpu_percent": float(psutil.cpu_percent(interval=None)),
            "ram_used_bytes": int(vm.used), "ram_total_bytes": int(vm.total),
            "ram_percent": float(vm.percent), "process_rss_bytes": int(psutil.Process(os.getpid()).memory_info().rss),
            "timestamp": time.time()}


def device_snapshot() -> dict:
    has_torch = importlib.util.find_spec("torch") is not None
    cuda_available = False
    cuda_reason = None
    torch_version = None
    torch_cuda_version = None
    cuda_device_name = None
    if has_torch:
        try:
            import torch
            torch_version = torch.__version__
            torch_cuda_version = torch.version.cuda
            cuda_available = bool(torch.cuda.is_available())
            if cuda_available:
                try:
                    cuda_device_name = torch.cuda.get_device_name(0)
                except Exception as exc:
                    cuda_reason = _log_provider_error("PyTorch CUDA", "device name", exc)
            else:
                cuda_reason = "torch.cuda.is_available() returned false"
        except Exception as exc:
            cuda_reason = _log_provider_error("PyTorch", "CUDA availability", exc)
    else:
        cuda_reason = "PyTorch is not installed in the backend Python environment"
    return {"cuda_available": cuda_available, "cuda_unavailable_reason": cuda_reason,
            "cuda_device_name": cuda_device_name, "torch_version": torch_version,
            "torch_cuda_version": torch_cuda_version, "python_executable": sys.executable,
            "gpu": gpu_snapshot(), "system": system_snapshot()}
