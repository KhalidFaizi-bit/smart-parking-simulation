"""
parking_system.py
------------------
Core business logic for the Smart Parking System.

Two things live here:

  1. SpotSensorNetwork - a small abstraction that stands in for real
     hardware sensors. Today it "reads" occupancy from the database,
     but nothing else in the system cares where that reading comes
     from. Swapping in real IoT sensors later means replacing this
     one class, not touching check-in/check-out logic.

  2. SmartParkingSystem - check-in, check-out, fee calculation, and
     reporting. This is the same responsibility the original single
     file had, just separated from the CLI and the domain rules.
"""

import datetime
import logging
import sqlite3

from models import (
    VehicleType,
    SpotSize,
    ParkingSpot,
    VEHICLE_SPOT_COMPATIBILITY,
    SPOT_SIZE_HOURLY_RATE,
    build_garage_layout,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class ParkingLotFullError(Exception):
    """Raised when no compatible spot is available for a vehicle."""


class DuplicateCheckInError(Exception):
    """Raised when a plate is already checked in."""


class SpotSensorNetwork:
    """
    Simulates the physical sensor layer of the garage.

    In a real deployment, each spot has an ultrasonic/infrared sensor
    that reports OCCUPIED/VACANT to a controller, which writes that
    state somewhere the system can read it. We don't have real
    hardware here, so we simulate the sensor reading by treating
    "is there an active session for this spot?" as the sensor
    signal - it's the same read the system would do either way.
    """

    def __init__(self, db_name: str, layout: list[ParkingSpot]):
        self.db_name = db_name
        self.layout = layout

    def get_occupied_spot_numbers(self) -> set[int]:
        """Poll for every spot number currently in use."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT spot_number FROM active_sessions")
            return {row[0] for row in cursor.fetchall()}

    def scan_free_spots(self, size: SpotSize) -> list[int]:
        """
        Simulate a sensor sweep: every free spot of the given size,
        closest-to-entrance (lowest number) first.
        """
        occupied = self.get_occupied_spot_numbers()
        return [
            spot.number
            for spot in self.layout
            if spot.size == size and spot.number not in occupied
        ]


class SmartParkingSystem:
    def __init__(self, db_name: str = "parking_lot.db", layout: list[ParkingSpot] | None = None):
        self.db_name = db_name
        self.layout = layout or build_garage_layout()
        self.sensors = SpotSensorNetwork(self.db_name, self.layout)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_sessions (
                    plate_number TEXT PRIMARY KEY,
                    spot_number INTEGER UNIQUE,
                    entry_time TEXT,
                    vehicle_type TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate_number TEXT,
                    spot_number INTEGER,
                    entry_time TEXT,
                    exit_time TEXT,
                    fee_charged REAL
                )
            """)
            conn.commit()

    def _find_compatible_spot(self, vehicle_type: VehicleType) -> int | None:
        """
        Ask the sensor network for a free spot this vehicle fits in,
        trying the tightest-fitting size class first (see
        VEHICLE_SPOT_COMPATIBILITY in models.py).
        """
        for size in VEHICLE_SPOT_COMPATIBILITY[vehicle_type]:
            free_spots = self.sensors.scan_free_spots(size)
            if free_spots:
                return free_spots[0]
        return None

    def _get_spot_size(self, spot_number: int) -> SpotSize:
        """Look up the fixed size of a spot by its number, for billing."""
        for spot in self.layout:
            if spot.number == spot_number:
                return spot.size
        raise ValueError(f"Spot #{spot_number} is not part of this garage's layout.")

    def check_in(self, plate_number: str, vehicle_type: VehicleType = VehicleType.STANDARD) -> int:
        """
        Check a vehicle in. Returns the assigned spot number.

        Raises:
            ParkingLotFullError: no compatible spot is free.
            DuplicateCheckInError: this plate is already parked.

        Note on correctness: the UNIQUE constraint on spot_number is
        a deliberate safety net. We scan for a free spot, then
        insert - if two check-ins somehow raced for the same spot in
        that gap, SQLite raises IntegrityError here instead of
        silently letting two cars "own" the same spot in the data.
        """
        plate_number = plate_number.strip().upper()
        spot_number = self._find_compatible_spot(vehicle_type)

        if spot_number is None:
            logger.warning("No free %s-compatible spot for %s", vehicle_type.value, plate_number)
            raise ParkingLotFullError(f"No available spot for a {vehicle_type.value} vehicle.")

        entry_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO active_sessions VALUES (?, ?, ?, ?)",
                    (plate_number, spot_number, entry_time, vehicle_type.value),
                )
                conn.commit()
        except sqlite3.IntegrityError as exc:
            if "plate_number" in str(exc) or "PRIMARY KEY" in str(exc):
                raise DuplicateCheckInError(f"{plate_number} is already checked in.") from exc
            raise  # a genuinely unexpected constraint failure - don't swallow it

        logger.info("Checked in %s at spot #%d (%s)", plate_number, spot_number, vehicle_type.value)
        return spot_number

    def calculate_fee(self, entry_time_str: str, hourly_rate: float = 4.0) -> tuple[float, str]:
        """
        Bill for a stay so far, with a 30-minute minimum charge.
        check_out() passes the tiered rate for the spot's size; the
        default here only applies if this is called standalone.
        """
        entry_time = datetime.datetime.strptime(entry_time_str, "%Y-%m-%d %H:%M:%S")
        exit_time = datetime.datetime.now()
        duration_hours = max((exit_time - entry_time).total_seconds() / 3600, 0.5)
        fee = round(duration_hours * hourly_rate, 2)
        return fee, exit_time.strftime("%Y-%m-%d %H:%M:%S")

    def check_out(self, plate_number: str) -> dict:
        """Check a vehicle out and move its record into history_logs."""
        plate_number = plate_number.strip().upper()
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT spot_number, entry_time, vehicle_type FROM active_sessions WHERE plate_number = ?",
                (plate_number,),
            )
            record = cursor.fetchone()

            if not record:
                logger.warning("Check-out failed - no active session for %s", plate_number)
                raise ValueError(f"No active check-in record found for plate {plate_number}.")

            spot_number, entry_time, _vehicle_type = record
            hourly_rate = SPOT_SIZE_HOURLY_RATE[self._get_spot_size(spot_number)]
            fee, exit_time = self.calculate_fee(entry_time, hourly_rate)

            cursor.execute("DELETE FROM active_sessions WHERE plate_number = ?", (plate_number,))
            cursor.execute(
                "INSERT INTO history_logs (plate_number, spot_number, entry_time, exit_time, fee_charged) "
                "VALUES (?, ?, ?, ?, ?)",
                (plate_number, spot_number, entry_time, exit_time, fee),
            )
            conn.commit()

        logger.info("Checked out %s from spot #%d - fee $%.2f", plate_number, spot_number, fee)
        return {
            "plate_number": plate_number,
            "spot_number": spot_number,
            "fee": fee,
            "entry_time": entry_time,
            "exit_time": exit_time,
        }

    def list_active(self) -> list[tuple]:
        """(plate, spot, entry_time) for every vehicle currently parked."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT plate_number, spot_number, entry_time FROM active_sessions ORDER BY spot_number"
            )
            return cursor.fetchall()

    def occupancy_summary(self) -> dict[SpotSize, tuple[int, int]]:
        """
        {size: (occupied, total)} for each spot size - a quick
        sensor-driven occupancy dashboard.
        """
        occupied = self.sensors.get_occupied_spot_numbers()
        summary: dict[SpotSize, tuple[int, int]] = {}
        for size in SpotSize:
            spots_of_size = [s for s in self.layout if s.size == size]
            occupied_count = sum(1 for s in spots_of_size if s.number in occupied)
            summary[size] = (occupied_count, len(spots_of_size))
        return summary