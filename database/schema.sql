PRAGMA foreign_keys = ON;

--------------------------------------------------
-- CLIENTS
--------------------------------------------------

CREATE TABLE clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    notes TEXT,
    created_at DATE DEFAULT CURRENT_DATE
);

--------------------------------------------------
-- VEHICLES
--------------------------------------------------

CREATE TABLE vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,

    brand TEXT,
    model TEXT,
    year INTEGER,

    plate TEXT UNIQUE,

    notes TEXT,

    FOREIGN KEY (client_id) REFERENCES clients(id)
);

--------------------------------------------------
-- ORDER STATUS
--------------------------------------------------

CREATE TABLE order_status (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

INSERT INTO order_status (id, name) VALUES
(1, 'pending'),
(2, 'scheduled'),
(3, 'in_progress'),
(4, 'waiting_parts'),
(5, 'completed'),
(6, 'cancelled');

--------------------------------------------------
-- ORDERS
--------------------------------------------------

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    vehicle_id INTEGER NOT NULL,
    status_id INTEGER NOT NULL,

    created_at DATE NOT NULL DEFAULT CURRENT_DATE,

    scheduled_date DATE,
    scheduled_time TEXT,

    started_at DATE,
    completed_at DATE,

    notes TEXT,

    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    FOREIGN KEY (status_id) REFERENCES order_status(id)
);

--------------------------------------------------
-- ORDER ITEMS (trabajos realizados)
--------------------------------------------------

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    order_id INTEGER NOT NULL,

    description TEXT NOT NULL,

    price REAL NOT NULL CHECK(price >= 0),
    cost REAL CHECK(cost >= 0),

    FOREIGN KEY (order_id) REFERENCES orders(id)
);

--------------------------------------------------
-- EXPENSES
--------------------------------------------------

CREATE TABLE expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    date DATE NOT NULL DEFAULT CURRENT_DATE,
    description TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount >= 0),
    category TEXT
);

--------------------------------------------------
-- APPOINTMENTS 
--------------------------------------------------

CREATE TABLE appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    vehicle_id INTEGER, 
    
    appointment_date DATE NOT NULL,
    appointment_time TEXT NOT NULL, 
    
    reason TEXT, 
    status TEXT DEFAULT 'scheduled', 
    
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);



--------------------------------------------------
-- INDEXES IMPORTANTES
--------------------------------------------------

CREATE INDEX idx_orders_vehicle
ON orders(vehicle_id);

CREATE INDEX idx_orders_scheduled_date
ON orders(scheduled_date);

CREATE INDEX idx_order_items_order
ON order_items(order_id);

CREATE INDEX idx_vehicles_client
ON vehicles(client_id);

CREATE INDEX idx_appointments_date
ON appointments(appointment_date);