import datetime
import sqlite3

class SmartParkingSystem:
    def __init__(self, db_name="parking_lot.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
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

    def get_available_spot(self, total_spots=50):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT spot_number FROM active_sessions")
            occupied = {row[0] for row in cursor.fetchall()}
            for spot in range(1, total_spots + 1):
                if spot not in occupied:
                    return spot
        return None

    def check_in(self, plate_number, vehicle_type="Standard"):
        spot = self.get_available_spot()
        if not spot:
            print("[ERROR] Parking lot is currently at full capacity.")
            return False

        entry_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO active_sessions VALUES (?, ?, ?, ?)",
                    (plate_number.upper(), spot, entry_time, vehicle_type)
                )
                conn.commit()
            print(f"[SUCCESS] Vehicle {plate_number.upper()} parked at Spot #{spot} at {entry_time}.")
            return True
        except sqlite3.IntegrityError:
            print(f"[ERROR] Vehicle {plate_number.upper()} is already checked in.")
            return False

    def calculate_fee(self, entry_time_str, hourly_rate=4.0):
        entry_time = datetime.datetime.strptime(entry_time_str, "%Y-%m-%d %H:%M:%S")
        exit_time = datetime.datetime.now()
        duration_hours = max((exit_time - entry_time).total_seconds() / 3600, 0.5)
        return round(duration_hours * hourly_rate, 2), exit_time.strftime("%Y-%m-%d %H:%M:%S")

    def check_out(self, plate_number):
        plate_number = plate_number.upper()
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT spot_number, entry_time, vehicle_type FROM active_sessions WHERE plate_number = ?", (plate_number,))
            record = cursor.fetchone()

            if not record:
                print(f"[ERROR] No active check-in record found for plate {plate_number}.")
                return

            spot, entry_time, vtype = record
            fee, exit_time = self.calculate_fee(entry_time)

            cursor.execute("DELETE FROM active_sessions WHERE plate_number = ?", (plate_number,))
            cursor.execute(
                "INSERT INTO history_logs (plate_number, spot_number, entry_time, exit_time, fee_charged) VALUES (?, ?, ?, ?, ?)",
                (plate_number, spot, entry_time, exit_time, fee)
            )
            conn.commit()

        print(f"[CHECK-OUT COMPLETE]")
        print(f"Plate: {plate_number} | Spot Freed: #{spot}")
        print(f"Total Duration Bill: ${fee:.2f}")

    def list_active(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT plate_number, spot_number, entry_time FROM active_sessions")
            rows = cursor.fetchall()
            print("\n--- ACTIVE PARKING OCCUPANCY ---")
            for r in rows:
                print(f"Spot #{r[1]:02d} | Plate: {r[0]} | Check-in: {r[2]}")
            if not rows:
                print("No vehicles currently parked.")
            print("--------------------------------\n")

if __name__ == "__main__":
    system = SmartParkingSystem()
    while True:
        print("\n1. Check-In Vehicle\n2. Check-Out Vehicle\n3. View Active Lot\n4. Exit")
        choice = input("Select an option: ").strip()
        if choice == "1":
            plate = input("Enter License Plate: ")
            system.check_in(plate)
        elif choice == "2":
            plate = input("Enter License Plate: ")
            system.check_out(plate)
        elif choice == "3":
            system.list_active()
        elif choice == "4":
            break
# This is the final Boss