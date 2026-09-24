# 🅿️ Smart Parking System Simulation

A modular, object-oriented Python simulation of a sensor-driven smart parking garage. The system models a fixed-size garage where each physical spot is wired to an occupancy sensor, matches incoming vehicles to a spot that actually fits them, and automates fee calculation on exit.

---

## ✨ Features
- **Simulated Sensor Layer:** `SpotSensorNetwork` models each spot's occupancy sensor. Check-in/check-out logic never touches the database directly for availability — it asks the sensor layer, so swapping in real hardware later only means replacing that one class.
- **Size-Aware Spot Matching:** Vehicles (`Motorcycle`, `Compact`, `Standard`, `Large`) are matched to the tightest-fitting free spot (`Small`, `Medium`, `Large`) using an explicit compatibility table, so a motorcycle never occupies a large spot while a small one sits open.
- **Tiered Billing:** Fees are charged by the size of the spot occupied — Small $2/hr, Medium $4/hr, Large $6/hr — with a 30-minute minimum charge.
- **Occupancy Dashboard:** A live breakdown of occupied vs. total spots per size class.
- **Analytics Reporting:** `ParkingReportGenerator` computes daily occupancy trends, average dwell time, and cumulative revenue from completed sessions.
- **Object-Oriented Design:** `Enum`s for vehicle/spot types, a frozen `dataclass` for spots, custom exceptions (`ParkingLotFullError`, `DuplicateCheckInError`) instead of silent failures, and a clean separation of concerns across files.

---

## 🗂️ Project Structure
```
models.py               # Domain rules: VehicleType, SpotSize, compatibility + rate tables, garage layout
parking_system.py       # SpotSensorNetwork + SmartParkingSystem (DB access, check-in/out, tiered billing)
reporting.py            # ParkingReportGenerator - daily trends, dwell time, revenue analytics
main.py                 # CLI menu only — no business logic
test_parking_system.py  # Unit tests for size matching, duplicates, full-lot, tiered fees, and reporting
```

Each layer only knows about the one below it: `main.py` calls `SmartParkingSystem`, which calls `SpotSensorNetwork`, which is the only thing that touches SQLite for occupancy reads.

---

## 🛠️ Tech Stack
- **Language:** Python 3.10+
- **Core Modules:** `sqlite3`, `datetime`, `enum`, `dataclasses`, `logging` — standard library only, no external dependencies.

---

## ▶️ Running It
```bash
python main.py
```

## ✅ Running Tests
```bash
pip install pytest   # if not already installed
pytest test_parking_system.py -v
```

---

## 🔭 Possible Next Steps
- Persist the garage layout itself in the database instead of rebuilding it in code each run.
- Add a reservation system (hold a spot before arrival).
- Peak-hour or dynamic (demand-based) pricing on top of the existing size tiers.
- Wrap `SmartParkingSystem` in a small FastAPI service so the sensor layer could report over HTTP from real hardware.
