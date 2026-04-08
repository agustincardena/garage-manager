**Garage Manager - Backend**
Backend de un sistema de gestion para talleres mecanicos diseñado para administrar clientes, vehiculos, ordenes de trabajo, turnos y reportes.

**Descripcion**
El sistema centraliza la operatividad de un taller mecanico, permitiendo un flujo de trabajo organizado desde la recepcion del vehiculo hasta la entrega y facturacion.

**Estructura del proyecto**
garage-manager/
│
├── database/          # Conexion y configuracion de la base de datos
├── services/          # Logica de negocio (CRUD y operaciones)
│   ├── client_service.py
│   ├── vehicle_service.py
│   ├── order_service.py
│   ├── appointment_service.py
│   ├── expense_service.py
│   └── report_service.py
│
├── main.py            # Punto de entrada para testing
├── requirements.txt
└── README.md


**Tecnologias utilizadas**
Lenguaje: Python 3

Base de Datos: SQLite

Arquitectura: Service Layer Pattern (Patron de Capa de Servicio)

**Conceptos clave**
Separacion de responsabilidades: La carpeta services/ contiene la totalidad de la logica de negocio, aislandola de la persistencia y de la interfaz.

Centralizacion de datos: El manejo de la base de datos se realiza de forma unificada para garantizar la integridad de la informacion.

Modularidad: Cada entidad del sistema posee su propio servicio dedicado.

Escalabilidad: El backend esta diseñado para ser consumido por diversas implementaciones de interfaz de usuario, ya sean entornos de escritorio o aplicaciones web.