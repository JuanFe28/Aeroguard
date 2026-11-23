"""
AeroGuard — Servicio RAG Vectorial con Qdrant Embebido y Embeddings Livianos

Diseñado para Oracle Cloud (<= 4 GiB RAM / 2 vCPU, compatible x86_64 y ARM64):
- Vectorización determinista liviana (512 dims en NumPy, sin PyTorch ni sentence-transformers).
- Soporte opcional de embeddings remotos vía EMBEDDING_API_URL.
- Qdrant en modo local embebido por defecto (0 contenedores extra) o remoto vía QDRANT_URL.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import httpx
import numpy as np
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

try:
    from qdrant_client import QdrantClient, models as qdrant_models

    HAS_QDRANT = True
except ImportError:  # pragma: no cover - fallback solo si falta wheel opcional
    QdrantClient = None
    qdrant_models = None
    HAS_QDRANT = False

EMBEDDING_DIM = 512
DEFAULT_CORPUS_DIR = Path(__file__).resolve().parents[3] / "docs" / "conocimiento_cuas"

_STOPWORDS = frozenset({
    "a", "al", "con", "de", "del", "el", "en", "es", "la", "las",
    "lo", "los", "o", "para", "por", "que", "se", "su", "un", "una", "y",
})

_SYNONYMS: dict[str, tuple[str, ...]] = {
    "dron": ("uav", "aeronave", "cuadricoptero", "quadcopter"),
    "uav": ("dron", "aeronave"),
    "geocerca": ("zona", "poligono", "perimetro", "exclusion"),
    "zona": ("geocerca", "perimetro", "area"),
    "altitud": ("cota", "techo", "altura", "120m", "agl"),
    "cota": ("altitud", "techo", "altura", "120m", "agl"),
    "120": ("120m", "cota", "altitud", "agl"),
    "120m": ("120", "cota", "altitud", "agl"),
    "ave": ("pajaro", "bird", "falso", "positivo"),
    "jamming": ("inhibicion", "interferencia", "spoofing", "derribo", "rf", "cinetica"),
    "defensivo": ("pasivo", "protocolo", "cuas", "bloqueo"),
    "protocolo": ("defensivo", "procedimiento", "pasivo", "cuas"),
    "arima": ("pronostico", "serie", "pico", "tendencia"),
    "random": ("forest", "clasificador", "amenaza", "riesgo"),
    "kmeans": ("cluster", "perfil", "vuelo", "agrupamiento"),
    "rbac": ("permiso", "rol", "admin", "operator", "analyst"),
    "oracle": ("arm64", "x86_64", "memoria", "ram", "compose"),
}


def _normalize_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _content_tokens(text: str) -> list[str]:
    norm_txt = _normalize_text(text)
    raw = re.findall(r"[a-z0-9_]+", norm_txt)
    return [tok for tok in raw if len(tok) >= 2 and tok not in _STOPWORDS]


class LightweightEmbedder:
    """Generador de embeddings liviano (feature hashing + n-gramas + sinónimos C-UAS)."""

    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        if settings.EMBEDDING_API_URL:
            remote = self._try_remote_embedding(text)
            if remote is not None:
                return remote
        return self._local_embed(text)

    def _try_remote_embedding(self, text: str) -> list[float] | None:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if settings.EMBEDDING_API_KEY:
            headers["Authorization"] = f"Bearer {settings.EMBEDDING_API_KEY}"
        body: dict[str, Any] = {"input": text}
        if settings.EMBEDDING_MODEL:
            body["model"] = settings.EMBEDDING_MODEL
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(settings.EMBEDDING_API_URL, json=body, headers=headers)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    if data and isinstance(data[0].get("embedding"), list):
                        vec = np.asarray(data[0]["embedding"], dtype=np.float32)
                        norm = float(np.linalg.norm(vec))
                        if norm > 0.0 and len(vec) == self.dim:
                            return (vec / norm).tolist()
        except Exception as exc:
            logger.debug("Fallback a embedding local liviano", error=str(exc))
        return None

    def _local_embed(self, text: str) -> list[float]:
        tokens = _content_tokens(text)
        unique_tokens = list(dict.fromkeys(tokens))
        expanded: list[tuple[str, float]] = []
        for tok in unique_tokens:
            tf_boost = 1.0 + min(tokens.count(tok), 3) * 0.25
            expanded.append((f"w:{tok}", 2.6 * tf_boost))
            if len(tok) >= 5:
                for i in range(len(tok) - 2):
                    expanded.append((f"c:{tok[i:i + 3]}", 0.15))
            for syn in _SYNONYMS.get(tok, ()):
                expanded.append((f"s:{syn}", 0.9))
        seen_bigrams: set[str] = set()
        for i in range(len(tokens) - 1):
            bg = f"{tokens[i]}_{tokens[i + 1]}"
            if bg not in seen_bigrams:
                seen_bigrams.add(bg)
                expanded.append((f"b:{bg}", 1.25))

        vec = np.zeros(self.dim, dtype=np.float32)
        for feat, weight in expanded:
            digest = hashlib.sha256(feat.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if (digest[4] & 1) == 0 else -1.0
            vec[idx] += sign * weight

        norm = float(np.linalg.norm(vec))
        if norm > 0.0:
            vec /= norm
        else:
            vec[0] = 1.0
        return vec.tolist()


def _chunk_markdown(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)
    chunks: list[dict[str, str]] = []
    doc_title = path.stem.replace("_", " ")
    for block in sections:
        clean = block.strip()
        if not clean:
            continue
        lines = clean.splitlines()
        heading = lines[0].lstrip("# ").strip() if lines else doc_title
        body = clean[:1200]
        chunks.append(
            {
                "doc_id": f"{path.name}#{heading[:40]}",
                "source": path.name,
                "section": heading[:120],
                "content": body,
            }
        )
    return chunks


class AgentRagService:
    """Repositorio vectorial RAG respaldado por Qdrant (embebido local o remoto)."""

    def __init__(self):
        self.embedder = LightweightEmbedder()
        self._client: Any = None
        self._vector_backend: str = "uninitialized"
        self._memory_fallback: list[dict[str, Any]] = []
        self._last_indexed_at: str | None = None
        self._indexed_chunks: int = 0
        self._active_path: str | None = None

    def _corpus_dir(self) -> Path:
        if settings.RAG_CORPUS_DIR:
            return Path(settings.RAG_CORPUS_DIR)
        return DEFAULT_CORPUS_DIR

    def reset_client(self, path: str | None = None) -> None:
        """Reinicia la instancia Qdrant (útil en tests aislados con ':memory:')."""
        if self._client is not None and hasattr(self._client, "close"):
            try:
                self._client.close()
            except Exception as exc:
                logger.debug("Cierre previo de Qdrant omitido", error=str(exc))
        self._client = None
        self._indexed_chunks = 0
        self._memory_fallback = []
        self._active_path = path

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        if not HAS_QDRANT:
            self._vector_backend = "numpy_fallback"
            return None

        target_path = self._active_path or settings.QDRANT_PATH
        try:
            if settings.QDRANT_URL:
                self._client = QdrantClient(url=settings.QDRANT_URL, timeout=5.0)
                self._vector_backend = "qdrant_remote"
            elif target_path == ":memory:":
                self._client = QdrantClient(":memory:")
                self._vector_backend = "qdrant_embedded"
            else:
                qpath = Path(target_path)
                qpath.mkdir(parents=True, exist_ok=True)
                self._client = QdrantClient(path=str(qpath))
                self._vector_backend = "qdrant_embedded"
        except Exception as exc:
            logger.warning("Qdrant embebido en disco ocupado; usando memoria local", error=str(exc))
            self._client = QdrantClient(":memory:")
            self._vector_backend = "qdrant_embedded"

        self._ensure_collection()
        return self._client

    def _ensure_collection(self) -> None:
        if self._client is None or qdrant_models is None:
            return
        col = settings.QDRANT_COLLECTION
        if self._client.collection_exists(col):
            try:
                info = self._client.get_collection(col)
                existing_size = getattr(getattr(getattr(info, "config", None), "params", None), "vectors", None)
                size_val = getattr(existing_size, "size", EMBEDDING_DIM)
                if size_val != EMBEDDING_DIM:
                    self._client.delete_collection(col)
            except Exception as exc:
                logger.debug("No se pudo inspeccionar colección Qdrant existente", error=str(exc))
        if not self._client.collection_exists(col):
            self._client.create_collection(
                collection_name=col,
                vectors_config=qdrant_models.VectorParams(
                    size=EMBEDDING_DIM,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )

    def reindex_corpus(self, corpus_dir: Path | None = None) -> dict[str, Any]:
        target_dir = corpus_dir or self._corpus_dir()
        if not target_dir.exists():
            return {
                "indexed_chunks": 0,
                "vector_backend": self._vector_backend,
                "corpus_dir": str(target_dir),
                "warning": "Directorio de corpus RAG no encontrado.",
            }

        chunks: list[dict[str, str]] = []
        for md_file in sorted(target_dir.glob("*.md")):
            chunks.extend(_chunk_markdown(md_file))

        client = self._get_client()
        self._memory_fallback = []

        if client is not None and qdrant_models is not None and chunks:
            self._ensure_collection()
            points = []
            for ch in chunks:
                vec = self.embedder.embed(f"{ch['section']}\n{ch['section']}\n{ch['content']}")
                pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"aeroguard:{ch['doc_id']}"))
                points.append(
                    qdrant_models.PointStruct(
                        id=pid,
                        vector=vec,
                        payload=ch,
                    )
                )
            client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points, wait=True)
        else:
            for ch in chunks:
                vec = self.embedder.embed(f"{ch['section']}\n{ch['section']}\n{ch['content']}")
                self._memory_fallback.append({"vector": np.asarray(vec, dtype=np.float32), "payload": ch})

        self._indexed_chunks = len(chunks)
        self._last_indexed_at = datetime.now(timezone.utc).isoformat()
        return {
            "indexed_chunks": self._indexed_chunks,
            "vector_backend": self._vector_backend,
            "collection": settings.QDRANT_COLLECTION,
            "last_indexed_at": self._last_indexed_at,
        }

    @staticmethod
    def _hybrid_rerank_score(query_tokens: set[str], vec_score: float, payload: Mapping[str, Any]) -> float:
        if not query_tokens:
            return round(float(vec_score), 4)
        section_tokens = set(_content_tokens(str(payload.get("section", ""))))
        body_tokens = set(_content_tokens(str(payload.get("content", ""))))
        all_doc_tokens = section_tokens | body_tokens
        exact_hits = len(query_tokens & all_doc_tokens)
        section_hits = len(query_tokens & section_tokens)
        lex_ratio = (exact_hits + 0.5 * section_hits) / float(len(query_tokens) * 1.5)
        lex_ratio = min(1.0, max(0.0, lex_ratio))
        return round(0.65 * float(vec_score) + 0.35 * lex_ratio, 4)

    def search(self, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        if self._indexed_chunks == 0:
            self.reindex_corpus()

        limit = max(1, min(top_k, 10))
        candidate_limit = max(12, limit * 3)
        q_vec = self.embedder.embed(query)
        q_tokens = set(_content_tokens(query))
        client = self._get_client()
        candidates: list[tuple[float, Mapping[str, Any]]] = []

        if client is not None:
            response = client.query_points(
                collection_name=settings.QDRANT_COLLECTION,
                query=q_vec,
                limit=candidate_limit,
            )
            for pt in getattr(response, "points", []) or []:
                payload = pt.payload or {}
                raw_score = float(getattr(pt, "score", 0.0))
                candidates.append((self._hybrid_rerank_score(q_tokens, raw_score, payload), payload))
        else:
            q_arr = np.asarray(q_vec, dtype=np.float32)
            for entry in self._memory_fallback:
                raw_score = float(np.dot(q_arr, entry["vector"]))
                candidates.append((self._hybrid_rerank_score(q_tokens, raw_score, entry["payload"]), entry["payload"]))

        candidates.sort(key=lambda item: item[0], reverse=True)
        results: list[dict[str, Any]] = []
        for score, payload in candidates[:limit]:
            content = str(payload.get("content", ""))
            results.append(
                {
                    "doc_id": str(payload.get("doc_id", "")),
                    "source": str(payload.get("source", "")),
                    "section": str(payload.get("section", "")),
                    "snippet": content[:320].replace("\n", " ").strip(),
                    "score": score,
                }
            )
        return results

    def status(self) -> dict[str, Any]:
        self._get_client()
        return {
            "vector_backend": self._vector_backend,
            "collection": settings.QDRANT_COLLECTION,
            "indexed_chunks": self._indexed_chunks,
            "last_indexed_at": self._last_indexed_at,
            "embedding_dim": EMBEDDING_DIM,
        }


agent_rag_service = AgentRagService()
