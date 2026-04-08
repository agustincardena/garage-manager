from services.client_service import ClientService
from services.vehicle_service import VehicleService
from services.order_service import OrderService


def main():
    client_service = ClientService()
    vehicle_service = VehicleService()
    order_service = OrderService()

    # ----------------------------------------
    # CREAR CLIENTE
    # ----------------------------------------
    client_id = client_service.create_client(
        name="Juan Perez",
        phone="3411234567",
        email="juan@mail.com"
    )
    print(f"Cliente creado con ID: {client_id}")

    # ----------------------------------------
    # CREAR VEHICULO
    # ----------------------------------------
    vehicle_id = vehicle_service.create_vehicle(
        client_id=client_id,
        brand="Ford",
        model="Fiesta",
        plate="ABC5234"
    )
    print(f"Vehículo creado con ID: {vehicle_id}")

    # ----------------------------------------
    # CREAR ORDEN
    # ----------------------------------------
    order_id = order_service.create_order(
        vehicle_id=vehicle_id,
        scheduled_date="2026-04-10",
        scheduled_time="10:00",
        notes="Cambio de aceite"
    )
    print(f"Orden creada con ID: {order_id}")

    # ----------------------------------------
    # LISTAR ORDENES
    # ----------------------------------------
    orders = order_service.get_all_orders()
    print("\nÓrdenes registradas:")
    for order in orders:
        print(order)


if __name__ == "__main__":
    main()