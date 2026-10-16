"""
AeroGuard — Database Configuration & Session Management
Resiliente: Conexión asíncrona a PostgreSQL con fallback automático a SQLite (aiosqlite).
"""

from typing import AsyncGenerator
import structlog
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.models.models import Base

logger = structlog.get_logger(__name__)

# Configuración inicial del Engine
_engine_url = settings.DATABASE_URL
_engine_kwargs = {"echo": False, "future": True}

if "postgresql" in _engine_url:
    _engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    _engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW

engine = create_async_engine(_engine_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para inyectar la sesión asíncrona de base de datos en endpoints FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def _seed_data(session: AsyncSession):
    """Siembra datos iniciales (usuarios y zonas) si la base de datos está vacía."""
    from app.models.models import User, RestrictedZone, UserRole, ThreatLevel
    from app.core.security import hash_password

    try:
        # Seed Users
        user_res = await session.execute(select(User))
        if not user_res.scalars().first():
            users = [
                User(
                    username="admin",
                    email="admin@aeroguard.co",
                    first_name="Admin",
                    last_name="AeroGuard",
                    password_hash=hash_password("Admin@12345"),
                    role=UserRole.ADMIN,
                    is_active=True,
                ),
                User(
                    username="operador",
                    email="operador@aeroguard.co",
                    first_name="Carlos",
                    last_name="Operador",
                    password_hash=hash_password("Operator@12345"),
                    role=UserRole.OPERATOR,
                    is_active=True,
                ),
                User(
                    username="analista",
                    email="analista@aeroguard.co",
                    first_name="Laura",
                    last_name="Analista",
                    password_hash=hash_password("Analyst@12345"),
                    role=UserRole.ANALYST,
                    is_active=True,
                ),
            ]
            session.add_all(users)
            await session.commit()
            logger.info("Usuarios iniciales creados en la base de datos")

        # Seed Zones
        zone_res = await session.execute(select(RestrictedZone))
        if not zone_res.scalars().first():
            zones = [
                RestrictedZone(
                    name="Aeropuerto Palonegro (Área Crítica)",
                    description="Zona de aproximación y pista de aterrizaje principal.",
                    threat_level=ThreatLevel.CRITICAL,
                    color="#ef4444",
                    max_altitude=1200.0,
                    min_altitude=0.0,
                    coordinates=[[7.1265, -73.1848], [7.1350, -73.1720], [7.1210, -73.1650], [7.1140, -73.1780]],
                    is_active=True,
                ),
                RestrictedZone(
                    name="Complejo Gubernamental Santander",
                    description="Edificios administrativos centrales y centro de mando.",
                    threat_level=ThreatLevel.HIGH,
                    color="#f59e0b",
                    max_altitude=300.0,
                    min_altitude=0.0,
                    coordinates=[[7.1190, -73.1250], [7.1240, -73.1200], [7.1210, -73.1140], [7.1150, -73.1190]],
                    is_active=True,
                ),
                RestrictedZone(
                    name="Aeropuerto El Dorado",
                    description="Zona de exclusión aeroportuaria principal y corredores de aproximación.",
                    threat_level=ThreatLevel.CRITICAL,
                    color="#ef4444",
                    max_altitude=1200.0,
                    min_altitude=0.0,
                    coordinates=[[4.700, -74.145], [4.720, -74.145], [4.720, -74.110], [4.700, -74.110]],
                    is_active=True,
                ),
                RestrictedZone(
                    name="Centro de Operaciones Bogotá",
                    description="Zona de exclusión operativa, gubernamental y centro de control.",
                    threat_level=ThreatLevel.HIGH,
                    color="#f59e0b",
                    max_altitude=500.0,
                    min_altitude=0.0,
                    coordinates=[[4.705, -74.080], [4.715, -74.080], [4.715, -74.065], [4.705, -74.065]],
                    is_active=True,
                ),
                RestrictedZone(
                    name="Zona Residencial Norte Bogotá",
                    description="Zona de vuelo restringido sobre áreas urbanas densas y sedes diplomáticas.",
                    threat_level=ThreatLevel.MEDIUM,
                    color="#3b82f6",
                    max_altitude=200.0,
                    min_altitude=0.0,
                    coordinates=[[4.730, -74.075], [4.745, -74.075], [4.745, -74.060], [4.730, -74.060]],
                    is_active=True,
                ),
            ]
            session.add_all(zones)
            await session.commit()
            logger.info("Zonas iniciales creadas en la base de datos")
    except Exception as e:
        logger.error("Error al sembrar datos iniciales", error=str(e))
        await session.rollback()


async def init_db():
    """Inicializa tablas y datos semilla, aplicando fallback a SQLite si PostgreSQL no está disponible."""
    global engine, AsyncSessionLocal

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Base de datos conectada exitosamente", url=str(engine.url))
    except Exception as e:
        logger.warning(
            "No se pudo conectar a PostgreSQL. Activando fallback a SQLite local...",
            error=str(e),
        )
        sqlite_url = "sqlite+aiosqlite:///./aeroguard.db"
        engine = create_async_engine(sqlite_url, echo=False, future=True)
        AsyncSessionLocal.configure(bind=engine)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Base de datos SQLite local inicializada exitosamente", url=sqlite_url)

    async with AsyncSessionLocal() as session:
        await _seed_data(session)
