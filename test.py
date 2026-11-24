"""Integration tests for logic.py.

Run from the project directory: python -m unittest -v test.py
"""

import os
import unittest
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from logic import Database

load_dotenv()

DB_USER = "root"
DB_NAME = "project3510_test"
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = "localhost"

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = BASE_DIR / "sql/02_create_tables.sql"
DATA_FILE = BASE_DIR / "sql/03_insert_data.sql"
REPORT_FILE = BASE_DIR / "test_results.xlsx"


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


def write_excel_report(headers, rows, path):
    """Write the test report to an .xlsx file as a formatted Excel table."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Test Results"

    ws.append(list(headers))
    for row in rows:
        ws.append([str(value) for value in row])

    last_row = len(rows) + 1
    last_col = get_column_letter(len(headers))

    # Real Excel table: banded rows, filter buttons, sortable columns
    table = Table(displayName="TestResults", ref=f"A1:{last_col}{last_row}")
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2", showRowStripes=True,
        showFirstColumn=False, showLastColumn=False, showColumnStripes=False,
    )
    ws.add_table(table)

    base = Font(name="Arial", size=10)
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    pass_fill = PatternFill("solid", start_color="C6EFCE")
    fail_fill = PatternFill("solid", start_color="FFC7CE")
    status_col = len(headers)

    for row in ws.iter_rows(min_row=1, max_row=last_row, max_col=len(headers)):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.font = header_font if cell.row == 1 else base
        # Color only the Status cell so the table style's banding stays visible
        if row[0].row > 1:
            status = row[status_col - 1]
            is_pass = status.value == "PASS"
            status.fill = pass_fill if is_pass else fail_fill
            status.font = Font(name="Arial", size=10, bold=True,
                               color="006100" if is_pass else "9C0006")
            status.alignment = Alignment(horizontal="center", vertical="top")
    ws.cell(row=1, column=status_col).alignment = Alignment(horizontal="center", vertical="top")

    # Column widths sized to content, capped so long outputs wrap instead of running off
    for idx in range(1, len(headers) + 1):
        longest = max(len(str(ws.cell(row=r, column=idx).value or "")) for r in range(1, last_row + 1))
        ws.column_dimensions[get_column_letter(idx)].width = min(max(longest + 2, 12), 60)

    ws.freeze_panes = "A2"
    wb.save(path)


# (table, row to insert, row after update). Every column is listed, as the strings a
# web form would submit. Where the primary key differs between the two rows, the
# update also changes the key.
CRUD_CASES = [
    ("Hotel",
     {"hotel_id": "99", "name": "Test Hotel", "address": "1 Test St", "city": "Raleigh", "rating": "3"},
     {"hotel_id": "99", "name": "Renamed Hotel", "address": "2 Test St", "city": "Durham", "rating": "5"}),
    ("Area",
     {"area": "Desert"},
     {"area": "Canyon"}),
    ("Hotel_Area",
     {"hotel_id": "1", "area": "Lake"},
     {"hotel_id": "1", "area": "River"}),
    ("Amenity",
     {"amenity_id": "98", "name": "Test Amenity"},
     {"amenity_id": "98", "name": "Renamed Amenity"}),
    ("Hotel_Amenity",
     {"hotel_id": "1", "amenity_id": "4", "charge": "5.00"},
     {"hotel_id": "1", "amenity_id": "4", "charge": "7.50"}),
    ("Conference_Room",
     {"hotel_id": "1", "conf_room_no": "999", "capacity": "10"},
     {"hotel_id": "1", "conf_room_no": "999", "capacity": "25"}),
    ("Room_Location",
     {"location": "Center"},
     {"location": "Middle"}),
    ("Room_Bed",
     {"bed": "Twin"},
     {"bed": "Bunk"}),
    ("Room_Type",
     {"hotel_id": "1", "bed": "King", "smoking": "1", "accessible": "1", "rate": "189.00"},
     {"hotel_id": "1", "bed": "King", "smoking": "1", "accessible": "1", "rate": "195.00"}),
    ("Room",
     {"hotel_id": "1", "room_no": "999", "floor": "9", "location": "North",
      "bed": "Queen", "smoking": "0", "accessible": "0"},
     {"hotel_id": "1", "room_no": "999", "floor": "8", "location": "South",
      "bed": "Queen", "smoking": "0", "accessible": "0"}),
    ("Guest",
     {"user_id": "99", "phone": "9995550199", "name": "Test Guest", "address": "1 Test Way, Raleigh, NC"},
     {"user_id": "99", "phone": "9995550199", "name": "Test Guest", "address": "2 Test Way, Durham, NC"}),
    ("Credit_Card",
     {"card_no": "9999999999999999", "exp_date": "2030-01-31", "holder_name": "Test Guest"},
     {"card_no": "9999999999999999", "exp_date": "2031-02-28", "holder_name": "Renamed Guest"}),
]

TEST_CARD = "3530111333300000"   # Sam Rivera's card (user 6)
TEST_USER = "6"


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

        try:
            write_excel_report(headers, cls.report_rows, REPORT_FILE)
            print(f"\nExcel report written to {REPORT_FILE}")
        except Exception as exc:  # never let a report problem block database cleanup
            print(f"\nCould not write Excel report: {exc}")

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

    # Helpers for the write tests

    def _stored(self, table, key):
        """Return the stored row as form-style strings, or None if it does not exist."""
        cols = self.db._columns(table)
        where = " AND ".join(f"`{k}` = %s" for k in key)
        rows = self.db._query(f"SELECT * FROM `{table}` WHERE {where}", tuple(key.values()))
        if not rows:
            return None
        return {c["name"]: Database._to_form(c, rows[0][c["name"]]) for c in cols}

    def _cleanup_sql(self, sql, params=()):
        """Best-effort delete used by addCleanup, so a failed test cannot leak rows."""
        try:
            self.db._execute(sql, params)
        except pymysql.MySQLError:
            pass

    def _force_delete(self, table, key):
        where = " AND ".join(f"`{k}` = %s" for k in key)
        self._cleanup_sql(f"DELETE FROM `{table}` WHERE {where}", tuple(key.values()))

    @staticmethod
    def _raises(exc_type, func, *args):
        """Call func; return the exception if it raised exc_type, otherwise None."""
        try:
            func(*args)
        except exc_type as exc:
            return exc
        return None

    def _reservation_form(self, **overrides):
        form = {
            "col_reservation_no": "",
            "col_user_id": TEST_USER,
            "col_card_no": TEST_CARD,
            "col_booking_date": "2026-11-24",
            "col_status": "Confirmed",
            "col_cancel_date": "",
        }
        form.update(overrides)
        return form

    def _make_reservation(self, **overrides):
        """Insert a reservation and register cleanup for it and anything attached to it."""
        rno = self.db.insert_row("Reservation", self._reservation_form(**overrides))
        # addCleanup runs last-in-first-out: charges, then rooms, then the reservation
        self.addCleanup(self._cleanup_sql, "DELETE FROM Reservation WHERE reservation_no = %s", (rno,))
        self.addCleanup(self._cleanup_sql, "DELETE FROM Reservation_Room WHERE reservation_no = %s", (rno,))
        self.addCleanup(self._cleanup_sql, "DELETE FROM Charge WHERE reservation_no = %s", (rno,))
        return rno

    @staticmethod
    def _room_form(rno, hotel_id, room_no, check_in, check_out):
        return {
            "col_reservation_no": str(rno),
            "col_hotel_id": str(hotel_id),
            "col_room_no": str(room_no),
            "col_check_in": check_in,
            "col_check_out": check_out,
        }

    def _reservation_update_form(self, rno, **overrides):
        form = {"pk_reservation_no": str(rno)}
        form.update({k: v for k, v in self._reservation_form().items() if k != "col_reservation_no"})
        form.update(overrides)
        return form

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


    def test_insert_update_delete_each_table(self):
        """Full insert -> update -> delete round trip for every table without an auto id."""
        for table, new_row, changed_row in CRUD_CASES:
            with self.subTest(table=table):
                pk_cols = [c["name"] for c in self.db._columns(table) if c["pk"]]
                old_key = {c: new_row[c] for c in pk_cols}
                new_key = {c: changed_row[c] for c in pk_cols}
                self.addCleanup(self._force_delete, table, new_key)
                self.addCleanup(self._force_delete, table, old_key)

                # INSERT
                self.db.insert_row(table, {"col_" + k: v for k, v in new_row.items()})
                stored = self._stored(table, old_key)
                self.check_case(
                    ("INSERT " + table, new_row),
                    stored,
                    stored == new_row,
                    "expected the stored row to match the inserted values",
                )

                # UPDATE (pk_* identifies the old row, col_* carries the new values)
                form = {"pk_" + k: v for k, v in old_key.items()}
                form.update({"col_" + k: v for k, v in changed_row.items()})
                updated = self.db.update_row(table, form)
                stored = self._stored(table, new_key)
                self.check_case(
                    ("UPDATE " + table, changed_row),
                    f"update_row returned {updated}; stored={stored}",
                    updated == 1 and stored == changed_row,
                    "expected one updated row matching the new values",
                )
                if old_key != new_key:
                    old_gone = self._stored(table, old_key) is None
                    self.check_case(
                        ("UPDATE " + table + " (key change)", f"{old_key} -> {new_key}"),
                        f"old key gone={old_gone}",
                        old_gone,
                        "expected the old primary key to no longer exist",
                    )

                # DELETE
                deleted = self.db.delete_row(table, {"pk_" + k: v for k, v in new_key.items()})
                remaining = self._stored(table, new_key)
                self.check_case(
                    ("DELETE " + table, new_key),
                    f"delete_row returned {deleted}; row exists={remaining is not None}",
                    deleted == 1 and remaining is None,
                    "expected one deleted row and nothing left",
                )

    def test_reservation_insert_update_delete(self):
        rno = self._make_reservation()
        self.check_case(
            "INSERT Reservation",
            f"insert_row returned auto id {rno}",
            isinstance(rno, int) and rno > 12,
            "expected a new AUTO_INCREMENT reservation_no above the seed data",
        )
        stored = self._stored("Reservation", {"reservation_no": rno})
        self.check_case(
            ("INSERT Reservation", "stored values"),
            stored,
            stored is not None and stored["status"] == "Confirmed" and stored["cancel_date"] == "",
            "expected status 'Confirmed' and no cancel_date",
        )

        updated = self.db.update_row(
            "Reservation", self._reservation_update_form(rno, col_status="Completed")
        )
        stored = self._stored("Reservation", {"reservation_no": rno})
        self.check_case(
            ("UPDATE Reservation", {"status": "Completed"}),
            f"update_row returned {updated}; status={stored and stored['status']}",
            updated == 1 and stored["status"] == "Completed",
            "expected one updated row with status 'Completed'",
        )

        deleted = self.db.delete_row("Reservation", {"pk_reservation_no": str(rno)})
        remaining = self._stored("Reservation", {"reservation_no": rno})
        self.check_case(
            ("DELETE Reservation", rno),
            f"delete_row returned {deleted}; row exists={remaining is not None}",
            deleted == 1 and remaining is None,
            "expected one deleted row",
        )

    def test_reservation_room_insert_update_delete(self):
        rno = self._make_reservation()
        key = {"reservation_no": rno, "hotel_id": 1, "room_no": 102}
        pk = {"pk_reservation_no": str(rno), "pk_hotel_id": "1", "pk_room_no": "102"}

        self.db.insert_row("Reservation_Room", self._room_form(rno, 1, 102, "2030-03-01", "2030-03-03"))
        stored = self._stored("Reservation_Room", key)
        self.check_case(
            "INSERT Reservation_Room",
            stored,
            stored is not None and stored["check_in"] == "2030-03-01" and stored["check_out"] == "2030-03-03",
            "expected the stay dates to be stored",
        )

        # The room must not clash with the row being edited
        form = dict(pk)
        form.update(self._room_form(rno, 1, 102, "2030-03-01", "2030-03-04"))
        updated = self.db.update_row("Reservation_Room", form)
        stored = self._stored("Reservation_Room", key)
        self.check_case(
            ("UPDATE Reservation_Room", {"check_out": "2030-03-04"}),
            f"update_row returned {updated}; check_out={stored and stored['check_out']}",
            updated == 1 and stored["check_out"] == "2030-03-04",
            "expected an update that is not blocked by its own row",
        )

        deleted = self.db.delete_row("Reservation_Room", pk)
        remaining = self._stored("Reservation_Room", key)
        self.check_case(
            ("DELETE Reservation_Room", pk),
            f"delete_row returned {deleted}; row exists={remaining is not None}",
            deleted == 1 and remaining is None,
            "expected one deleted row",
        )

    def test_reservation_room_booking_rules(self):
        rno = self._make_reservation()

        # Hotel 1 room 102 is booked 2026-12-28 to 2027-01-02 by reservation 5
        exc = self._raises(
            ValueError, self.db.insert_row, "Reservation_Room",
            self._room_form(rno, 1, 102, "2026-12-30", "2027-01-01"),
        )
        count = len(self.db._query("SELECT 1 FROM Reservation_Room WHERE reservation_no = %s", (rno,)))
        self.check_case(
            "overlapping stay in room 102",
            f"ValueError={exc is not None}; rows inserted={count}",
            exc is not None and count == 0,
            "expected a double-booking to be rejected",
        )

        exc = self._raises(
            ValueError, self.db.insert_row, "Reservation_Room",
            self._room_form(rno, 1, 102, "2030-05-05", "2030-05-03"),
        )
        self.check_case(
            "check-out before check-in",
            f"ValueError={exc is not None}",
            exc is not None,
            "expected check-out earlier than check-in to be rejected",
        )

        # Check-in on the day another guest checks out is allowed (stay ends 2027-01-02)
        exc = self._raises(
            Exception, self.db.insert_row, "Reservation_Room",
            self._room_form(rno, 1, 102, "2027-01-02", "2027-01-04"),
        )
        self.check_case(
            "back-to-back stay in room 102",
            f"error={exc!r}" if exc else "inserted",
            exc is None,
            "expected same-day turnover to be allowed",
        )

        # Reservation 3 is cancelled and held hotel 3 room 21 on 2026-11-20 to 2026-11-22
        rno2 = self._make_reservation()
        exc = self._raises(
            Exception, self.db.insert_row, "Reservation_Room",
            self._room_form(rno2, 3, 21, "2026-11-20", "2026-11-22"),
        )
        self.check_case(
            "room held only by a cancelled reservation",
            f"error={exc!r}" if exc else "inserted",
            exc is None,
            "expected a cancelled reservation not to block the room",
        )

    def test_reservation_cancellation_rules(self):
        # Insert: a cancel_date with the wrong status flips the status to Cancelled
        rno = self._make_reservation(col_cancel_date="2030-01-01T09:00")
        stored = self._stored("Reservation", {"reservation_no": rno})
        self.check_case(
            ("INSERT Reservation", "cancel_date set, status Confirmed"),
            stored,
            stored["status"] == "Cancelled",
            "expected status to be forced to 'Cancelled'",
        )

        # Update: status Cancelled with no date gets a cancel_date filled in
        rno = self._make_reservation()
        self.db.update_row(
            "Reservation", self._reservation_update_form(rno, col_status="Cancelled")
        )
        stored = self._stored("Reservation", {"reservation_no": rno})
        self.check_case(
            ("UPDATE Reservation", "status Cancelled, blank cancel_date"),
            stored,
            stored["status"] == "Cancelled" and stored["cancel_date"] != "",
            "expected a cancel_date to be filled in automatically",
        )

        # Late cancellation (within 48h of 3pm check-in) charges 20% of the first night.
        # Room 102 is Queen/non-smoking at hotel 1: $129.00 * 0.20 = $25.80
        rno = self._make_reservation()
        self.db.insert_row("Reservation_Room", self._room_form(rno, 1, 102, "2030-01-10", "2030-01-12"))
        self.db.update_row(
            "Reservation",
            self._reservation_update_form(rno, col_status="Cancelled", col_cancel_date="2030-01-09T10:00"),
        )
        charges = self.db._query("SELECT amount, charge_type FROM Charge WHERE reservation_no = %s", (rno,))
        self.check_case(
            ("late cancel", "room 102, cancelled 2030-01-09 10:00 for 2030-01-10 check-in"),
            [(float(c["amount"]), c["charge_type"]) for c in charges],
            len(charges) == 1 and float(charges[0]["amount"]) == 25.80 and charges[0]["charge_type"] == "Fee",
            "expected one $25.80 Fee charge",
        )

        # Editing an already-cancelled reservation must not charge again
        self.db.update_row(
            "Reservation",
            self._reservation_update_form(
                rno, col_status="Cancelled", col_cancel_date="2030-01-09T10:00",
                col_booking_date="2026-11-23",
            ),
        )
        charges = self.db._query("SELECT charge_id FROM Charge WHERE reservation_no = %s", (rno,))
        self.check_case(
            ("late cancel", "edit after cancellation"),
            f"{len(charges)} charge rows",
            len(charges) == 1,
            "expected no second fee",
        )

        # Early cancellation (well before check-in) is free
        rno = self._make_reservation()
        self.db.insert_row("Reservation_Room", self._room_form(rno, 1, 102, "2030-01-10", "2030-01-12"))
        self.db.update_row(
            "Reservation",
            self._reservation_update_form(rno, col_status="Cancelled", col_cancel_date="2029-12-01T10:00"),
        )
        charges = self.db._query("SELECT charge_id FROM Charge WHERE reservation_no = %s", (rno,))
        self.check_case(
            ("early cancel", "cancelled 2029-12-01 for 2030-01-10 check-in"),
            f"{len(charges)} charge rows",
            len(charges) == 0,
            "expected no cancellation fee",
        )

    def test_bonus_for_reservation(self):
        # Sam Rivera (user 6) only has a cancelled booking, so three new 2026 bookings earn the bonus
        # Check right after each insert: the Bonus view is per guest per year, so once the
        # third booking exists, every one of the three reservation numbers reports the bonus.
        results = []
        for _ in range(3):
            rno = self._make_reservation()
            results.append(self.db.bonus_for_reservation(rno))
        self.check_case(
            "3 new 2026 reservations for Sam Rivera",
            results,
            results == [None, None, "Sam Rivera"],
            "expected the bonus to appear on the third booking",
        )
        bonus_names = {(r["name"], r["year"]) for r in self.db.bonus_list()}
        self.check_case(
            "bonus_list after the third booking",
            sorted(bonus_names),
            ("Sam Rivera", 2026) in bonus_names,
            "expected Sam Rivera 2026 in the bonus list",
        )

    def test_charge_insert_update_delete(self):
        form = {
            "col_charge_id": "",
            "col_reservation_no": "1",
            "col_card_no": "4111111111111111",
            "col_amount": "10.00",
            "col_reason": "Test charge",
            "col_charge_type": "Fee",
            "col_charge_date": "2026-11-24",
        }
        charge_id = self.db.insert_row("Charge", form)
        self.addCleanup(self._force_delete, "Charge", {"charge_id": charge_id})
        stored = self._stored("Charge", {"charge_id": charge_id})
        self.check_case(
            "INSERT Charge",
            f"auto id {charge_id}; stored={stored}",
            charge_id > 0 and stored is not None and stored["amount"] == "10.00",
            "expected a new AUTO_INCREMENT charge_id and the stored amount",
        )

        update = {"pk_charge_id": str(charge_id)}
        update.update({k: v for k, v in form.items() if k != "col_charge_id"})
        update["col_amount"] = "12.50"
        updated = self.db.update_row("Charge", update)
        stored = self._stored("Charge", {"charge_id": charge_id})
        self.check_case(
            ("UPDATE Charge", {"amount": "12.50"}),
            f"update_row returned {updated}; amount={stored and stored['amount']}",
            updated == 1 and stored["amount"] == "12.50",
            "expected one updated row with amount 12.50",
        )

        deleted = self.db.delete_row("Charge", {"pk_charge_id": str(charge_id)})
        remaining = self._stored("Charge", {"charge_id": charge_id})
        self.check_case(
            ("DELETE Charge", charge_id),
            f"delete_row returned {deleted}; row exists={remaining is not None}",
            deleted == 1 and remaining is None,
            "expected one deleted row",
        )

    # Rejected writes

    def test_write_errors(self):
        hotel = {"col_hotel_id": "98", "col_name": "Bad", "col_address": "x", "col_city": "y", "col_rating": "3"}
        self.addCleanup(self._force_delete, "Hotel", {"hotel_id": "98"})

        missing = dict(hotel)
        missing["col_name"] = ""
        exc = self._raises(ValueError, self.db.insert_row, "Hotel", missing)
        self.check_case(
            "INSERT Hotel with blank name",
            f"ValueError={exc is not None}",
            exc is not None,
            "expected a required-field error",
        )

        dup = dict(hotel)
        dup["col_hotel_id"] = "1"
        exc = self._raises(pymysql.err.IntegrityError, self.db.insert_row, "Hotel", dup)
        self.check_case(
            "INSERT Hotel with duplicate primary key",
            f"IntegrityError={exc is not None}",
            exc is not None,
            "expected a duplicate-key error",
        )

        exc = self._raises(
            pymysql.err.IntegrityError, self.db.insert_row, "Hotel_Area",
            {"col_hotel_id": "999", "col_area": "Lake"},
        )
        self.check_case(
            "INSERT Hotel_Area for a hotel that does not exist",
            f"IntegrityError={exc is not None}",
            exc is not None,
            "expected a foreign-key error",
        )

        exc = self._raises(pymysql.err.IntegrityError, self.db.delete_row, "Hotel", {"pk_hotel_id": "1"})
        still_there = self._stored("Hotel", {"hotel_id": "1"}) is not None
        self.check_case(
            "DELETE Hotel 1 (has rooms and reservations)",
            f"IntegrityError={exc is not None}; hotel still exists={still_there}",
            exc is not None and still_there,
            "expected the delete to be blocked by child rows",
        )

        bad_rating = dict(hotel)
        bad_rating["col_rating"] = "7"
        exc = self._raises(pymysql.MySQLError, self.db.insert_row, "Hotel", bad_rating)
        self.check_case(
            "INSERT Hotel with rating 7",
            f"error={exc is not None}",
            exc is not None,
            "expected the CHECK (rating BETWEEN 1 AND 6) constraint to reject it (MySQL 8.0.16+)",
        )

        deleted = self.db.delete_row("Amenity", {"pk_amenity_id": "12345"})
        self.check_case(
            "DELETE Amenity 12345 (missing)",
            f"delete_row returned {deleted}",
            deleted == 0,
            "expected zero rows deleted",
        )

        updated = self.db.update_row(
            "Amenity", {"pk_amenity_id": "12345", "col_amenity_id": "12345", "col_name": "Ghost"}
        )
        self.check_case(
            "UPDATE Amenity 12345 (missing)",
            f"update_row returned {updated}",
            updated == 0,
            "expected zero rows updated",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
    