"""
AeroGuard — Sensor Simulator
Genera datos de telemetría simulados que imitan sensores reales.
Envía los datos al backend via RabbitMQ o HTTP.

Datos generados por sensor:
  - Latitud, Longitud, Altitud, Velocidad, Dirección, Timestamp

Ejecutar: python simulator.py
"""

import asyncio
import json
import math
import random
import time
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("AeroGuard-Simulator")

# ============================================================
# Configuration
# ============================================================

BACKEND_URL   = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")
SENSOR_TOKEN  = os.getenv("SIMULATOR_TOKEN", "")
INTERVAL_SEC  = float(os.getenv("INTERVAL_SEC", "3.0"))  # Telemetry send interval

# Bogotá center (origin for simulation)
CENTER_LAT = 4.7110
CENTER_LNG = -74.0721

# Validation ranges (RF-029: discard invalid data)
LAT_MIN, LAT_MAX   = -90.0,  90.0
LNG_MIN, LNG_MAX   = -180.0, 180.0
ALT_MIN, ALT_MAX   = 0.0,    2000.0
SPD_MIN, SPD_MAX   = 0.0,    300.0
HDG_MIN, HDG_MAX   = 0.0,    360.0


# ============================================================
# Telemetry Data Class
# ============================================================

@dataclass
class TelemetryPacket:
    sensor_id:  str
    latitude:   float
    longitude:  float
    altitude:   float
    speed:      float
    heading:    float
    timestamp:  str
    object_id: str = ""

    def is_valid(self) -> bool:
        """Validate data ranges. Discard packets outside physical limits."""
        return (
            LAT_MIN <= self.latitude  <= LAT_MAX  and
            LNG_MIN <= self.longitude <= LNG_MAX  and
            ALT_MIN <= self.altitude  <= ALT_MAX  and
            SPD_MIN <= self.speed     <= SPD_MAX  and
            HDG_MIN <= self.heading   <= HDG_MAX
        )


# ============================================================
# Object Simulator (simulates a flying object)
# ============================================================

class FlyingObject:
    def __init__(self, obj_id: str, start_lat: float, start_lng: float):
        self.id        = obj_id
        self.lat       = start_lat
        self.lng       = start_lng
        self.altitude  = random.uniform(20, 150)
        self.speed     = random.uniform(10, 60)   # km/h
        self.heading   = random.uniform(0, 360)   # degrees
        self._alive    = True

        # Flight behavior parameters
        self._turn_rate  = random.uniform(-5, 5)    # degrees/step
        self._climb_rate = random.uniform(-2, 2)    # m/step
        self._steps      = 0
        self._max_steps  = random.randint(40, 120)

    @property
    def alive(self) -> bool:
        return self._alive

    def step(self) -> None:
        """Advance the object one simulation step."""
        self._steps += 1
        if self._steps >= self._max_steps:
            self._alive = False
            return

        # Occasional behavior changes (simulate anomalous behavior)
        if random.random() < 0.05:
            self._turn_rate  = random.uniform(-15, 15)
            self._climb_rate = random.uniform(-5, 5)
            self.speed       = max(0, self.speed + random.uniform(-10, 10))

        # Update heading
        self.heading = (self.heading + self._turn_rate) % 360

        # Update position (approximate: 1 degree ≈ 111 km)
        speed_deg_per_step = (self.speed / 3600) / 111 * INTERVAL_SEC
        rad_heading = math.radians(self.heading)
        self.lat += math.cos(rad_heading) * speed_deg_per_step
        self.lng += math.sin(rad_heading) * speed_deg_per_step

        # Update altitude
        self.altitude = max(5.0, min(1500.0, self.altitude + self._climb_rate))

        # Keep in simulation area (wrap around)
        if abs(self.lat - CENTER_LAT) > 0.1:
            self.heading = (180 - self.heading) % 360
        if abs(self.lng - CENTER_LNG) > 0.1:
            self.heading = (360 - self.heading) % 360


# ============================================================
# Sensor Simulator
# ============================================================

class SensorSimulator:
    def __init__(self, sensor_id: str, lat: float, lng: float, range_km: float = 5.0):
        self.sensor_id = sensor_id
        self.lat       = lat
        self.lng       = lng
        self.range_km  = range_km
        self._objects: List[FlyingObject] = []
        self._running  = False

    def _generate_new_object(self) -> FlyingObject:
        """Spawn a new flying object near the sensor."""
        angle = random.uniform(0, 2 * math.pi)
        dist  = random.uniform(0.005, 0.04)  # ~0.5–4 km offset
        lat = self.lat + dist * math.cos(angle)
        lng = self.lng + dist * math.sin(angle)
        return FlyingObject(f"{self.sensor_id}-OBJ-{int(time.time()*1000)%9999}", lat, lng)

    def get_detections(self) -> List[TelemetryPacket]:
        """
        Update all objects and return valid telemetry packets.
        Validates data ranges (RF-029).
        """
        # Randomly spawn new objects
        if len(self._objects) < 3 and random.random() < 0.3:
            self._objects.append(self._generate_new_object())

        # Update all objects
        valid_packets = []
        for obj in self._objects[:]:
            obj.step()
            if not obj.alive:
                self._objects.remove(obj)
                continue

            packet = TelemetryPacket(
                sensor_id  = self.sensor_id,
                object_id  = obj.id,
                latitude   = round(obj.lat, 6),
                longitude  = round(obj.lng, 6),
                altitude   = round(obj.altitude, 1),
                speed      = round(obj.speed, 1),
                heading    = round(obj.heading, 1),
                timestamp  = datetime.now(timezone.utc).isoformat(),
            )

            # Validate before sending (RF-029)
            if packet.is_valid():
                valid_packets.append(packet)
            else:
                logger.warning(
                    "Invalid telemetry discarded",
                    sensor=self.sensor_id,
                    lat=packet.latitude,
                    lng=packet.longitude,
                    alt=packet.altitude,
                )

        return valid_packets


# ============================================================
# Network Sender
# ============================================================

class TelemetrySender:
    def __init__(self, backend_url: str, token: str = ""):
        self.backend_url = backend_url
        self.token = token
        self._client = httpx.AsyncClient(timeout=5.0)

    async def send(self, packet: TelemetryPacket) -> bool:
        """Send telemetry packet to backend."""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            res = await self._client.post(
                f"{self.backend_url}/sensors/telemetry",
                json=asdict(packet),
                headers=headers,
            )
            return res.status_code in (200, 201, 202)
        except Exception as e:
            logger.debug(f"Backend not available: {e}")
            return False

    async def close(self):
        await self._client.aclose()


# ============================================================
# Main Simulation Loop
# ============================================================

async def main():
    logger.info("AeroGuard Sensor Simulator starting...")
    logger.info(f"Backend: {BACKEND_URL} | Interval: {INTERVAL_SEC}s")

    # Define simulated sensors (matching backend sensor IDs)
    sensors = [
        SensorSimulator("SEN-1", 4.742, -74.072, range_km=5),
        SensorSimulator("SEN-2", 4.680, -74.072, range_km=5),
        SensorSimulator("SEN-3", 4.711, -74.032, range_km=3),
    ]

    sender = TelemetrySender(BACKEND_URL, SENSOR_TOKEN)

    try:
        iteration = 0
        while True:
            iteration += 1
            all_packets = []

            for sensor in sensors:
                packets = sensor.get_detections()
                all_packets.extend(packets)

                for packet in packets:
                    logger.info(
                        f"[{sensor.sensor_id}] → "
                        f"lat={packet.latitude}, lng={packet.longitude}, "
                        f"alt={packet.altitude}m, spd={packet.speed}km/h, "
                        f"hdg={packet.heading}°"
                    )
                    await sender.send(packet)

            if not any(packets for sensor in sensors for packets in [sensor.get_detections()]):
                logger.info("No active objects this cycle.")

            logger.info(f"Cycle {iteration}: {len(all_packets)} telemetry packets sent.")
            await asyncio.sleep(INTERVAL_SEC)

    except KeyboardInterrupt:
        logger.info("Simulator stopped by user.")
    finally:
        await sender.close()


if __name__ == "__main__":
    asyncio.run(main())
