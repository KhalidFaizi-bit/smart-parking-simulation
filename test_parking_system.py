"""
test_parking_system.py
-----------------------
A small test suite covering the behaviors most worth demonstrating:
vehicle-size matching, duplicate check-ins, a full lot, and the fee
minimum. Uses a throwaway on-disk SQLite file per test (deleted in
teardown) so tests never touch your real parking_lot.db.

Run with:  pytest test_parking_system.py -v
"""

import datetime
import os
import unittest

from models import VehicleType, build_garage_layout
from parking_system import SmartParkingSystem, ParkingLotFullError, DuplicateCheckInError
from reporting import ParkingReportGenerator


class TestSmartParkingSystem(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_parking_lot.db"
        # tiny layout: 1 small, 1 medium, 1 large spot - makes "lot full" easy to trigger
        self.layout = build_garage_layout(small_spots=1, medium_spots=1, large_spots=1)
        self.system = SmartParkingSystem(db_name=self.db_path, layout=self.layout)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_motorcycle_gets_small_spot_not_large(self):
        spot = self.system.check_in("ABC123", VehicleType.MOTORCYCLE)
        self.assertEqual(spot, 1)  # spot #1 is the Small spot in this layout

    def test_large_vehicle_never_gets_small_or_medium_spot(self):
        spot = self.system.check_in("TRUCK99", VehicleType.LARGE)
        self.assertEqual(spot, 3)  # spot #3 is the Large spot

    def test_duplicate_check_in_raises(self):
        self.system.check_in("DUP111", VehicleType.STANDARD)
        with self.assertRaises(DuplicateCheckInError):
            self.system.check_in("DUP111", VehicleType.STANDARD)

    def test_lot_full_for_vehicle_type_raises(self):
        # Standard cars can use Medium OR Large spots, so both must fill
        # before a third Standard car is correctly rejected.
        self.system.check_in("CAR001", VehicleType.STANDARD)  # takes the Medium spot
        self.system.check_in("CAR002", VehicleType.STANDARD)  # overflows into the Large spot
        with self.assertRaises(ParkingLotFullError):
            self.system.check_in("CAR003", VehicleType.STANDARD)

    def test_fee_has_thirty_minute_minimum(self):
        self.system.check_in("FAST001", VehicleType.STANDARD)  # -> Medium spot, $4.00/hr
        result = self.system.check_out("FAST001")  # checked out almost immediately
        self.assertEqual(result["fee"], 2.0)  # 0.5 hr * $4.00/hr minimum

    def test_tiered_rate_billed_by_spot_size_not_vehicle_type(self):
        self.system.check_in("BIKE001", VehicleType.MOTORCYCLE)  # -> Small spot, $2.00/hr
        bike_result = self.system.check_out("BIKE001")
        self.assertEqual(bike_result["fee"], 1.0)  # 0.5 hr * $2.00/hr minimum

        self.system.check_in("TRUCK99", VehicleType.LARGE)  # -> Large spot, $6.00/hr
        truck_result = self.system.check_out("TRUCK99")
        self.assertEqual(truck_result["fee"], 3.0)  # 0.5 hr * $6.00/hr minimum

    def test_check_out_unknown_plate_raises(self):
        with self.assertRaises(ValueError):
            self.system.check_out("GHOST404")


class TestParkingReportGenerator(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_reporting.db"
        self.layout = build_garage_layout(small_spots=1, medium_spots=1, large_spots=1)
        self.system = SmartParkingSystem(db_name=self.db_path, layout=self.layout)
        self.reporter = ParkingReportGenerator(db_name=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_cumulative_revenue_sums_completed_sessions(self):
        self.system.check_in("CAR100", VehicleType.STANDARD)      # Medium, $4/hr -> $2.00 min fee
        self.system.check_out("CAR100")
        self.system.check_in("BIKE200", VehicleType.MOTORCYCLE)   # Small, $2/hr -> $1.00 min fee
        self.system.check_out("BIKE200")
        self.assertEqual(self.reporter.cumulative_revenue(), 3.0)

    def test_daily_occupancy_trends_counts_todays_sessions(self):
        self.system.check_in("CAR101", VehicleType.STANDARD)
        self.system.check_out("CAR101")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        trends = self.reporter.daily_occupancy_trends()
        self.assertEqual(trends.get(today), 1)

    def test_average_dwell_time_is_non_negative(self):
        self.system.check_in("CAR102", VehicleType.STANDARD)
        self.system.check_out("CAR102")
        self.assertGreaterEqual(self.reporter.average_dwell_time_minutes(), 0.0)

    def test_no_completed_sessions_yields_empty_report(self):
        # nothing has checked out yet in this fresh db
        report = self.reporter.generate_summary_report()
        self.assertEqual(report["cumulative_revenue"], 0.0)
        self.assertEqual(report["daily_occupancy_trends"], {})
        self.assertEqual(report["average_dwell_time_minutes"], 0.0)


if __name__ == "__main__":
    unittest.main()