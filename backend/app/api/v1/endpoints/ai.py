"""
AeroGuard — AI Endpoint (RF-021)
Integración con motor de visión artificial para clasificación de drones.
Fase 2 - CODE: Integración real con OpenCV + YOLOv8 (HU-01, [CODE-01]).
"""

from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
import structlog

from app.core.security import require_permission
from app.services.ai_vision_service import ai_vision_service, AIVisionService

logger = structlog.get_logger("AeroGuard-AI-Endpoint")

router = APIRouter()


@router.post("/analyze", summary="Analizar imagen con Inteligencia Artificial (RF-021 / CODE-01)")
async def analyze_image(
    file: UploadFile = File(...),
    sensor_id: Optional[str] = Form("CAM-BGA-NORTE-01"),
    zone_id: Optional[int] = Form(None),
    current_user = Depends(require_permission("detections:write")),
):
    """
    Recibe un fotograma (imagen) capturado por un sensor óptico o cámara C-UAS
    y lo procesa utilizando el motor real de visión artificial (OpenCV + YOLOv8).

    - Valida formatos permitidos (JPEG, PNG, WEBP).
    - Detecta objetos aéreos tipo dron, calculando bounding_box, nivel de confianza y tiempo de inferencia.
    - Cumple estrictamente con el contrato JSON estipulado en la Planificación v1.1.
    """
    # 1. Leer contenido binario del archivo
    data = await file.read()

    # 2. Validación de formato y contenido según criterios Gherkin
    try:
        AIVisionService.validate_image_file(
            filename=file.filename or "",
            content_type=file.content_type,
            data_len=len(data),
        )
    except ValueError as ve:
        logger.warning(
            "Petición de análisis rechazada por archivo inválido",
            filename=file.filename,
            content_type=file.content_type,
            reason=str(ve),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )

    # 3. Procesamiento con el motor de visión artificial
    result = ai_vision_service.analyze_image_bytes(
        image_bytes=data,
        sensor_id=sensor_id or "CAM-BGA-NORTE-01",
        zone_id=zone_id,
    )

    logger.info(
        "Inferencia de IA completada",
        sensor_id=result.get("sensor_id"),
        engine=result.get("engine"),
        is_drone=result.get("detection", {}).get("is_drone"),
        confidence=result.get("detection", {}).get("confidence"),
        time_ms=result.get("processing_time_ms"),
    )

    return result
