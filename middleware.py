import socket
import mysql.connector
from mysql.connector import Error
import threading
import tkinter as tk
from tkinter import scrolledtext

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'localhost',
    'database': 'chat',
    'user': 'root',
    'password': ''
}

# Función para crear la tabla si no existe
def create_table():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        cursor.execute(""" 
            CREATE TABLE IF NOT EXISTS mensajes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cliente VARCHAR(255) NOT NULL,
                mensaje TEXT NOT NULL
            )
        """)
        connection.commit()
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Función para guardar mensajes en la base de datos
def save_message(cliente, mensaje):
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        cursor.execute("INSERT INTO mensajes (cliente, mensaje) VALUES (%s, %s)", (cliente, mensaje))
        connection.commit()
    except Error as e:
        print(f"Error al insertar en MySQL: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Clase para el servidor
class ChatServer:
    def __init__(self, text_area):
        self.tcp_socket = None
        self.udp_socket = None
        self.is_running = False
        self.text_area = text_area
        self.tcp_clients = []  # Lista para mantener los sockets de clientes TCP
        self.udp_clients = []  # Lista para mantener las direcciones de clientes UDP

    # Función para manejar conexiones TCP
    def handle_tcp_connection(self, client_socket, addr):
        self.append_to_text_area(f"Conexión TCP aceptada de {addr}")
        self.tcp_clients.append(client_socket)  # Agregar cliente a la lista
        with client_socket:
            while self.is_running:
                data = client_socket.recv(1024)
                if not data:
                    break
                cliente = f"Cliente TCP: {addr}"
                mensaje = data.decode('utf-8')
                self.append_to_text_area(f"{cliente} dijo: {mensaje}")
                save_message(cliente, mensaje)
                self.broadcast_message(f"{cliente}: {mensaje}")  # Reenviar el mensaje a todos los clientes TCP y UDP

    # Función para manejar conexiones UDP
    def handle_udp_connection(self):
        while self.is_running:
            data, addr = self.udp_socket.recvfrom(1024)
            cliente = f"Cliente UDP: {addr}"
            mensaje = data.decode('utf-8')
            self.append_to_text_area(f"{cliente} dijo: {mensaje}")
            save_message(cliente, mensaje)

            # Agregar cliente UDP a la lista si no está ya en la lista
            if addr not in self.udp_clients:
                self.udp_clients.append(addr)

            self.broadcast_message(f"{cliente}: {mensaje}", addr)  # Reenviar el mensaje a todos los clientes TCP

    # Función para difundir mensajes a todos los clientes TCP y UDP conectados
    def broadcast_message(self, message, sender_addr=None):
        for client in self.tcp_clients:
            try:
                client.sendall(message.encode('utf-8'))
            except Exception as e:
                self.append_to_text_area(f"Error al enviar mensaje a un cliente TCP: {e}")

        # Enviar mensaje a todos los clientes UDP conectados, excepto al que envió el mensaje
        for udp_client in self.udp_clients:
            if udp_client != sender_addr:  # No enviar al cliente que envió el mensaje
                self.udp_socket.sendto(message.encode('utf-8'), udp_client)

    # Función para iniciar el servidor
    def start_server(self):
        self.is_running = True
        self.append_to_text_area("Iniciando servidor")
        create_table()

        # Crear sockets
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Configurar puertos y direcciones
        self.tcp_socket.bind(('0.0.0.0', 8080))
        self.udp_socket.bind(('0.0.0.0', 8080))

        # Escuchar conexiones TCP
        self.tcp_socket.listen(5)
        self.append_to_text_area("Esperando conexiones TCP en el puerto 8080")

        # Iniciar hilos para TCP y UDP
        threading.Thread(target=self.accept_tcp_connections, daemon=True).start()
        threading.Thread(target=self.handle_udp_connection, daemon=True).start()

    def accept_tcp_connections(self):
        while self.is_running:
            client_socket, addr = self.tcp_socket.accept()
            threading.Thread(target=self.handle_tcp_connection, args=(client_socket, addr), daemon=True).start()

    # Función para detener el servidor
    def stop_server(self):
        self.is_running = False
        self.tcp_socket.close()
        self.udp_socket.close()
        self.append_to_text_area("Servidor detenido.")

    def append_to_text_area(self, message):
        self.text_area.insert(tk.END, message + '\n')
        self.text_area.see(tk.END)

# Clase para la GUI
class ChatServerGUI:
    def __init__(self, root):
        self.text_area = scrolledtext.ScrolledText(root, width=60, height=20)
        self.text_area.pack()

        self.server = ChatServer(self.text_area)  # Pasar el área de texto al servidor

        self.start_button = tk.Button(root, text="Iniciar Servidor", command=self.start_server)
        self.start_button.pack()

        self.stop_button = tk.Button(root, text="Detener Servidor", command=self.stop_server)
        self.stop_button.pack()

    def start_server(self):
        self.server.start_server()

    def stop_server(self):
        self.server.stop_server()

# Ejecutar la GUI
if __name__ == "__main__":
    root = tk.Tk()
    gui = ChatServerGUI(root)
    root.mainloop()
