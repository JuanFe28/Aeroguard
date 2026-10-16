"""
AeroGuard — AI Vision Service (RF-021)
Análisis de imágenes para detección de posibles drones.
Utiliza OpenCV + YOLOv8 (modelo preentrenado).

Clasificación limitada a: posible dron / no posible dron
NO clasifica por marca, modelo o fabricante.
"""

import asyncio
import base64
import io
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("AeroGuard-AI")

# Configuration
MIN_CONFIDENCE      = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.70"))
MODEL_PATH          = os.getenv("AI_MODEL_PATH", "models/yolov8n.pt")
USE_YOLO            = os.getenv("AI_USE_YOLO", "false").lower() == "true"

# COCO class IDs that could indicate a drone-like object
# Class 0=person, 4=airplane, 5=bus, 6=car, 7=train, 8=truck
# In a real system, a custom-trained YOLO model for drones would be used.
DRONE_LIKE_CLASSES = {4, 39, 40}  # airplane, bottle (placeholder), wine glass (placeholder)


# ============================================================
# Analysis Result
# ============================================================

@dataclass
class AnalysisResult:
    is_drone:        bool
    confidence:      float
    model_used:      str
    processing_ms:   float
    bounding_box:    Optional[dict] = None
    raw_detections:  int = 0


# ============================================================
# OpenCV Heuristic Detector (fallback / demo)
# ============================================================

class HeuristicDetector:
    """
    Simple heuristic drone detector using OpenCV image processing.
    Used when a trained YOLO model is not available.
    
    Detects:
    1. Small, high-contrast moving objects
    2. Objects with aspect ratios consistent with drones
    3. Objects in the upper half of the frame (sky region)
    """

    def analyze(self, image: np.ndarray) -> AnalysisResult:
        start = time.perf_counter()

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Detect edges
        edges = cv2.Canny(blurred, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        h, w = image.shape[:2]
        drone_candidates = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 50 or area > 5000:
                continue

            x, y, cw, ch = cv2.boundingRect(cnt)
            aspect_ratio = cw / ch if ch > 0 else 0
            sky_region = y < h * 0.7  # Upper 70% = sky

            # Drone-like: small, roughly square-ish aspect, in sky
            if 0.3 <= aspect_ratio <= 4.0 and sky_region:
                score = min(1.0, area / 1000) * 0.4
                if 0.7 <= aspect_ratio <= 2.5:
                    score += 0.2  # More drone-like aspect
                if y < h * 0.4:
                    score += 0.1  # High in frame
                drone_candidates.append((score, (x, y, cw, ch)))

        elapsed_ms = (time.perf_counter() - start) * 1000

        if not drone_candidates:
            return AnalysisResult(
                is_drone=False, confidence=0.05,
                model_used="OpenCV-Heuristic", processing_ms=elapsed_ms,
                raw_detections=0,
            )

        best_score, best_box = max(drone_candidates, key=lambda x: x[0])
        confidence = min(0.95, best_score + 0.3)  # Scale to realistic range

        return AnalysisResult(
            is_drone=confidence >= MIN_CONFIDENCE,
            confidence=confidence,
            model_used="OpenCV-Heuristic",
            processing_ms=elapsed_ms,
            bounding_box={"x": best_box[0], "y": best_box[1], "w": best_box[2], "h": best_box[3]},
            raw_detections=len(drone_candidates),
        )


# ============================================================
# YOLO Detector (requires ultralytics package + model file)
# ============================================================

class YOLODetector:
    def __init__(self, model_path: str):
        self._model = None
        self._model_path = model_path
        self._loaded = False

    def load(self) -> bool:
        try:
            from ultralytics import YOLO
            self._model = YOLO(self._model_path)
            self._loaded = True
            logger.info(f"YOLO model loaded: {self._model_path}")
            return True
        except Exception as e:
            logger.warning(f"Could not load YOLO model: {e}. Using heuristic fallback.")
            return False

    def analyze(self, image: np.ndarray) -> AnalysisResult:
        if not self._loaded:
            return AnalysisResult(
                is_drone=False, confidence=0.0,
                model_used="YOLO-NotLoaded", processing_ms=0.0
            )

        start = time.perf_counter()
        results = self._model(image, verbose=False)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Check for drone-like detections
        best_confidence = 0.0
        best_box = None

        for result in results:
            for box in result.boxes:
                cls_id     = int(box.cls[0])
                confidence = float(box.conf[0])
                if confidence > best_confidence:
                    best_confidence = confidence
                    xyxy = box.xyxy[0].tolist()
                    best_box = {"x": xyxy[0], "y": xyxy[1], "w": xyxy[2]-xyxy[0], "h": xyxy[3]-xyxy[1]}

        # In a real system, use a custom-trained drone detection model.
        # Here we simulate detection based on any high-confidence YOLO detection.
        is_drone = best_confidence >= MIN_CONFIDENCE

        return AnalysisResult(
            is_drone=is_drone,
            confidence=best_confidence,
            model_used=f"YOLOv8:{os.path.basename(self._model_path)}",
            processing_ms=elapsed_ms,
            bounding_box=best_box,
            raw_detections=sum(len(r.boxes) for r in results),
        )


# ============================================================
# Main AI Service
# ============================================================

class DroneDetectionService:
    """
    Unified AI service for drone detection.
    Automatically selects YOLO or heuristic detector based on availability.

    Classification: posible dron / no posible dron (binary).
    Does NOT classify by brand, model, or manufacturer.
    """

    def __init__(self):
        self._yolo     = None
        self._heuristic = HeuristicDetector()
        self._detector  = self._heuristic  # Default to heuristic

        if USE_YOLO:
            self._yolo = YOLODetector(MODEL_PATH)
            if self._yolo.load():
                self._detector = self._yolo

    def analyze_bytes(self, image_bytes: bytes) -> AnalysisResult:
        """Analyze raw image bytes."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            return AnalysisResult(
                is_drone=False, confidence=0.0,
                model_used="Error", processing_ms=0.0
            )
        return self._detector.analyze(image)

    def analyze_base64(self, base64_str: str) -> AnalysisResult:
        """Analyze base64-encoded image."""
        try:
            image_bytes = base64.b64decode(base64_str)
            return self.analyze_bytes(image_bytes)
        except Exception as e:
            logger.error(f"Error decoding base64 image: {e}")
            return AnalysisResult(
                is_drone=False, confidence=0.0,
                model_used="Error", processing_ms=0.0
            )

    def analyze_file(self, file_path: str) -> AnalysisResult:
        """Analyze an image file."""
        image = cv2.imread(file_path)
        if image is None:
            return AnalysisResult(
                is_drone=False, confidence=0.0,
                model_used="Error", processing_ms=0.0
            )
        return self._detector.analyze(image)


# ============================================================
# RabbitMQ Worker (async consumer)
# ============================================================

async def process_ai_queue():
    """
    Consume image analysis requests from RabbitMQ queue.
    Used for asynchronous processing (RF-021).
    """
    try:
        import aio_pika

        RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://aeroguard:aeroguard_pass@localhost:5672/")
        QUEUE_NAME   = os.getenv("QUEUE_AI_PROCESSING", "ai.processing")

        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel    = await connection.channel()
        queue      = await channel.declare_queue(QUEUE_NAME, durable=True)

        service = DroneDetectionService()
        logger.info(f"AI Worker listening on queue: {QUEUE_NAME}")

        async for message in queue:
            async with message.process():
                try:
                    payload     = json.loads(message.body.decode())
                    image_b64   = payload.get("image_base64", "")
                    detection_id = payload.get("detection_id", "")

                    result = service.analyze_base64(image_b64)

                    logger.info(
                        f"AI Analysis complete | detection={detection_id} | "
                        f"is_drone={result.is_drone} | confidence={result.confidence:.2f} | "
                        f"model={result.model_used} | time={result.processing_ms:.1f}ms"
                    )

                    # TODO: Update detection record in database
                    # await update_detection_ai_result(detection_id, result)

                except Exception as e:
                    logger.error(f"Error processing AI message: {e}")

    except Exception as e:
        logger.error(f"RabbitMQ connection error: {e}")
        await asyncio.sleep(5)
        await process_ai_queue()  # Reconnect


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(process_ai_queue())
