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
