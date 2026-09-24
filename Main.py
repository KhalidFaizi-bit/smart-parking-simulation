"""
main.py
-------
Command-line entry point for the Smart Parking System.

This file only handles menus and printing. It doesn't know how a fee
is calculated or how a spot is chosen - it just calls methods on
SmartParkingSystem and displays the result. That separation is what
lets you replace this CLI with, say, a Flask API later without
touching parking_system.py at all.
"""

from models import VehicleType
from parking_system import SmartParkingSystem, ParkingLotFullError, DuplicateCheckInError
from reporting import ParkingReportGenerator

VEHICLE_MENU = {
    "1": VehicleType.MOTORCYCLE,
    "2": VehicleType.COMPACT,
    "3": VehicleType.STANDARD,
    "4": VehicleType.LARGE,
}


def prompt_vehicle_type() -> VehicleType:
    print("Vehicle type: 1) Motorcycle  2) Compact  3) Standard  4) Large")
    choice = input("Select: ").strip()
    return VEHICLE_MENU.get(choice, VehicleType.STANDARD)


def run() -> None:
    print("=" * 40)
    print("  Welcome To Khalid's Parking Garage")
    print("=" * 40)

    system = SmartParkingSystem()
    reporter = ParkingReportGenerator(system.db_name)

    while True:
        print(
            "\n1. Check-In Vehicle\n2. Check-Out Vehicle\n3. View Active Lot"
            "\n4. Occupancy Summary\n5. Generate Report\n6. Exit"
        )
        choice = input("Select an option: ").strip()

        if choice == "1":
            plate = input("Enter License Plate: ")
            vehicle_type = prompt_vehicle_type()
            try:
                spot = system.check_in(plate, vehicle_type)
                print(f"[SUCCESS] {plate.strip().upper()} parked at Spot #{spot}.")
            except (ParkingLotFullError, DuplicateCheckInError) as e:
                print(f"[ERROR] {e}")

        elif choice == "2":
            plate = input("Enter License Plate: ")
            try:
                result = system.check_out(plate)
                print(f"[CHECK-OUT COMPLETE] Plate: {result['plate_number']} | Spot Freed: #{result['spot_number']}")
                print(f"Total Duration Bill: ${result['fee']:.2f}")
            except ValueError as e:
                print(f"[ERROR] {e}")

        elif choice == "3":
            rows = system.list_active()
            print("\n--- ACTIVE PARKING OCCUPANCY ---")
            if not rows:
                print("No vehicles currently parked.")
            for plate, spot, entry_time in rows:
                print(f"Spot #{spot:02d} | Plate: {plate} | Check-in: {entry_time}")
            print("--------------------------------\n")

        elif choice == "4":
            summary = system.occupancy_summary()
            print("\n--- SENSOR OCCUPANCY SUMMARY ---")
            for size, (occupied, total) in summary.items():
                print(f"{size.value:<8}: {occupied}/{total} occupied")
            print("---------------------------------\n")

        elif choice == "5":
            report = reporter.generate_summary_report()
            print("\n--- PARKING ANALYTICS REPORT ---")
            print(f"Cumulative Revenue: ${report['cumulative_revenue']:.2f}")
            print(f"Average Dwell Time: {report['average_dwell_time_minutes']:.1f} minutes")
            print("Daily Occupancy Trends:")
            if not report["daily_occupancy_trends"]:
                print("  No completed sessions yet.")
            for day, count in report["daily_occupancy_trends"].items():
                print(f"  {day}: {count} vehicle(s) checked in")
            print("---------------------------------\n")

        elif choice == "6":
            break

        else:
            print("Invalid option, try again.")


if __name__ == "__main__":
    run()