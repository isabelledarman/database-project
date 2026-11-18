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
    PRIMARY KEY(hotel_id)
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
    reservation_no INT NOT NULL,
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
-- ============================================

INSERT INTO Hotel (hotel_id, name, address, city, rating) VALUES
    (1, 'Harborview Inn',   '12 Pier Street',    'Baltimore', 4),
    (2, 'Capitol Suites',   '500 K Street NW',   'Washington', 5),
    (3, 'Pinecrest Lodge',  '88 Ridge Road',     'Asheville', 3);

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
    (3, 4, 15.00);

INSERT INTO Conference_Room (hotel_id, conf_room_no, capacity) VALUES
    (1, 101,  40),
    (1, 102,  15),
    (2, 201, 120),
    (2, 202,  50),
    (2, 203,  20),
    (3,   1,  30);

INSERT INTO Room_Location (location) VALUES
    ('Harbor View'),
    ('City View'),
    ('Courtyard'),
    ('Pool Side'),
    ('Mountain View');

INSERT INTO Room_Bed (bed) VALUES
    ('Single'),
    ('Double'),
    ('Queen'),
    ('King');

INSERT INTO Room_Type (hotel_id, bed, smoking, `accessible`, rate) VALUES
    (1, 'Queen',  FALSE, FALSE, 129.00),
    (1, 'King',   FALSE, TRUE,  159.00),
    (1, 'Double', TRUE,  FALSE, 109.00),
    (2, 'King',   FALSE, FALSE, 249.00),
    (2, 'Queen',  FALSE, TRUE,  229.00),
    (2, 'Single', FALSE, FALSE, 179.00),
    (3, 'Double', FALSE, FALSE,  99.00),
    (3, 'Queen',  TRUE,  FALSE,  89.00),
    (3, 'King',   FALSE, TRUE,  119.00);

INSERT INTO Room (hotel_id, room_no, floor, location, bed, smoking, `accessible`) VALUES
    (1,  101,  1, 'Courtyard',     'King',   FALSE, TRUE),
    (1,  102,  1, 'Courtyard',     'Queen',  FALSE, FALSE),
    (1,  201,  2, 'Harbor View',   'Queen',  FALSE, FALSE),
    (1,  202,  2, 'Harbor View',   'Double', TRUE,  FALSE),
    (2,  301,  3, 'City View',     'King',   FALSE, FALSE),
    (2,  302,  3, 'City View',     'Queen',  FALSE, TRUE),
    (2, 1001, 10, 'City View',     'Single', FALSE, FALSE),
    (2, 1002, 10, 'City View',     'King',   FALSE, FALSE),
    (3,   11,  1, 'Mountain View', 'Double', FALSE, FALSE),
    (3,   12,  1, 'Pool Side',     'Queen',  TRUE,  FALSE),
    (3,   21,  2, 'Mountain View', 'King',   FALSE, TRUE);

INSERT INTO Guest (user_id, phone, name, address) VALUES
    (1, '4105550101', 'Maya Ortiz',  '14 Elm St, Baltimore, MD'),
    (2, '2025550142', 'Daniel Kim',  '901 Pennsylvania Ave, Washington, DC'),
    (3, '8285550177', 'Priya Nair',  '7 Laurel Ln, Asheville, NC'),
    (4, '3015550119', 'Tom Becker',  '220 Oak Dr, Rockville, MD');

INSERT INTO Credit_Card (card_no, exp_date, holder_name) VALUES
    ('4111111111111111', '2028-09-30', 'Maya Ortiz'),
    ('5500000000000004', '2027-04-30', 'Daniel Kim'),
    ('340000000000009',  '2029-01-31', 'Priya Nair'),
    ('6011000000000004', '2026-12-31', 'Tom Becker');

INSERT INTO Reservation (reservation_no, user_id, card_no, booking_date, status, cancel_date) VALUES
    (1, 1, '4111111111111111', '2026-09-01', 'Completed', NULL),
    (2, 2, '5500000000000004', '2026-10-10', 'Confirmed', NULL),
    (3, 3, '340000000000009',  '2026-10-20', 'Cancelled', '2026-11-02 14:35:00'),
    (4, 3, '340000000000009',  '2026-11-01', 'Confirmed', NULL),
    (5, 1, '4111111111111111', '2026-11-05', 'Confirmed', NULL);

INSERT INTO Reservation_Room (reservation_no, hotel_id, room_no, check_in, check_out) VALUES
    (1, 1, 201, '2026-09-12', '2026-09-15'),
    (2, 2, 301, '2026-12-20', '2026-12-23'),
    (2, 2, 302, '2026-12-20', '2026-12-23'),
    (3, 3,  21, '2026-11-20', '2026-11-22'),
    (4, 3,  11, '2026-12-01', '2026-12-05'),
    (5, 1, 102, '2026-12-28', '2027-01-02');

-- charge_id is AUTO_INCREMENT, so it is left out of the column list
INSERT INTO Charge (reservation_no, card_no, amount, reason, charge_type, charge_date) VALUES
    (1, '4111111111111111',  387.00, 'Room 201, 3 nights',            'Room',    '2026-09-15'),
    (1, '4111111111111111',   37.50, 'Breakfast x3',                  'Amenity', '2026-09-15'),
    (2, '5500000000000004', 1434.00, 'Rooms 301 and 302, 3 nights',   'Room',    '2026-10-10'),
    (3, '340000000000009',    50.00, 'Late cancellation fee',         'Fee',     '2026-11-02'),
    (4, '340000000000009',   396.00, 'Room 11, 4 nights',             'Room',    '2026-11-01'),
    (5, '4111111111111111',  645.00, 'Room 102, 5 nights',            'Room',    '2026-11-05');