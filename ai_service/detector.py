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

# Solo nombres explícitos de un modelo entrenado para drones. COCO no basta.
DRONE_CLASS_NAMES = {"drone", "uav", "quadcopter", "quadcopter_uav"}


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
                names = result.names
                class_name = names.get(cls_id, "") if isinstance(names, dict) else names[cls_id]
                if str(class_name).strip().casefold() not in DRONE_CLASS_NAMES:
                    continue
                confidence = float(box.conf[0])
                if confidence > best_confidence:
                    best_confidence = confidence
                    xyxy = box.xyxy[0].tolist()
                    best_box = {"x": xyxy[0], "y": xyxy[1], "w": xyxy[2]-xyxy[0], "h": xyxy[3]-xyxy[1]}

        # La presencia de una clase válida no constituye validación del modelo.
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
    import aio_pika
    import httpx
    import hashlib
    from uuid import UUID
    token = os.getenv('AI_WORKER_TOKEN', '')
    if not token:
        raise RuntimeError('AI_WORKER_TOKEN es obligatorio; crea una sesión de operador dedicada.')
    service = DroneDetectionService()
    queue_name = os.getenv('QUEUE_AI_PROCESSING', 'ai.processing')
    backend = os.getenv('BACKEND_URL', 'http://backend:8000/api/v1').rstrip('/')
    while True:
        connection = None
        try:
            connection = await aio_pika.connect_robust(os.environ['RABBITMQ_URL'])
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)
            await channel.declare_queue(queue_name + '.dead', durable=True)
            queue = await channel.declare_queue(queue_name, durable=True, arguments={
                'x-dead-letter-exchange': '', 'x-dead-letter-routing-key': queue_name + '.dead'})
            async with httpx.AsyncClient(timeout=30, headers={'Authorization': 'Bearer ' + token}) as client:
                async with queue.iterator() as messages:
                    async for message in messages:
                        try:
                            if len(message.body) > 14 * 1024 * 1024:
                                raise ValueError('Mensaje demasiado grande')
                            payload = json.loads(message.body)
                            detection_id = str(UUID(payload['detection_id']))
                            raw = base64.b64decode(payload['image_base64'], validate=True)
                            import io
                            from PIL import Image
                            with Image.open(io.BytesIO(raw)) as image:
                                if image.format not in {'JPEG','PNG','WEBP'} or image.width * image.height > 25_000_000:
                                    raise ValueError('Formato o dimensiones no permitidas')
                                image.verify()
                            result = service.analyze_bytes(raw)
                            if result.model_used == 'Error':
                                raise ValueError('No se pudo analizar la imagen')
                            body = {'job_id': hashlib.sha256(message.body).hexdigest(), 'is_drone': result.is_drone,
                                    'confidence': result.confidence, 'model_used': result.model_used, 'processing_ms': result.processing_ms}
                            response = await client.post(f'{backend}/detections/{detection_id}/ai-analysis', json=body)
                            if response.status_code >= 500:
                                raise httpx.ConnectError('Backend no disponible')
                            response.raise_for_status()
                            await message.ack()
                            logger.info('Resultado experimental persistido para detección %s', detection_id)
                        except (httpx.ConnectError, httpx.TimeoutException):
                            await asyncio.sleep(2)
                            await message.reject(requeue=True)
                        except Exception:
                            logger.exception('Trabajo rechazado; conservado en cola dead-letter')
                            await message.reject(requeue=False)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Worker desconectado; reintento en cinco segundos')
            await asyncio.sleep(5)
        finally:
            if connection:
                await connection.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(process_ai_queue())
