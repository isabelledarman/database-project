-- ============================================
-- Hotel Database Schema
-- A hotel reservation system for COSC3510
-- ============================================

-- Clean slate: drop and recreate database
DROP DATABASE IF EXISTS project3510;
CREATE DATABASE project3510;
USE project3510;

-- ============================================
-- DDL (Table creation)
-- ============================================

CREATE TABLE Hotel(
    hotel_id INT NOT NULL,
    name VARCHAR(30) NOT NULL,
    address VARCHAR(30) NOT NULL,
    city VARCHAR(30) NOT NULL,
    rating INT NOT NULL,
    PRIMARY KEY(hotel_id),
    CHECK (rating BETWEEN 1 AND 6)
);

CREATE TABLE Area(
    area VARCHAR(20) NOT NULL,
    PRIMARY KEY(area)
);

CREATE TABLE Hotel_Area(
    hotel_id INT NOT NULL,
    area VARCHAR(20) NOT NULL,

    PRIMARY KEY(hotel_id, area),
    FOREIGN KEY (hotel_id) REFERENCES Hotel(hotel_id),
    FOREIGN KEY (area) REFERENCES Area(area)
);

CREATE TABLE Amenity(
    amenity_id INT NOT NULL,
    name VARCHAR(20) NOT NULL,
    PRIMARY KEY(amenity_id)
);

CREATE TABLE Hotel_Amenity(
    hotel_id INT NOT NULL,
    amenity_id INT NOT NULL,
    charge DECIMAL(10, 2) NOT NULL,

    PRIMARY KEY(hotel_id, amenity_id),
    FOREIGN KEY (hotel_id) REFERENCES Hotel(hotel_id),
    FOREIGN KEY (amenity_id) REFERENCES Amenity(amenity_id)
);

CREATE TABLE Conference_Room(
    hotel_id INT NOT NULL,
    conf_room_no INT NOT NULL,
    capacity INT NOT NULL,

    PRIMARY KEY(hotel_id, conf_room_no),
    FOREIGN KEY (hotel_id) REFERENCES Hotel(hotel_id)
);

CREATE TABLE Room_Location(
    location VARCHAR(20) NOT NULL,
    PRIMARY KEY(location)
);

CREATE TABLE Room_Bed(
    bed VARCHAR(20) NOT NULL,
    PRIMARY KEY(bed)
);

CREATE TABLE Room_Type(
    hotel_id INT NOT NULL,
    bed VARCHAR(20) NOT NULL,
    smoking BOOLEAN NOT NULL,
    `accessible` BOOLEAN NOT NULL,
    rate DECIMAL(10, 2) NOT NULL,

    PRIMARY KEY(hotel_id, bed, smoking, `accessible`),
    FOREIGN KEY (hotel_id) REFERENCES Hotel(hotel_id),
    FOREIGN KEY (bed) REFERENCES Room_Bed(bed)
);

CREATE TABLE Room(
    hotel_id INT NOT NULL,
    room_no INT NOT NULL,
    floor INT NOT NULL,
    location VARCHAR(20) NOT NULL,
    bed VARCHAR(20) NOT NULL,
    smoking BOOLEAN NOT NULL,
    `accessible` BOOLEAN NOT NULL,

    PRIMARY KEY(hotel_id, room_no),
    FOREIGN KEY (hotel_id, bed, smoking, `accessible`) REFERENCES Room_Type(hotel_id, bed, smoking, `accessible`),
    FOREIGN KEY (location) REFERENCES Room_Location(location)
);

CREATE TABLE Guest(
    user_id INT NOT NULL,
    phone VARCHAR(10) NOT NULL,
    name VARCHAR(30) NOT NULL,
    address VARCHAR(100) NOT NULL,

    PRIMARY KEY(user_id),
    UNIQUE(phone, name)
);

CREATE TABLE Credit_Card(
    card_no VARCHAR(19) NOT NULL,
    exp_date DATE NOT NULL,
    holder_name VARCHAR(30) NOT NULL,

    PRIMARY KEY(card_no)
);

CREATE TABLE Reservation(
    reservation_no INT NOT NULL AUTO_INCREMENT, 
    user_id INT NOT NULL,
    card_no VARCHAR(19) NOT NULL,
    booking_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL,
    cancel_date DATETIME,

    PRIMARY KEY(reservation_no),
    FOREIGN KEY (user_id) REFERENCES Guest(user_id),
    FOREIGN KEY (card_no) REFERENCES Credit_Card(card_no)
);

CREATE TABLE Reservation_Room(
    reservation_no INT NOT NULL,
    hotel_id INT NOT NULL,
    room_no INT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,

    PRIMARY KEY(reservation_no, hotel_id, room_no),
    FOREIGN KEY (reservation_no) REFERENCES Reservation(reservation_no),
    FOREIGN KEY (hotel_id, room_no) REFERENCES Room(hotel_id, room_no)
);

CREATE TABLE Charge(
    charge_id INT NOT NULL AUTO_INCREMENT,
    reservation_no INT NOT NULL,
    card_no VARCHAR(19) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    reason VARCHAR(50) NOT NULL,
    charge_type VARCHAR(15) NOT NULL,
    charge_date DATE NOT NULL,

    PRIMARY KEY(charge_id),
    FOREIGN KEY (reservation_no) REFERENCES Reservation(reservation_no),
    FOREIGN KEY (card_no) REFERENCES Credit_Card(card_no)
);

CREATE VIEW Bonus AS
    SELECT
        r.user_id,
        YEAR(r.booking_date) AS year,
        COUNT(*)             AS reservation_count
    FROM Reservation r
    WHERE r.status <> 'Cancelled' AND r.cancel_date IS NULL
    GROUP BY r.user_id, YEAR(r.booking_date)
    HAVING COUNT(*) >= 3;

-- ============================================
-- Sample data (inserted parents-first so foreign keys are satisfied)
-- Designed so that every query in logic.py returns rows.
-- See the "TEST INPUTS" block at the bottom of this file.
-- ============================================

INSERT INTO Hotel (hotel_id, name, address, city, rating) VALUES
    (1, 'Harborview Inn',   '12 Pier Street',    'Baltimore',      4),
    (2, 'Capitol Suites',   '500 K Street NW',   'Washington',     5),
    (3, 'Pinecrest Lodge',  '88 Ridge Road',     'Asheville',      3),
    (4, 'Seaside Resort',   '300 Boardwalk Ave', 'Virginia Beach', 4);

INSERT INTO Amenity (amenity_id, name) VALUES
    (1, 'WiFi'),
    (2, 'Breakfast'),
    (3, 'Parking'),
    (4, 'Pool Access'),
    (5, 'Spa'),
    (6, 'Airport Shuttle');

INSERT INTO Hotel_Amenity (hotel_id, amenity_id, charge) VALUES
    (1, 1,  0.00),
    (1, 2, 12.50),
    (1, 3, 25.00),
    (2, 1,  0.00),
    (2, 2, 22.00),
    (2, 3, 45.00),
    (2, 4,  0.00),
    (2, 5, 85.00),
    (2, 6, 30.00),
    (3, 1,  0.00),
    (3, 2,  9.50),
    (3, 3,  0.00),
    (3, 4, 15.00),
    (4, 1,  0.00),
    (4, 2, 18.00),
    (4, 3, 20.00),
    (4, 4,  0.00),
    (4, 5, 70.00);

INSERT INTO Conference_Room (hotel_id, conf_room_no, capacity) VALUES
    (1, 101,  40),
    (1, 102,  15),
    (2, 201, 120),
    (2, 202,  50),
    (2, 203,  20),
    (3,   1,  30),
    (4,  10,  80),
    (4,  11,  25);

INSERT INTO Room_Location (location) VALUES
    ('North'), 
    ('South'), 
    ('East'), 
    ('West'),
    ('North-East'), 
    ('North-West'), 
    ('South-East'), 
    ('South-West');

INSERT INTO Area (area) VALUES
    ('Ocean'), (
    'Mountain'), 
    ('Lake'), 
    ('River'), 
    ('Bay'), 
    ('Downtown');

INSERT INTO Hotel_Area (hotel_id, area) VALUES
    (1, 'Bay'),
    (1, 'Downtown'),
    (2, 'River'),
    (2, 'Downtown'),
    (3, 'Mountain'),
    (3, 'Lake'),
    (4, 'Ocean');


INSERT INTO Room_Bed (bed) VALUES
    ('Single'),
    ('Double'),
    ('Queen'),
    ('King');

INSERT INTO Room_Type (hotel_id, bed, smoking, `accessible`, rate) VALUES
    (1, 'Queen',  FALSE, FALSE, 129.00),
    (1, 'King',   FALSE, TRUE,  159.00),
    (1, 'Double', TRUE,  FALSE, 109.00),
    (1, 'Single', FALSE, FALSE,  89.00),
    (2, 'King',   FALSE, FALSE, 249.00),
    (2, 'Queen',  FALSE, TRUE,  229.00),
    (2, 'Single', FALSE, FALSE, 179.00),
    (3, 'Double', FALSE, FALSE,  99.00),
    (3, 'Queen',  TRUE,  FALSE,  89.00),
    (3, 'King',   FALSE, TRUE,  119.00),
    (4, 'King',   FALSE, FALSE, 199.00),
    (4, 'Queen',  FALSE, TRUE,  179.00),
    (4, 'Double', FALSE, FALSE, 139.00),
    (4, 'Queen',  TRUE,  FALSE, 149.00);

INSERT INTO Room (hotel_id, room_no, floor, location, bed, smoking, `accessible`) VALUES
    (1,  101,  1, 'North',     'King',   FALSE, TRUE),
    (1,  102,  1, 'North',     'Queen',  FALSE, FALSE),
    (1,  201,  2, 'East',   'Queen',  FALSE, FALSE),
    (1,  202,  2, 'East',   'Double', TRUE,  FALSE),
    (1,  203,  2, 'South',   'Single', FALSE, FALSE),
    (2,  301,  3, 'North-East',     'King',   FALSE, FALSE),
    (2,  302,  3, 'North-West',     'Queen',  FALSE, TRUE),
    (2, 1001, 10, 'South',     'Single', FALSE, FALSE),
    (2, 1002, 10, 'South-East',     'King',   FALSE, FALSE),
    (2, 1003, 10, 'South-West',     'Queen',  FALSE, TRUE),
    (3,   11,  1, 'West', 'Double', FALSE, FALSE),
    (3,   12,  1, 'South',     'Queen',  TRUE,  FALSE),
    (3,   21,  2, 'West', 'King',   FALSE, TRUE),
    (4,  110,  1, 'East',    'King',   FALSE, FALSE),
    (4,  120,  1, 'East',    'Queen',  FALSE, TRUE),
    (4,  210,  2, 'East',    'Double', FALSE, FALSE),
    (4,  220,  2, 'West',     'Queen',  TRUE,  FALSE);

INSERT INTO Guest (user_id, phone, name, address) VALUES
    (1, '4105550101', 'Maya Ortiz',  '14 Elm St, Baltimore, MD'),
    (2, '2025550142', 'Daniel Kim',  '901 Pennsylvania Ave, Washington, DC'),
    (3, '8285550177', 'Priya Nair',  '7 Laurel Ln, Asheville, NC'),
    (4, '3015550119', 'Tom Becker',  '220 Oak Dr, Rockville, MD'),
    (5, '7575550133', 'Lena Park',   '45 Bay Ct, Norfolk, VA'),
    (6, '9195550188', 'Sam Rivera',  '310 Oakwood Ave, Raleigh, NC');

INSERT INTO Credit_Card (card_no, exp_date, holder_name) VALUES
    ('4111111111111111', '2028-09-30', 'Maya Ortiz'),
    ('5500000000000004', '2027-04-30', 'Daniel Kim'),
    ('340000000000009',  '2029-01-31', 'Priya Nair'),
    ('6011000000000004', '2026-12-31', 'Tom Becker'),
    ('378282246310005',  '2029-06-30', 'Lena Park'),
    ('3530111333300000', '2028-03-31', 'Sam Rivera');

-- Reservation notes:
--   Maya (1): 3 non-cancelled bookings in 2026 (#1, #5, #6)  -> Bonus 2026
--   Daniel (2): 3 non-cancelled bookings in 2025 (#10-#12)   -> Bonus 2025
--   #3 and #9 are cancelled (cancelled rows are ignored by availability + Bonus)
--   #7 and #8 are 'Confirmed' with a check-in date already in the past -> no-shows
--   #2, #4, #5 are Confirmed with future check-in -> NOT no-shows
INSERT INTO Reservation (reservation_no, user_id, card_no, booking_date, status, cancel_date) VALUES
    ( 1, 1, '4111111111111111', '2026-09-01', 'Completed', NULL),
    ( 2, 2, '5500000000000004', '2026-10-10', 'Confirmed', NULL),
    ( 3, 3, '340000000000009',  '2026-10-20', 'Cancelled', '2026-11-19 10:00:00'),    
    ( 4, 3, '340000000000009',  '2026-11-01', 'Confirmed', NULL),
    ( 5, 1, '4111111111111111', '2026-11-05', 'Confirmed', NULL),
    ( 6, 1, '4111111111111111', '2026-06-15', 'Completed', NULL),
    ( 7, 4, '6011000000000004', '2026-09-25', 'Confirmed', NULL),
    ( 8, 5, '378282246310005',  '2026-10-01', 'Confirmed', NULL),
    ( 9, 6, '3530111333300000', '2026-10-15', 'Cancelled', '2026-10-30 09:10:00'),
    (10, 2, '5500000000000004', '2025-02-10', 'Completed', NULL),
    (11, 2, '5500000000000004', '2025-06-05', 'Completed', NULL),
    (12, 2, '5500000000000004', '2025-11-20', 'Completed', NULL);

INSERT INTO Reservation_Room (reservation_no, hotel_id, room_no, check_in, check_out) VALUES
    ( 1, 1,  201, '2026-09-12', '2026-09-15'),
    ( 2, 2,  301, '2026-12-20', '2026-12-23'),
    ( 2, 2,  302, '2026-12-20', '2026-12-23'),
    ( 3, 3,   21, '2026-11-20', '2026-11-22'),
    ( 4, 3,   11, '2026-12-01', '2026-12-05'),
    ( 5, 1,  102, '2026-12-28', '2027-01-02'),
    ( 6, 4,  110, '2026-07-04', '2026-07-07'),
    ( 7, 1,  202, '2026-10-05', '2026-10-08'),
    ( 8, 4,  120, '2026-10-18', '2026-10-20'),
    ( 8, 4,  210, '2026-10-18', '2026-10-20'),
    ( 9, 2, 1001, '2026-11-25', '2026-11-28'),
    (10, 2, 1002, '2025-03-01', '2025-03-03'),
    (11, 3,   21, '2025-06-20', '2025-06-22'),
    (12, 1,  101, '2025-12-05', '2025-12-07');

-- charge_id is AUTO_INCREMENT, so it is left out of the column list
INSERT INTO Charge (reservation_no, card_no, amount, reason, charge_type, charge_date) VALUES
    ( 1, '4111111111111111',  387.00, 'Room 201, 3 nights',            'Room',    '2026-09-15'),
    ( 1, '4111111111111111',   37.50, 'Breakfast x3',                  'Amenity', '2026-09-15'),
    ( 2, '5500000000000004', 1434.00, 'Rooms 301 and 302, 3 nights',   'Room',    '2026-10-10'),
    ( 3, '340000000000009', 23.80, 'Late cancellation: 20% of first night', 'Fee', '2026-11-19'),    
    ( 4, '340000000000009',   396.00, 'Room 11, 4 nights',             'Room',    '2026-11-01'),
    ( 5, '4111111111111111',  645.00, 'Room 102, 5 nights',            'Room',    '2026-11-05'),
    ( 6, '4111111111111111',  597.00, 'Room 110, 3 nights',            'Room',    '2026-07-07'),
    ( 6, '4111111111111111',   60.00, 'Parking x3',                    'Amenity', '2026-07-07'),
    ( 7, '6011000000000004',  327.00, 'Room 202, 3 nights',            'Room',    '2026-09-25'),
    ( 8, '378282246310005',   636.00, 'Rooms 120 and 210, 2 nights',   'Room',    '2026-10-01'),
    (10, '5500000000000004',  498.00, 'Room 1002, 2 nights',           'Room',    '2025-03-03'),
    (11, '5500000000000004',  238.00, 'Room 21, 2 nights',             'Room',    '2025-06-22'),
    (12, '5500000000000004',  318.00, 'Room 101, 2 nights',            'Room',    '2025-12-07'),
    (12, '5500000000000004',   25.00, 'Breakfast x2',                  'Amenity', '2025-12-07');