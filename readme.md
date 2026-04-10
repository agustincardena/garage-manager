# Garage Manager - Backend

Backend for a management system designed for automotive workshops, aimed at handling clients, vehicles, work orders, appointments, and reports.

## Description

The system centralizes workshop operations, enabling an organized workflow from vehicle intake to delivery and billing.

## Project Structure

garage-manager/
│
├── database/ # Database connection and configuration
├── services/ # Business logic (CRUD and operations)
│ ├── client_service.py
│ ├── vehicle_service.py
│ ├── order_service.py
│ ├── appointment_service.py
│ ├── expense_service.py
│ └── report_service.py
│
├── main.py # Entry point for testing
├── requirements.txt
└── README.md


## Technologies Used

- **Language:** Python 3  
- **Database:** SQLite  
- **Architecture:** Service Layer Pattern  

## Key Concepts

- **Separation of concerns:**  
  The `services/` directory contains all business logic, isolating it from persistence and the interface layer.

- **Data centralization:**  
  Database management is handled in a unified way to ensure data integrity.

- **Modularity:**  
  Each system entity has its own dedicated service.

- **Scalability:**  
  The backend is designed to be consumed by different user interface implementations, whether desktop environments or web applications.
