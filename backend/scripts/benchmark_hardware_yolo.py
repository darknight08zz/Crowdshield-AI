"""
CROWDSHIELD HARDWARE ACCELERATION BENCHMARK FOR YOLOV8
======================================================
Performs honest hardware inspection and critical-path benchmarking for YOLOv8
person detection on standard operational live video resolution (1280x720).

Measures:
1. PyTorch CPU Native inference latency & throughput.
2. CUDA GPU availability & inference latency (if CUDA hardware present).
3. ONNX / OpenVINO CPU export inference latency & throughput (if exporters present).
"""

import sys
import os
import time
import json
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("crowdshield.benchmark.hardware")

# Ensure backend root in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def benchmark_hardware():
    logger.info("=================================================================")
    logger.info("STARTING CROWDSHIELD YOLOV8 HARDWARE ACCELERATION BENCHMARK")
    logger.info("=================================================================")

    # 1. Hardware Inspection
    import torch
    cuda_available = torch.cuda.is_available()
    device_count = torch.cuda.device_count() if cuda_available else 0
    gpu_name = torch.cuda.get_device_name(0) if cuda_available else "N/A (No NVIDIA CUDA GPU Detected)"

    logger.info(f"Hardware Inspection:")
    logger.info(f"  PyTorch Version : {torch.__version__}")
    logger.info(f"  CUDA Available  : {cuda_available}")
    logger.info(f"  GPU Count       : {device_count}")
    logger.info(f"  GPU Device Name : {gpu_name}")

    # Standard operational frame: 1280x720 BGR numpy array
    dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    results = {
        "hardware": {
            "pytorch_version": torch.__version__,
            "cuda_available": cuda_available,
            "gpu_count": device_count,
            "gpu_name": gpu_name,
            "operational_resolution": "1280x720"
        },
        "benchmarks": {}
    }

    # 2. PyTorch CPU Benchmark
    try:
        from ultralytics import YOLO
        model_cpu = YOLO("yolov8n.pt")

        logger.info("Running PyTorch CPU Warmup (20 iterations)...")
        for _ in range(20):
            model_cpu.predict(dummy_frame, imgsz=640, classes=[0], verbose=False)

        logger.info("Running PyTorch CPU Benchmark (100 iterations)...")
        cpu_latencies = []
        for _ in range(100):
            t0 = time.perf_counter()
            model_cpu.predict(dummy_frame, imgsz=640, classes=[0], verbose=False)
            t1 = time.perf_counter()
            cpu_latencies.append((t1 - t0) * 1000.0)

        cpu_mean = float(np.mean(cpu_latencies))
        cpu_p95 = float(np.percentile(cpu_latencies, 95))
        cpu_fps = float(1000.0 / cpu_mean)

        logger.info(f"PyTorch CPU Results:")
        logger.info(f"  Mean Latency : {cpu_mean:.2f} ms")
        logger.info(f"  P95 Latency  : {cpu_p95:.2f} ms")
        logger.info(f"  Throughput   : {cpu_fps:.2f} FPS")

        results["benchmarks"]["pytorch_cpu"] = {
            "status": "COMPLETED",
            "mean_latency_ms": round(cpu_mean, 2),
            "p95_latency_ms": round(cpu_p95, 2),
            "throughput_fps": round(cpu_fps, 2)
        }
    except Exception as e:
        logger.error(f"PyTorch CPU benchmark failed: {e}")
        results["benchmarks"]["pytorch_cpu"] = {"status": "FAILED", "error": str(e)}

    # 3. PyTorch GPU (CUDA) Benchmark if available
    if cuda_available:
        try:
            model_gpu = YOLO("yolov8n.pt").to("cuda")
            logger.info("Running PyTorch GPU Warmup (20 iterations)...")
            for _ in range(20):
                model_gpu.predict(dummy_frame, imgsz=640, classes=[0], verbose=False, device="cuda")

            logger.info("Running PyTorch GPU Benchmark (100 iterations)...")
            gpu_latencies = []
            for _ in range(100):
                t0 = time.perf_counter()
                model_gpu.predict(dummy_frame, imgsz=640, classes=[0], verbose=False, device="cuda")
                torch.cuda.synchronize()
                t1 = time.perf_counter()
                gpu_latencies.append((t1 - t0) * 1000.0)

            gpu_mean = float(np.mean(gpu_latencies))
            gpu_p95 = float(np.percentile(gpu_latencies, 95))
            gpu_fps = float(1000.0 / gpu_mean)

            logger.info(f"PyTorch GPU Results:")
            logger.info(f"  Mean Latency : {gpu_mean:.2f} ms")
            logger.info(f"  P95 Latency  : {gpu_p95:.2f} ms")
            logger.info(f"  Throughput   : {gpu_fps:.2f} FPS")

            results["benchmarks"]["pytorch_gpu_cuda"] = {
                "status": "COMPLETED",
                "mean_latency_ms": round(gpu_mean, 2),
                "p95_latency_ms": round(gpu_p95, 2),
                "throughput_fps": round(gpu_fps, 2)
            }
        except Exception as e:
            logger.error(f"PyTorch GPU benchmark failed: {e}")
            results["benchmarks"]["pytorch_gpu_cuda"] = {"status": "FAILED", "error": str(e)}
    else:
        logger.info("CUDA GPU not available. GPU benchmark skipped (reported as NOT_AVAILABLE).")
        results["benchmarks"]["pytorch_gpu_cuda"] = {
            "status": "NOT_AVAILABLE",
            "reason": "No CUDA hardware present on host machine."
        }

    # 4. OpenVINO / ONNX CPU Export Benchmark if available
    try:
        from ultralytics import YOLO
        logger.info("Attempting OpenVINO export for optimized CPU inference...")
        model_ov = YOLO("yolov8n.pt")
        ov_path = model_ov.export(format="openvino", imgsz=640, verbose=False)
        model_ov_engine = YOLO(ov_path)

        logger.info("Running OpenVINO CPU Warmup (20 iterations)...")
        for _ in range(20):
            model_ov_engine.predict(dummy_frame, imgsz=640, classes=[0], verbose=False)

        logger.info("Running OpenVINO CPU Benchmark (100 iterations)...")
        ov_latencies = []
        for _ in range(100):
            t0 = time.perf_counter()
            model_ov_engine.predict(dummy_frame, imgsz=640, classes=[0], verbose=False)
            t1 = time.perf_counter()
            ov_latencies.append((t1 - t0) * 1000.0)

        ov_mean = float(np.mean(ov_latencies))
        ov_p95 = float(np.percentile(ov_latencies, 95))
        ov_fps = float(1000.0 / ov_mean)

        logger.info(f"OpenVINO CPU Results:")
        logger.info(f"  Mean Latency : {ov_mean:.2f} ms")
        logger.info(f"  P95 Latency  : {ov_p95:.2f} ms")
        logger.info(f"  Throughput   : {ov_fps:.2f} FPS")

        results["benchmarks"]["openvino_cpu"] = {
            "status": "COMPLETED",
            "mean_latency_ms": round(ov_mean, 2),
            "p95_latency_ms": round(ov_p95, 2),
            "throughput_fps": round(ov_fps, 2)
        }
    except Exception as e:
        logger.info(f"OpenVINO CPU benchmark omitted ({e}).")
        results["benchmarks"]["openvino_cpu"] = {
            "status": "OMITTED",
            "reason": str(e)
        }

    # Save artifact
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts", "yolov8_hardware_benchmark.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Hardware Benchmark Artifact written to '{output_path}'")
    logger.info("=================================================================")
    return results

if __name__ == "__main__":
    benchmark_hardware()
