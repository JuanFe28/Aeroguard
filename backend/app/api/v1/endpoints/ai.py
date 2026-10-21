"""
AeroGuard — AI Endpoint (RF-021)
Integración con motor de visión artificial para clasificación de drones.
Fase 2 - CODE: Integración real con OpenCV + YOLOv8 (HU-01, [CODE-01]).
"""

from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
import structlog

from app.core.security import require_permission
from app.core.config import settings
from app.core.database import get_db
from starlette.concurrency import run_in_threadpool
from app.services.ai_vision_service import ai_vision_service, AIVisionService

logger = structlog.get_logger("AeroGuard-AI-Endpoint")

router = APIRouter()


@router.post("/analyze", summary="Analizar imagen con visión experimental (RF-021 / CODE-01)")
async def analyze_image(
    file: UploadFile = File(...),
    sensor_id: Optional[str] = Form("CAM-BGA-NORTE-01"),
    zone_id: Optional[str] = Form(None),
    db=Depends(get_db),
    current_user = Depends(require_permission("detections:write")),
):
    """
    Procesa una imagen con heurísticas OpenCV/Pillow o con un adaptador YOLO opcional.
    No acredita reconocimiento validado de drones; el score no es precisión calibrada.

    - Valida formatos permitidos (JPEG, PNG, WEBP).
    - Devuelve candidatos, caja envolvente, score y tiempo de procesamiento.
    - Identifica el motor utilizado y declara model_validated=false.
    """
    from app.api.v1.endpoints.config import load_persisted_config
    await load_persisted_config(db)
    if not settings.AI_ENABLED:
        raise HTTPException(409, 'El análisis visual está deshabilitado en la configuración.')
    # 1. Leer contenido binario del archivo
    max_upload_bytes = 10 * 1024 * 1024
    data = await file.read(max_upload_bytes + 1)
    if len(data) > max_upload_bytes:
        raise HTTPException(status_code=413, detail="La imagen supera el límite de 10 MiB.")

    # 2. Validación de formato y contenido según criterios Gherkin
    try:
        AIVisionService.validate_image_file(
            filename=file.filename or "",
            content_type=file.content_type,
            data_len=len(data),
        )
        # Comprobar los bytes, además del nombre y MIME declarados por el cliente.
        import io
        from PIL import Image, UnidentifiedImageError
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"} or image.width * image.height > 25_000_000:
                    raise ValueError("Formato o dimensiones de imagen no permitidos.")
                image.verify()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            raise ValueError("El contenido no es una imagen JPEG, PNG o WEBP válida.") from error
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
    try:
        result = await run_in_threadpool(ai_vision_service.analyze_image_bytes,
            image_bytes=data,
            sensor_id=sensor_id or "CAM-BGA-NORTE-01",
            zone_id=zone_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    logger.info(
        "Inferencia de IA completada",
        sensor_id=result.get("sensor_id"),
        engine=result.get("engine"),
        is_drone=result.get("detection", {}).get("is_drone"),
        confidence=result.get("detection", {}).get("confidence"),
        time_ms=result.get("processing_time_ms"),
    )

    return result
