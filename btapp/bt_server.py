import bluetooth

# Set Bluetooth device name and discoverability
device_name = 'Shootpi'
discoverable_time = 180  # 3 minutes

# Set up Bluetooth socket
server_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
server_socket.bind(("", bluetooth.PORT_ANY))
server_socket.listen(1)

# Get the Bluetooth port number
port = server_socket.getsockname()[1]

# Set the Bluetooth device discoverable
bluetooth.advertise_service(
    server_socket,
    "Shootpi",
    service_id=bluetooth.SERIAL_PORT_CLASS,
    service_classes=[bluetooth.SERIAL_PORT_CLASS],
    profiles=[bluetooth.SERIAL_PORT_PROFILE],
    )

print(f"Waiting for connection on RFCOMM channel {port}...")
print(f"Device '{device_name}' is discoverable for {discoverable_time} seconds.")

# Start accepting connections
client_socket, client_info = server_socket.accept()
print(f"Accepted connection from {client_info}")

# Handle the connection
try:
    while True:
        data = client_socket.recv(1024)
        if not data:
            break
        print(f"Received data: {data.decode()}")

except OSError as e:
    print(f"Socket error: {e}")

finally:
    # Clean up the connection
    client_socket.close()
    server_socket.close()
    print("Connection closed.")