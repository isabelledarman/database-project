"""Integration tests for logic.py.

Run from the project directory: python -m unittest -v test.py
"""

import os
import unittest
from pathlib import Path

import pymysql
from dotenv import load_dotenv

from logic import Database

load_dotenv()

DB_USER = "root"
DB_NAME = "project3510_test"
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = "localhost"

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = BASE_DIR / "sql/02_create_tables.sql"
DATA_FILE = BASE_DIR / "sql/03_insert_data.sql"


class TestDatabaseConfig:
    DB_USER = DB_USER
    DB_NAME = DB_NAME
    DB_PASSWORD = DB_PASSWORD
    DB_HOST = DB_HOST


def execute_sql_file(connection, path):
    """Execute a SQL script containing ordinary semicolon-terminated statements."""
    sql = path.read_text(encoding="utf-8")
    with connection.cursor() as cursor:
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
    connection.commit()


class LogicIntegrationTests(unittest.TestCase):
    report_rows = []

    @classmethod
    def setUpClass(cls):
        cls.admin_conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            unix_socket="/tmp/mysql.sock",
            autocommit=True,
        )
        with cls.admin_conn.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`")
            cursor.execute(
                f"CREATE DATABASE `{DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )

        setup_conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            unix_socket="/tmp/mysql.sock",
            autocommit=False,
        )
        try:
            execute_sql_file(setup_conn, SCHEMA_FILE)
            execute_sql_file(setup_conn, DATA_FILE)
        finally:
            setup_conn.close()

        cls.db = Database(TestDatabaseConfig)

    @classmethod
    def tearDownClass(cls):
        # Print one row per tested case, including cases that failed assertions
        print("\n\nTEST CASE RESULTS")
        headers = ("Test function", "Case input", "Output", "Status")
        rows = [headers] + cls.report_rows
        widths = [
            max(len(str(row[i])) for row in rows)
            for i in range(len(headers))
        ]
        fmt = " | ".join("{:<" + str(width) + "}" for width in widths)
        print(fmt.format(*headers))
        print("-+-".join("-" * width for width in widths))
        for row in cls.report_rows:
            print(fmt.format(*[str(value) for value in row]))

        if hasattr(cls, "db"):
            cls.db.close()
        if hasattr(cls, "admin_conn"):
            with cls.admin_conn.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`")
            cls.admin_conn.close()

    def check_case(self, case_input, output, passed, detail=""):
        """Record a case before asserting, so failures also appear in the report."""
        status = "PASS" if passed else "FAIL"
        rendered_output = str(output)
        if detail:
            rendered_output += f" ({detail})"
        self.report_rows.append(
            (self._testMethodName, str(case_input), rendered_output, status)
        )
        self.assertTrue(passed, detail or f"Case failed: {case_input}")

    # Query functions

    def test_available_rooms(self):
        cases = [
            ("Baltimore", "Queen", 0, "2026-12-10", "2026-12-12", {102, 201}),
            ("Baltimore", "Queen", 0, "2026-12-27", "2026-12-30", {201}),
            ("Baltimore", "Double", 1, "2026-12-10", "2026-12-12", {202}),
            ("Washington", "King", 0, "2026-12-10", "2026-12-12", {301, 1002}),
            ("Virginia Beach", "Queen", 1, "2026-12-10", "2026-12-12", {220}),
        ]
        for city, bed, smoking, check_in, check_out, expected in cases:
            with self.subTest(city=city, bed=bed, dates=(check_in, check_out)):
                rows = self.db.available_rooms(city, bed, smoking, check_in, check_out)
                actual = sorted(row["room"] for row in rows)
                expected_sorted = sorted(expected)
                self.check_case(
                    (city, bed, smoking, check_in, check_out),
                    actual,
                    set(actual) == expected,
                    f"expected {expected_sorted}",
                )

    def test_available_accessible_rooms(self):
        cases = [
            ("Washington", "2026-12-10", "2026-12-12", {302, 1003}),
            ("Washington", "2026-12-20", "2026-12-23", {1003}),
            ("Asheville", "2026-11-20", "2026-11-22", {21}),
            ("Baltimore", "2026-12-10", "2026-12-12", {101}),
            ("Virginia Beach", "2026-12-10", "2026-12-12", {120}),
        ]
        for city, check_in, check_out, expected in cases:
            with self.subTest(city=city, dates=(check_in, check_out)):
                rows = self.db.available_accessible_rooms(city, check_in, check_out)
                actual = sorted(row["room"] for row in rows)
                self.check_case(
                    (city, check_in, check_out),
                    actual,
                    set(actual) == expected,
                    f"expected {sorted(expected)}",
                )

    def test_mountain_or_ocean(self):
        cases = [
            ((), {("Asheville", "Pinecrest Lodge"), ("Virginia Beach", "Seaside Resort")}),
            (("Asheville",), {("Asheville", "Pinecrest Lodge")}),
            (("Baltimore",), set()),
        ]
        for args, expected in cases:
            rows = self.db.mountain_or_ocean(*args)
            actual = sorted((row["city"], row["name"]) for row in rows)
            self.check_case(
                args if args else "no city argument",
                actual,
                set(actual) == expected,
                f"expected {sorted(expected)}",
            )

    def test_reservations_by_person(self):
        cases = [
            ("Maya Ortiz", "4105550101", 3),
            ("Daniel Kim", "2025550142", 5),
            ("Priya Nair", "8285550177", 2),
            ("Sam Rivera", "9195550188", 1),
            ("Lena Park", "7575550133", 2),
        ]
        for name, phone, expected_rows in cases:
            rows = self.db.reservations_by_person(name, phone)
            self.check_case(
                (name, phone),
                f"{len(rows)} rows",
                len(rows) == expected_rows,
                f"expected {expected_rows} rows",
            )

    def test_guest_charges_list(self):
        cases = [
            ("Maya Ortiz", "4105550101", 5),
            ("Daniel Kim", "2025550142", 5),
            ("Priya Nair", "8285550177", 2),
            ("Sam Rivera", "9195550188", 0),
            ("Lena Park", "7575550133", 1),
        ]
        for name, phone, expected_rows in cases:
            rows = self.db.guest_charges_list(name, phone)
            self.check_case(
                (name, phone),
                f"{len(rows)} rows",
                len(rows) == expected_rows,
                f"expected {expected_rows} rows",
            )

        priya_charges = self.db.guest_charges_list("Priya Nair", "8285550177")
        has_late_cancel_charge = any(
            float(row["amount"]) == 23.80 for row in priya_charges
        )
        self.check_case(
            ("Priya Nair", "8285550177", "late cancellation amount"),
            [float(row["amount"]) for row in priya_charges],
            has_late_cancel_charge,
            "expected a $23.80 charge",
        )

    def test_no_show_reservations(self):
        rows = self.db.no_show_reservations()
        actual_numbers = {row["reservation_no"] for row in rows}
        self.check_case(
            "no arguments",
            f"{len(rows)} rows; reservation numbers {sorted(actual_numbers)}",
            len(rows) == 3 and actual_numbers == {7, 8},
            "expected 3 rows for reservation numbers 7 and 8",
        )

    def test_bonus_list(self):
        rows = self.db.bonus_list()
        actual = {(row["name"], row["year"]) for row in rows}
        expected = {("Daniel Kim", 2025), ("Maya Ortiz", 2026)}
        self.check_case(
            "no arguments",
            sorted(actual),
            actual == expected,
            f"expected {sorted(expected)}",
        )

    def test_reservation_details(self):
        rows = self.db.reservation_details()
        has_capitol_rooms = any(
            row["reservation_no"] == 2
            and row["room_no"] in (301, 302)
            and row["hotel_name"] == "Capitol Suites"
            for row in rows
        )
        all_nights_positive = all(row["nights"] > 0 for row in rows)
        passed = len(rows) > 0 and has_capitol_rooms and all_nights_positive
        self.check_case(
            "no arguments",
            f"{len(rows)} rows; Capitol Suites reservation 2 present; "
            f"all nights positive={all_nights_positive}",
            passed,
            "expected nonempty results, reservation 2 rooms 301/302 at Capitol Suites, "
            "and positive night counts",
        )

    # Insert, update, delete operations

    def test_insert_update_delete(self):
        inserted = self.db.insert_row(
            "Amenity",
            {"col_amenity_id": "99", "col_name": "Test Amenity"},
        )
        inserted_rows = self.db._query(
            "SELECT name FROM Amenity WHERE amenity_id = %s", (99,)
        )
        insert_ok = len(inserted_rows) == 1 and inserted_rows[0]["name"] == "Test Amenity"
        self.check_case(
            ("INSERT Amenity", {"amenity_id": 99, "name": "Test Amenity"}),
            f"matching rows={len(inserted_rows)}; insert_row returned {inserted}",
            insert_ok,
            "expected the new Amenity row to exist",
        )

        updated = self.db.update_row(
            "Amenity",
            {
                "pk_amenity_id": "99",
                "col_amenity_id": "99",
                "col_name": "Updated Amenity",
            },
        )
        updated_rows = self.db._query(
            "SELECT name FROM Amenity WHERE amenity_id = %s", (99,)
        )
        update_ok = (
            updated == 1
            and len(updated_rows) == 1
            and updated_rows[0]["name"] == "Updated Amenity"
        )
        self.check_case(
            ("UPDATE Amenity", {"pk_amenity_id": 99, "name": "Updated Amenity"}),
            f"update_row returned {updated}; stored name="
            f"{updated_rows[0]['name'] if updated_rows else 'missing'}",
            update_ok,
            "expected one updated row with name 'Updated Amenity'",
        )

        deleted = self.db.delete_row("Amenity", {"pk_amenity_id": "99"})
        remaining = self.db._query(
            "SELECT COUNT(*) AS n FROM Amenity WHERE amenity_id = %s", (99,)
        )[0]["n"]
        delete_ok = deleted == 1 and remaining == 0
        self.check_case(
            ("DELETE Amenity", {"pk_amenity_id": 99}),
            f"delete_row returned {deleted}; remaining rows={remaining}",
            delete_ok,
            "expected one deleted row and no remaining matching rows",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
