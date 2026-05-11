from services.client_service import ClientService
from services.order_service import OrderService
from services.vehicle_service import VehicleService


def main():
    client_service = ClientService()
    vehicle_service = VehicleService()
    order_service = OrderService()

    # ----------------------------------------
    # Create client
    # ----------------------------------------
    client_id = client_service.create_client(
        name="Juan Perez",
        phone="3411234567",
        email="juan@mail.com",
    )
    print(f"Client created with ID: {client_id}")

    # ----------------------------------------
    # Create vehicle
    # ----------------------------------------
    vehicle_id = vehicle_service.create_vehicle(
        client_id=client_id,
        brand="Ford",
        model="Fiesta",
        plate="ABC5234",
    )
    print(f"Vehicle created with ID: {vehicle_id}")

    # ----------------------------------------
    # Create order
    # ----------------------------------------
    order_id = order_service.create_order(
        vehicle_id=vehicle_id,
        scheduled_date="2026-04-10",
        scheduled_time="10:00",
        notes="Oil change",
    )
    print(f"Order created with ID: {order_id}")

    # ----------------------------------------
    # List orders
    # ----------------------------------------
    orders = order_service.get_all_orders()
    print("\nRegistered orders:")
    for order in orders:
        print(order)


if __name__ == "__main__":
    main()
