"""
models.py
---------
Domain models for the Smart Parking System.

This file defines *what things are* (vehicle types, spot sizes) and
the business rule connecting them (which vehicle fits which spot).
It has no database or I/O code in it on purpose - these are rules
that shouldn't change just because we swap storage engines or the
CLI for a web front end.
"""

from dataclasses import dataclass
from enum import Enum


class VehicleType(str, Enum):
    """Vehicle categories the system can check in."""
    MOTORCYCLE = "Motorcycle"
    COMPACT = "Compact"
    STANDARD = "Standard"
    LARGE = "Large"


class SpotSize(str, Enum):
    """Physical parking spot sizes available in the garage."""
    SMALL = "Small"     # motorcycles only
    MEDIUM = "Medium"   # compact + standard cars
    LARGE = "Large"     # trucks/SUVs - can also host any smaller vehicle


# Which spot sizes each vehicle type may use, ordered from tightest
# fit to loosest. check-in tries these in order so a motorcycle never
# takes a Large spot while a Small one sits empty.
VEHICLE_SPOT_COMPATIBILITY: dict[VehicleType, list[SpotSize]] = {
    VehicleType.MOTORCYCLE: [SpotSize.SMALL, SpotSize.MEDIUM, SpotSize.LARGE],
    VehicleType.COMPACT:    [SpotSize.MEDIUM, SpotSize.LARGE],
    VehicleType.STANDARD:   [SpotSize.MEDIUM, SpotSize.LARGE],
    VehicleType.LARGE:      [SpotSize.LARGE],
}


# Tiered hourly billing: the rate is set by which size spot a vehicle
# actually occupied, not by vehicle type - a motorcycle that overflows
# into a Large spot pays the Large rate, since that's the space it's
# using up. Larger spots are scarcer and cost more.
SPOT_SIZE_HOURLY_RATE: dict[SpotSize, float] = {
    SpotSize.SMALL: 2.0,
    SpotSize.MEDIUM: 4.0,
    SpotSize.LARGE: 6.0,
}


@dataclass(frozen=True)
class ParkingSpot:
    """A single physical spot in the garage. Size is fixed once built."""
    number: int
    size: SpotSize


def build_garage_layout(
    small_spots: int = 10,
    medium_spots: int = 25,
    large_spots: int = 15,
) -> list[ParkingSpot]:
    """
    Build the fixed physical layout of the garage: 50 spots total by
    default, numbered sequentially (Small, then Medium, then Large).

    This mirrors a real garage where each physical spot has a sensor
    wired to it and a size that never changes - only its occupancy
    (reported by the sensor) changes over time.
    """
    layout: list[ParkingSpot] = []
    spot_number = 1

    for _ in range(small_spots):
        layout.append(ParkingSpot(spot_number, SpotSize.SMALL))
        spot_number += 1
    for _ in range(medium_spots):
        layout.append(ParkingSpot(spot_number, SpotSize.MEDIUM))
        spot_number += 1
    for _ in range(large_spots):
        layout.append(ParkingSpot(spot_number, SpotSize.LARGE))
        spot_number += 1

    return layout