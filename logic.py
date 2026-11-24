"""Database layer: every SQL query in the project lives in this file.

Both front-ends use this same class:
  - view.py  (web app, Flask)
  - main.py  (command-line app, no web server)
"""

import datetime
import pymysql

# Every table in the schema, parents first (matches the order in schema.sql)
TABLES = [
    'Hotel', 'Area', 'Hotel_Area', 'Amenity', 'Hotel_Amenity', 'Conference_Room',
    'Room_Location', 'Room_Bed', 'Room_Type', 'Room',
    'Guest', 'Credit_Card', 'Reservation', 'Reservation_Room',
    'Charge',
]


class Database(object):
    """Database object to handle all DB operations"""

    def __init__(self, opts):
        """Initialize and connect to the database"""
        self.opts = opts
        self.__connect()

    def __connect(self):
        """Establish the MySQL connection"""
        self.conn = pymysql.connect(
            host=self.opts.DB_HOST,
            user=self.opts.DB_USER,
            password=self.opts.DB_PASSWORD,
            database=self.opts.DB_NAME,
            unix_socket='/tmp/mysql.sock',
            # Read-only usage: autocommit stops a long-lived connection from
            # showing a stale snapshot of the data on later page loads.
            autocommit=True
        )

    def close(self):
        """Close the connection when the program ends"""
        self.conn.close()

    def _query(self, sql, params=()):
        """Run a SELECT and return every row as a dict.

        Always pass user-supplied values through `params` (%s placeholders)
        so they are escaped by the driver and cannot cause SQL injection.
        """
        cur = self.conn.cursor(pymysql.cursors.DictCursor)
        try:
            cur.execute(sql, params)
            return cur.fetchall()
        finally:
            cur.close()

    # ---------- Read operations ----------

    def get_all_data(self):
        """Fetch everything in the database, organized for display.

        Returns a dict with these keys:
          hotels        each hotel with its amenities, conference_rooms and rooms
          reservations  each reservation with guest, card (last 4 only), rooms, charges, total
          guests        each guest with their reservation count
          bonuses       each bonus mailing with the guest's name
          counts        {table name: number of rows}, for every table
        """
        # --- Hotels, with everything that belongs to each one ---
        hotels = self._query('SELECT hotel_id, name, address, city, rating '
                             'FROM Hotel ORDER BY hotel_id')
        for hotel in hotels:
            hid = hotel['hotel_id']
            hotel['amenities'] = self._query('''
                SELECT a.name, ha.charge
                FROM Hotel_Amenity ha
                JOIN Amenity a ON a.amenity_id = ha.amenity_id
                WHERE ha.hotel_id = %s
                ORDER BY a.name''', (hid,))
            hotel['conference_rooms'] = self._query('''
                SELECT conf_room_no, capacity
                FROM Conference_Room
                WHERE hotel_id = %s
                ORDER BY conf_room_no''', (hid,))
            hotel['rooms'] = self._query('''
                SELECT r.room_no, r.floor, r.location, r.bed,
                       r.smoking, r.accessible, rt.rate
                FROM Room r
                JOIN Room_Type rt
                  ON rt.hotel_id = r.hotel_id AND rt.bed = r.bed
                 AND rt.smoking = r.smoking   AND rt.accessible = r.accessible
                WHERE r.hotel_id = %s
                ORDER BY r.room_no''', (hid,))

        # --- Reservations, with rooms and charges ---
        reservations = self._query('''
            SELECT res.reservation_no, res.booking_date, res.status, res.cancel_date,
                   g.name AS guest_name, g.phone AS guest_phone,
                   cc.holder_name, RIGHT(cc.card_no, 4) AS card_last4
            FROM Reservation res
            JOIN Guest g        ON g.user_id = res.user_id
            JOIN Credit_Card cc ON cc.card_no = res.card_no
            ORDER BY res.reservation_no''')
        for res in reservations:
            rno = res['reservation_no']
            res['rooms'] = self._query('''
                SELECT h.name AS hotel_name, rr.room_no, rr.check_in, rr.check_out,
                       DATEDIFF(rr.check_out, rr.check_in) AS nights
                FROM Reservation_Room rr
                JOIN Hotel h ON h.hotel_id = rr.hotel_id
                WHERE rr.reservation_no = %s
                ORDER BY rr.room_no''', (rno,))
            res['charges'] = self._query('''
                SELECT charge_id, amount, reason, charge_type, charge_date
                FROM Charge
                WHERE reservation_no = %s
                ORDER BY charge_date, charge_id''', (rno,))
            res['total'] = sum(c['amount'] for c in res['charges'])

        # --- Guests and bonuses ---
        guests = self._query('''
            SELECT g.user_id, g.name, g.phone, g.address,
                   COUNT(res.reservation_no) AS reservation_count
            FROM Guest g
            LEFT JOIN Reservation res ON res.user_id = g.user_id
            GROUP BY g.user_id, g.name, g.phone, g.address
            ORDER BY g.user_id''')
        bonuses = self._query('''
            SELECT g.name AS guest_name, b.year
            FROM Bonus b
            JOIN Guest g ON g.user_id = b.user_id
            ORDER BY b.year, g.name''')

        # --- Row count of every table (names come from the TABLES constant, never from users) ---
        counts = {}
        for table in TABLES:
            counts[table] = self._query(f'SELECT COUNT(*) AS n FROM {table}')[0]['n']

        return {
            'hotels': hotels,
            'reservations': reservations,
            'guests': guests,
            'bonuses': bonuses,
            'counts': counts,
        }

    def display_all(self):
        """Print everything in the database to the console, grouped by topic."""
        data = self.get_all_data()
        yes_no = lambda value: 'yes' if value else '-'
        line = '=' * 64

        print(line)
        print('HOTELS')
        print(line)
        for h in data['hotels']:
            print(f"\n{h['name']}  ({'*' * h['rating']})  {h['address']}, {h['city']}")
            print('  Rooms:')
            for r in h['rooms']:
                print(f"    #{r['room_no']:<5} floor {r['floor']:<3} {r['location']:<14} "
                      f"{r['bed']:<7} smoking: {yes_no(r['smoking']):<4} "
                      f"accessible: {yes_no(r['accessible']):<4} ${r['rate']:>7.2f}/night")
            print('  Amenities:')
            for a in h['amenities']:
                price = 'free' if a['charge'] == 0 else f"${a['charge']:.2f}"
                print(f"    {a['name']:<16} {price}")
            print('  Conference rooms:')
            for c in h['conference_rooms']:
                print(f"    Room {c['conf_room_no']:<5} seats {c['capacity']}")

        print(f"\n{line}\nRESERVATIONS\n{line}")
        for res in data['reservations']:
            print(f"\n#{res['reservation_no']}  {res['status']}  "
                  f"booked {res['booking_date']}  guest: {res['guest_name']}  "
                  f"card ending {res['card_last4']}")
            if res['cancel_date']:
                print(f"  cancelled {res['cancel_date']}")
            for room in res['rooms']:
                print(f"  {room['hotel_name']}, room {room['room_no']}: "
                      f"{room['check_in']} to {room['check_out']} ({room['nights']} nights)")
            for c in res['charges']:
                print(f"  charge #{c['charge_id']}  {c['charge_date']}  "
                      f"{c['charge_type']:<8} ${c['amount']:>8.2f}  {c['reason']}")
            print(f"  total charged: ${res['total']:.2f}")

        print(f"\n{line}\nGUESTS\n{line}")
        for g in data['guests']:
            print(f"  {g['name']:<14} {g['phone']}  {g['address']}  "
                  f"({g['reservation_count']} reservations)")

        print(f"\n{line}\nBONUS MAILINGS\n{line}")
        for b in data['bonuses']:
            print(f"  {b['year']}  {b['guest_name']:<14}")

        print(f"\n{line}\nROW COUNTS\n{line}")
        for table, n in data['counts'].items():
            print(f"  {table:<18} {n}")

    def get_cities(self):
        return self._query('SELECT DISTINCT city FROM Hotel ORDER BY city')

    def get_beds(self):
            return self._query('SELECT bed FROM Room_Bed ORDER BY bed')

    # Query 1
    def available_rooms(self, city, bed, smoking, check_in, check_out):
        return self._query('''
            SELECT h.name as hotel, r.room_no AS room, r.floor, r.location, r.bed, r.accessible, rt.rate
            FROM Room r
            JOIN Hotel h ON h.hotel_id = r.hotel_id
            JOIN Room_Type rt ON rt.hotel_id = r.hotel_id AND rt.bed = r.bed AND rt.smoking = r.smoking AND rt.accessible = r.accessible
            WHERE h.city = %s AND r.bed = %s and r.smoking = %s
                AND NOT EXISTS(
                    SELECT 1
                    FROM Reservation_Room rr
                    JOIN Reservation res on res.reservation_no = rr.reservation_no
                    WHERE rr.hotel_id = r.hotel_id AND rr.room_no = r.room_no AND res.status <> 'Cancelled' AND rr.check_in < %s AND rr.check_out > %s
                )
            ORDER BY h.name, r.room_no
        ''',
        (city, bed, smoking, check_out, check_in))

    # Query 2
    def available_accessible_rooms(self, city, check_in, check_out):
        return self._query('''
            SELECT h.name AS hotel, r.room_no AS room, r.floor, r.location, r.bed, IF(r.smoking, 'Smoking', 'Non-smoking') AS smoking, rt.rate
            FROM Room r
            JOIN Hotel h on h.hotel_id = r.hotel_id
            JOIN Room_Type rt on rt.hotel_id = r.hotel_id AND rt.bed = r.bed AND rt.smoking = r.smoking AND rt.accessible = r.accessible
            WHERE h.city = %s AND r.accessible = True
                AND NOT EXISTS(
                    SELECT 1
                    FROM Reservation_Room rr
                    JOIN Reservation res on res.reservation_no = rr.reservation_no
                    WHERE rr.hotel_id = r.hotel_id and rr.room_no = r.room_no AND res.status <> 'Cancelled' AND rr.check_in < %s AND rr.check_out > %s
                )
            ORDER BY h.name, r.room_no
        ''',
        (city, check_out, check_in))

    # Query 3
    def mountain_or_ocean(self, city=None):
        return self._query('''
            SELECT DISTINCT h.city, h.name AS name, h.address, GROUP_CONCAT(ha.area ORDER BY ha.area SEPARATOR ', ') AS next_to
            FROM Hotel h
            JOIN Hotel_Area ha ON ha.hotel_id = h.hotel_id
            WHERE ha.area IN ('Mountain', 'Ocean')
                AND (%s IS NULL OR h.city = %s)
            GROUP BY h.hotel_id, h.city, h.name, h.address
            ORDER BY h.city, h.name
        ''',
        (city or None, city or None))

    # Query 4
    def reservations_by_person(self, name, phone_number):
        return self._query('''
            SELECT g.user_id, g.name, g.phone, r.reservation_no, r.status, r.booking_date,
                    h.name AS hotel, h.city, rr.room_no AS room, rr.check_in, rr.check_out
            FROM Guest g
            JOIN Reservation r ON r.user_id = g.user_id
            JOIN Reservation_Room rr on rr.reservation_no = r.reservation_no
            JOIN Hotel h on h.hotel_id = rr.hotel_id
            WHERE g.name = %s AND g.phone = %s
            ORDER BY rr.check_in
        ''',
        (name, phone_number))

    # Query 5
    def guest_charges_list(self, name, phone_number):
        return self._query('''
            SELECT c.charge_id, c.reservation_no, c.card_no, c.charge_type,
                c.reason, c.amount, c.charge_date
            FROM Guest g
            JOIN Reservation r ON r.user_id = g.user_id
            JOIN Charge c ON c.reservation_no = r.reservation_no
            WHERE g.name = %s AND g.phone = %s
            ORDER BY c.charge_date, c.charge_id
        ''',
        (name, phone_number))

    # Query 6
    def no_show_reservations(self):
        return self._query('''
            SELECT r.reservation_no, r.booking_date, r.status,
                g.user_id, g.name AS guest_name, g.phone,
                h.hotel_id, h.name AS hotel_name,
                rr.room_no, rr.check_in, rr.check_out
            FROM Reservation r
            JOIN Guest g ON g.user_id = r.user_id
            JOIN Reservation_Room rr ON rr.reservation_no = r.reservation_no
            JOIN Hotel h ON h.hotel_id = rr.hotel_id
            WHERE r.cancel_date IS NULL AND r.status = 'Confirmed' AND TIMESTAMP(rr.check_in, '15:00:00') < NOW()
            ORDER BY rr.check_in, r.reservation_no, rr.room_no
        ''')

    # Query 6 helper - could also be automated, but it's outside the scope of the project
    def charge_no_show_fees(self):
        return self._execute('''
            INSERT INTO Charge (reservation_no, card_no, amount, reason, charge_type, charge_date)
            SELECT r.reservation_no, r.card_no, ROUND(SUM(0.20*rt.rate), 2), 'No-show: 20%% of first night', 'Fee', CURDATE()
            FROM Reservation r
            JOIN Reservation_Room rr on rr.reservation_no = r.reservation_no
            JOIN Room rm on rm.hotel_id = rr.hotel_id AND rm.room_no = rr.room_no
            JOIN Room_Type rt on rt.hotel_id = rm.hotel_id AND rt.bed = rm.bed AND rt.smoking = rm.smoking AND rt.`accessible` = rm.`accessible`
            WHERE r.cancel_date IS NULL and r.status = 'Confirmed' AND NOT EXISTS (SELECT 1 FROM Charge c where c.reservation_no = r.reservation_no and c.charge_type = 'Fee')
            GROUP BY r.reservation_no, r.card_no
            HAVING TIMESTAMP(MIN(rr.check_in), '15:00:00') < NOW()
        ''')
    
    # Query 7
    def bonus_list(self):
        return self._query('''
            SELECT g.name, g.phone, b.year, 'Will Receive Bonus' as status
            FROM Bonus b
            JOIN Guest g ON g.user_id = b.user_id
            ORDER BY b.year, g.name
        ''')

    # Query 8 - "universal relation" formatting/returning all reservation info
    def reservation_details(self):
        return self._query('''
            SELECT
                -- reservation
                r.reservation_no, r.booking_date, r.status, r.cancel_date,
                -- guest
                g.user_id, g.name AS guest_name, g.phone AS guest_phone, g.address AS guest_address,
                -- hotel branch
                h.hotel_id, h.name AS hotel_name, h.address AS hotel_address, h.city AS hotel_city, h.rating AS hotel_rating,
                (SELECT GROUP_CONCAT(ha.area ORDER BY ha.area SEPARATOR ', ')
                    FROM Hotel_Area ha
                WHERE ha.hotel_id = h.hotel_id) AS hotel_areas,
                (SELECT GROUP_CONCAT(
                    CONCAT(a.name, ' (',
                        IF(ha.charge = 0, 'free', CONCAT('$', ha.charge)),
                            ')')
                        ORDER BY a.name SEPARATOR ', ')
                    FROM Hotel_Amenity ha
                    JOIN Amenity a ON a.amenity_id = ha.amenity_id
                WHERE ha.hotel_id = h.hotel_id) AS amenities,
                (SELECT GROUP_CONCAT(
                    CONCAT('Room ', cr.conf_room_no,
                        ' (', cr.capacity, ' seats)')
                    ORDER BY cr.conf_room_no SEPARATOR ', ')
                FROM Conference_Room cr
                WHERE cr.hotel_id = h.hotel_id) AS conference_rooms,
                -- room and room type
                rm.room_no, rm.floor, rm.location, rt.bed, rt.smoking, rt.`accessible`,
                -- stay and cost
                rr.check_in, rr.check_out, DATEDIFF(rr.check_out, rr.check_in) AS nights,
                rt.rate AS rate_per_night, DATEDIFF(rr.check_out, rr.check_in) * rt.rate AS room_total
            FROM Reservation r
            JOIN Guest g ON g.user_id = r.user_id
            JOIN Reservation_Room rr ON rr.reservation_no = r.reservation_no
            JOIN Room rm ON rm.hotel_id = rr.hotel_id AND rm.room_no  = rr.room_no
            JOIN Room_Type rt ON rt.hotel_id = rm.hotel_id AND rt.bed = rm.bed AND rt.smoking = rm.smoking AND rt.`accessible` = rm.`accessible`
            JOIN Hotel h ON h.hotel_id = rm.hotel_id
            ORDER BY r.reservation_no, rr.room_no
        ''')
    
    # ---------- Generic add / edit / delete for ANY table ----------
    # Column names come from information_schema and table names are checked
    # against TABLES, so only values (never identifiers) come from the user,
    # and values always go through %s placeholders.

    def _check_table(self, table):
        if table not in TABLES:
            raise ValueError(f'Unknown table: {table}')

    def _columns(self, table):
        """Describe a table's columns: name, input kind, nullable, auto-increment, primary key."""
        self._check_table(table)
        rows = self._query('''
            SELECT COLUMN_NAME AS name, DATA_TYPE AS data_type, COLUMN_TYPE AS column_type,
                   IS_NULLABLE AS nullable, COLUMN_KEY AS col_key, EXTRA AS extra,
                   CHARACTER_MAXIMUM_LENGTH AS maxlen
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION''', (table,))
        cols = []
        for r in rows:
            dt = r['data_type'].lower()
            if r['column_type'].lower().startswith('tinyint(1)'):
                kind = 'bool'
            elif dt in ('tinyint', 'smallint', 'mediumint', 'int', 'bigint'):
                kind = 'int'
            elif dt in ('decimal', 'float', 'double'):
                kind = 'decimal'
            elif dt == 'date':
                kind = 'date'
            elif dt in ('datetime', 'timestamp'):
                kind = 'datetime'
            else:
                kind = 'text'
            cols.append({
                'name': r['name'],
                'kind': kind,
                'nullable': r['nullable'] == 'YES',
                'auto': 'auto_increment' in (r['extra'] or '').lower(),
                'pk': r['col_key'] == 'PRI',
                'maxlen': r['maxlen'],
            })
        return cols

    @staticmethod
    def _to_form(col, value):
        """Format a DB value as the string an HTML input expects."""
        if value is None:
            return ''
        if col['kind'] == 'bool':
            return '1' if value else '0'
        if isinstance(value, datetime.datetime):
            return value.strftime('%Y-%m-%dT%H:%M')
        if isinstance(value, datetime.date):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _coerce(col, raw):
        raw = (raw or '').strip()
        if raw == '':
            if col['nullable'] or col['auto']:
                return None
            raise ValueError(f"{col['name']} is required.")
        if col['kind'] == 'datetime':
            raw = raw.replace('T', ' ')
        return raw

    def _execute(self, sql, params=(), return_id=False):
        cur = self.conn.cursor()
        try:
            cur.execute(sql, params)
            return cur.lastrowid if return_id else cur.rowcount
        finally:
            cur.close()

    @staticmethod
    def _pk_where(cols, form):
        pk = [c for c in cols if c['pk']]
        where = ' AND '.join(f"`{c['name']}` = %s" for c in pk)
        return where, [form.get('pk_' + c['name'], '') for c in pk]

    def get_manage_data(self):
        tables = []
        for table in TABLES:
            cols = self._columns(table)
            order = ', '.join(f"`{c['name']}`" for c in cols if c['pk'])
            rows = self._query(f'SELECT * FROM `{table}` ORDER BY {order}')
            tables.append({
                'name': table,
                'columns': cols,
                'rows': [{c['name']: self._to_form(c, r[c['name']]) for c in cols} for r in rows],
            })
        return tables

    def _check_room_free(self, form):
        check_in = form.get('col_check_in', '').strip()
        check_out = form.get('col_check_out', '').strip()
        if check_in and check_out and check_out <= check_in: # ISO dates compare correctly as text
            raise ValueError('Check-out must be after check-in.')
        clash = self._query('''
            SELECT rr.reservation_no
            FROM Reservation_Room rr
            JOIN Reservation res ON res.reservation_no = rr.reservation_no
            WHERE rr.hotel_id = %s AND rr.room_no = %s
                AND res.status <> 'Cancelled'
                AND rr.check_in < %s AND rr.check_out > %s
                -- skip the row being edited (<=> is equals that also works with NULL)
                AND NOT (rr.reservation_no <=> %s AND rr.hotel_id <=> %s AND rr.room_no <=> %s)
        ''', (form.get('col_hotel_id'), form.get('col_room_no'), check_out, check_in,
              form.get('pk_reservation_no'), form.get('pk_hotel_id'), form.get('pk_room_no')))
        if clash:
            raise ValueError(f"That room is already booked for some of those nights "
                             f"(reservation #{clash[0]['reservation_no']}).")

    # Check whether guest will receive bonus after inserting new reservation row
    def bonus_for_reservation(self, reservation_no):
        rows = self._query('''
            SELECT g.name
            FROM Reservation r
            JOIN Bonus b on b.user_id = r.user_id AND b.year = YEAR(r.booking_date)
            JOIN Guest g on g.user_id = r.user_id
            WHERE r.reservation_no = %s
        ''', (reservation_no,))
        return rows[0]['name'] if rows else None

    @staticmethod
    def _sync_cancellation(form):
        form = dict(form.items())   # the submitted form is read-only, so work on a copy
        cancelled = form.get('col_status', '').strip() == 'Cancelled'
        has_date = form.get('col_cancel_date', '').strip() != ''
        if cancelled and not has_date:
            form['col_cancel_date'] = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M')
        elif has_date and not cancelled:
            form['col_status'] = 'Cancelled'
        return form

    def _charge_late_cancellation(self, reservation_no):
        return self._execute('''
            INSERT INTO Charge (reservation_no, card_no, amount, reason, charge_type, charge_date)
            SELECT r.reservation_no, r.card_no, ROUND(SUM(0.20 * rt.rate), 2),
                   'Late cancellation: 20%% of first night', 'Fee', DATE(r.cancel_date)
            FROM Reservation r
            JOIN Reservation_Room rr ON rr.reservation_no = r.reservation_no
            JOIN Room rm ON rm.hotel_id = rr.hotel_id AND rm.room_no = rr.room_no
            JOIN Room_Type rt ON rt.hotel_id = rm.hotel_id AND rt.bed = rm.bed
                             AND rt.smoking = rm.smoking AND rt.`accessible` = rm.`accessible`
            WHERE r.reservation_no = %s
            GROUP BY r.reservation_no, r.card_no, r.cancel_date
            HAVING r.cancel_date > TIMESTAMP(MIN(rr.check_in), '15:00:00') - INTERVAL 48 HOUR
        ''', (reservation_no,))
    

    def insert_row(self, table, form):
        if table == 'Reservation_Room':
            self._check_room_free(form)
        elif table == 'Reservation':
            form = self._sync_cancellation(form)
        cols = self._columns(table)
        names, vals = [], []
        for c in cols:
            raw = form.get('col_' + c['name'], '')
            if c['auto'] and raw.strip() == '':
                continue
            names.append(f"`{c['name']}`")
            vals.append(self._coerce(c, raw))
        sql = (f"INSERT INTO `{table}` ({', '.join(names)}) "
               f"VALUES ({', '.join(['%s'] * len(vals))})")
        return self._execute(sql, vals, return_id=True)

    def update_row(self, table, form):
        newly_cancelled = False
        if table == 'Reservation_Room':
            self._check_room_free(form)
        elif table == 'Reservation':
            form = self._sync_cancellation(form)
            old = self._query('SELECT status FROM Reservation WHERE reservation_no = %s',
                              (form.get('pk_reservation_no'),))
            newly_cancelled = (bool(old) and old[0]['status'] != 'Cancelled'
                               and form.get('col_status') == 'Cancelled')
        cols = self._columns(table)
        editable = [c for c in cols if not c['auto']]
        sets = ', '.join(f"`{c['name']}` = %s" for c in editable)
        vals = [self._coerce(c, form.get('col_' + c['name'], '')) for c in editable]
        where, pk_vals = self._pk_where(cols, form)

        self.conn.begin()
        try:
            n = self._execute(f'UPDATE `{table}` SET {sets} WHERE {where}', vals + pk_vals)
            if newly_cancelled:
                self._charge_late_cancellation(form.get('pk_reservation_no'))
            self.conn.commit()
            return n
        except Exception:
            self.conn.rollback()
            raise

    def delete_row(self, table, form):
        cols = self._columns(table)
        where, pk_vals = self._pk_where(cols, form)
        return self._execute(f'DELETE FROM `{table}` WHERE {where}', pk_vals) 