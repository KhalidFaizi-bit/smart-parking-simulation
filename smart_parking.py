from datetime import datetime
from enum import Enum
import math


class VehicleType(Enum):
    MOTORCYCLE = 1
    COMPACT = 2
    LARGE = 3


class SpotType(Enum):
    MOTORCYCLE = 1
    COMPACT = 2
    LARGE = 3


class Vehicle:
    def __init__(self, license_plate: str, vehicle_type: VehicleType):
        self.license_plate = license_plate
        self.vehicle_type = vehicle_type


class ParkingSpot:
    def __init__(self, spot_id: int, spot_type: SpotType):
        self.spot_id = spot_id
        self.spot_type = spot_type
        self.is_occupied = False
        self.current_vehicle = None
        self.entry_time = None

    def can_fit_vehicle(self, vehicle: Vehicle) -> bool:
        """Determines if a vehicle fits in this spot based on size rules."""
        if self.spot_type == SpotType.LARGE:
            return True  # Large spots fit any vehicle
        if self.spot_type == SpotType.COMPACT:
            return vehicle.vehicle_type in (
                VehicleType.COMPACT,
                VehicleType.MOTORCYCLE,
            )
        if self.spot_type == SpotType.MOTORCYCLE:
            return vehicle.vehicle_type == VehicleType.MOTORCYCLE
        return False

    def park(self, vehicle: Vehicle):
        self.current_vehicle = vehicle
        self.is_occupied = True
        self.entry_time = datetime.now()

    def unpark(self) -> tuple[Vehicle, datetime]:
        vehicle = self.current_vehicle
        entry_time = self.entry_time
        self.current_vehicle = None
        self.is_occupied = False
        self.entry_time = None
        return vehicle, entry_time


class SmartParkingLot:
    HOURLY_RATE = 5.00  # $5 per hour

    def __init__(self, name: str):
        self.name = name
        self.spots: list[ParkingSpot] = []
        self.active_tickets: dict[str, int] = (
            {}
        )  # License plate -> Spot ID mapping

    def add_spot(self, spot: ParkingSpot):
        self.spots.append(spot)

    def find_available_spot(self, vehicle: Vehicle) -> ParkingSpot | None:
        """Finds the best available spot for a given vehicle type."""
        for spot in self.spots:
            if not spot.is_occupied and spot.can_fit_vehicle(vehicle):
                return spot
        return None

    def park_vehicle(self, vehicle: Vehicle) -> str:
        """Parks a vehicle and registers an entry ticket."""
        if vehicle.license_plate in self.active_tickets:
            return f"⚠️ Vehicle {vehicle.license_plate} is already parked."

        spot = self.find_available_spot(vehicle)
        if not spot:
            return f"❌ Parking full! No suitable spot for {vehicle.vehicle_type.name} ({vehicle.license_plate})."

        spot.park(vehicle)
        self.active_tickets[vehicle.license_plate] = spot.spot_id
        return f"✅ Vehicle {vehicle.license_plate} parked in Spot #{spot.spot_id} ({spot.spot_type.name})."

    def remove_vehicle(self, license_plate: str) -> str:
        """Removes a vehicle and calculates total parking fee."""
        if license_plate not in self.active_tickets:
            return f"⚠️ Vehicle {license_plate} not found in system."

        spot_id = self.active_tickets.pop(license_plate)
        spot = next(s for s in self.spots if s.spot_id == spot_id)
        vehicle, entry_time = spot.unpark()

        # Simulate time duration (or calculate actual elapsed seconds)
        duration_hours = max(
            1, math.ceil((datetime.now() - entry_time).seconds / 3600)
        )
        total_fee = duration_hours * self.HOURLY_RATE

        return (
            f"🚗 Vehicle {vehicle.license_plate} unparked from Spot #{spot_id}.\n"
            f"   Duration: {duration_hours} hr(s) | Total Fee: ${total_fee:.2f}"
        )

    def display_status(self):
        """Prints current parking lot capacity status."""
        total = len(self.spots)
        occupied = sum(1 for s in self.spots if s.is_occupied)
        available = total - occupied
        print(
            f"\n--- 🅿️ {self.name} Status: {available}/{total} Spots Available ---"
        )
        for s in self.spots:
            status = (
                f"OCCUPIED by [{s.current_vehicle.license_plate}]"
                if s.is_occupied
                else "FREE"
            )
            print(f"  Spot #{s.spot_id:02d} [{s.spot_type.name:<10}] : {status}")
        print("-" * 50 + "\n")


# ---------------------------------------------------------
# Demonstration / Driver Script
# ---------------------------------------------------------
if __name__ == "__main__":
    lot = SmartParkingLot("UMSL Central Deck")

    # Add spots (2 Motorcycle, 2 Compact, 2 Large)
    lot.add_spot(ParkingSpot(1, SpotType.MOTORCYCLE))
    lot.add_spot(ParkingSpot(2, SpotType.MOTORCYCLE))
    lot.add_spot(ParkingSpot(3, SpotType.COMPACT))
    lot.add_spot(ParkingSpot(4, SpotType.COMPACT))
    lot.add_spot(ParkingSpot(5, SpotType.LARGE))
    lot.add_spot(ParkingSpot(6, SpotType.LARGE))

    # Create vehicles
    v1 = Vehicle("MO-123", VehicleType.COMPACT)
    v2 = Vehicle("MO-999", VehicleType.LARGE)
    v3 = Vehicle("MOTO-1", VehicleType.MOTORCYCLE)

    # Park vehicles
    print(lot.park_vehicle(v1))
    print(lot.park_vehicle(v2))
    print(lot.park_vehicle(v3))

    # Show Lot Status
    lot.display_status()

    # Unpark vehicle & checkout
    print(lot.remove_vehicle("MO-123"))

    # Show updated status
    lot.display_status()