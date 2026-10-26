"""Adaptador HTTP independiente para el detector y su comprobación de salud."""

from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import io
import json
import os

from PIL import Image
from ai_service.detector import DroneDetectionService

MAX_BYTES = 10 * 1024 * 1024
detector = DroneDetectionService()


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path != "/health":
            self.send_json(404, {"detail": "Ruta no encontrada"})
            return
        self.send_json(200, {"status": "healthy", "service": "aeroguard-ai-service", "version": "1.2.0-rc.1", "endpoint": "POST /analyze", "model_validated": False})

    def do_POST(self):
        if self.path != "/analyze":
            self.send_json(404, {"detail": "Ruta no encontrada"})
            return
        token = os.getenv("AI_SERVICE_TOKEN", "")
        if not token:
            self.send_json(503, {"detail": "Configurar AI_SERVICE_TOKEN"})
            return
        authorization = self.headers.get("Authorization", "")
        if not hmac.compare_digest(authorization.encode(), ("Bearer " + token).encode()):
            self.send_json(401, {"detail": "Token de servicio requerido"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BYTES:
                self.send_json(413, {"detail": "La imagen debe contener entre 1 byte y 10 MiB"})
                return
            raw = self.rfile.read(length)
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"} or image.width * image.height > 25_000_000:
                    raise ValueError("Formato o dimensiones no permitidas")
                image.verify()
            result = detector.analyze_bytes(raw)
            if result.model_used == "Error":
                raise ValueError("Imagen no analizable")
            self.send_json(200, {"service": "aeroguard-ai-service", "result": asdict(result), "model_validated": False})
        except (ValueError, OSError):
            self.send_json(400, {"detail": "Imagen inválida"})


if __name__ == "__main__":
    host = os.getenv("AI_HTTP_HOST", "127.0.0.1")
    port = int(os.getenv("AI_HTTP_PORT", "8001"))
    ThreadingHTTPServer((host, port), Handler).serve_forever()
