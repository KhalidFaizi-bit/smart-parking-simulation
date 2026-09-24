"""
reporting.py
------------
Analytics over completed parking sessions.

ParkingReportGenerator reads only from history_logs - it never
touches active_sessions - so pulling a report can never interfere
with a live check-in/check-out in progress. This is a separate class
from SmartParkingSystem on purpose: billing/allocation and analytics
are different responsibilities and change for different reasons.
"""

import datetime
import sqlite3
from collections import defaultdict


class ParkingReportGenerator:
    def __init__(self, db_name: str = "parking_lot.db"):
        self.db_name = db_name

    def _fetch_completed_sessions(self) -> list[tuple]:
        """(plate, spot, entry_time, exit_time, fee) for every finished session."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT plate_number, spot_number, entry_time, exit_time, fee_charged FROM history_logs"
            )
            return cursor.fetchall()

    def daily_occupancy_trends(self) -> dict[str, int]:
        """Number of completed sessions per calendar day, oldest first."""
        counts: dict[str, int] = defaultdict(int)
        for _, _, entry_time, _, _ in self._fetch_completed_sessions():
            day = entry_time.split(" ")[0]  # "YYYY-MM-DD HH:MM:SS" -> "YYYY-MM-DD"
            counts[day] += 1
        return dict(sorted(counts.items()))

    def average_dwell_time_minutes(self) -> float:
        """Average time between check-in and check-out, in minutes."""
        rows = self._fetch_completed_sessions()
        if not rows:
            return 0.0

        total_minutes = 0.0
        for _, _, entry_time, exit_time, _ in rows:
            entry = datetime.datetime.strptime(entry_time, "%Y-%m-%d %H:%M:%S")
            exit_ = datetime.datetime.strptime(exit_time, "%Y-%m-%d %H:%M:%S")
            total_minutes += (exit_ - entry).total_seconds() / 60

        return round(total_minutes / len(rows), 2)

    def cumulative_revenue(self) -> float:
        """Total fees collected across every completed session."""
        rows = self._fetch_completed_sessions()
        return round(sum(fee for *_rest, fee in rows), 2)

    def generate_summary_report(self) -> dict:
        """One-call bundle of every metric above - what main.py displays."""
        return {
            "daily_occupancy_trends": self.daily_occupancy_trends(),
            "average_dwell_time_minutes": self.average_dwell_time_minutes(),
            "cumulative_revenue": self.cumulative_revenue(),
        }