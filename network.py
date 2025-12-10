import socket
import threading
import json
import time

class NetworkManager:
    def __init__(self):
        self.server_socket = None
        self.client_socket = None
        self.is_server = False
        self.clients = [] # List of client sockets (if server)
        self.port = 5555
        self.running = False
        
        # Buffer for received data
        self.buffer = ""

    def start_server(self, port=5555):
        self.is_server = True
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('0.0.0.0', port))
        self.server_socket.listen(4) # Max 4 players total (Host + 3)
        self.running = True
        print(f"Server started on port {port}")
        
        threading.Thread(target=self._accept_clients, daemon=True).start()

    def connect_to_server(self, ip, port=5555):
        self.is_server = False
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((ip, port))
            self.running = True
            print(f"Connected to server {ip}:{port}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def _accept_clients(self):
        while self.running:
            try:
                client, addr = self.server_socket.accept()
                print(f"Client connected from {addr}")
                self.clients.append(client)
                # Ideally send an initial "Hello" or ID assignment here
                # For now, Game logic will handle ID assignment via broadcast
            except Exception as e:
                print(f"Accept error: {e}")
                if not self.running: break

    def send(self, data):
        """Send data to relevant party. 
           If Server: Broadcast to all clients.
           If Client: Send to server.
        """
        message = json.dumps(data) + "\n" # Newline delimiter
        try:
            if self.is_server:
                remove_clients = []
                for client in self.clients:
                    try:
                        client.send(message.encode())
                    except:
                        remove_clients.append(client)
                
                for c in remove_clients:
                    self.clients.remove(c)
            elif self.client_socket:
                self.client_socket.send(message.encode())
        except Exception as e:
            print(f"Send error: {e}")

    def receive(self):
        """Receive data (generator).
           If Server: Receive from all clients? (Needs threading per client or non-blocking)
           If Client: Receive from server.
           
           Actually, for Server, we need to gather inputs from all clients.
           This method is tricky for Server if single-threaded call.
           Better approach: Background threads reading input and putting to a queue?
        """
        # For this simple MVP, let's just make receive specific to 'Client' reading State?
        # Server needs to read Inputs.
        return None # TODO: Implement proper receive queue

class GameServer:
    def __init__(self, port):
        self.network = NetworkManager()
        self.network.start_server(port)
        self.input_queue = [] # Thread-safe queue?
        self.lock = threading.Lock()
        
        # Start input threads for clients as they join?
        # The NetworkManager logic above is a bit too simple for Server input handling.
        # Let's refine.
        pass

# Redefining structure to be simpler and integrated
# We will use non-blocking sockets or threads per client.

class SnakeNetwork:
    def __init__(self, side="client"): # side: server or client
        self.sock = None
        self.clients = {} # ID -> socket (Server only)
        self.running = False
        self.input_queue = [] # Messages received
        self.lock = threading.Lock()
        self.my_id = None # Assigned by server

    def start_host(self, port=5555):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allow reuse
        self.sock.bind(('0.0.0.0', port))
        self.sock.listen(4)
        self.running = True
        self.my_id = 0
        
        # Accept thread
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def connect(self, ip, port=5555):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((ip, port))
            self.running = True
            
            # Start receive thread
            threading.Thread(target=self._receive_loop, args=(self.sock, -1), daemon=True).start()
            return True
        except Exception as e:
            print(f"Connect failed: {e}")
            return False

    def _accept_loop(self):
        next_id = 1
        while self.running:
            try:
                conn, addr = self.sock.accept()
                print(f"New connection from {addr}, assigning ID {next_id}")
                
                with self.lock:
                    self.clients[next_id] = conn
                
                # Send ID assignment
                init_msg = {"type": "init", "id": next_id}
                self._send_raw(conn, init_msg)
                
                # Start receive thread for this client
                threading.Thread(target=self._receive_loop, args=(conn, next_id), daemon=True).start()
                
                next_id += 1
            except Exception as e:
                if self.running: print(f"Accept error: {e}")

    def _receive_loop(self, sock, client_id):
        buffer = ""
        while self.running:
            try:
                data = sock.recv(4096)
                if not data:
                    break
                
                buffer += data.decode()
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line:
                        msg = json.loads(line)
                        if client_id != -1: # Server receiving from client
                            msg['player_id'] = client_id # Force ID trust
                        
                        # Special handling for Init on client side
                        if msg.get('type') == 'init' and client_id == -1:
                            self.my_id = msg['id']
                            print(f"Assigned Player ID: {self.my_id}")
                        else:
                            with self.lock:
                                self.input_queue.append(msg)
            except Exception as e:
                # print(f"Receive error (ID {client_id}): {e}")
                break
        
        # Cleanup
        if client_id != -1:
            with self.lock:
                if client_id in self.clients:
                    del self.clients[client_id]
            # Enqueue disconnect message
            with self.lock:
                self.input_queue.append({"type": "disconnect", "player_id": client_id})

    def _send_raw(self, sock, data):
        try:
            msg = json.dumps(data) + "\n"
            sock.sendall(msg.encode())
        except:
            pass

    def send_update(self, state_data):
        # Server sending game state to all
        # Optimization: Don't send JSON if state is massive?
        # For Snake, it's okay for now.
        msg_str = json.dumps(state_data) + "\n"
        encoded = msg_str.encode()
        
        with self.lock:
            for cid, conn in self.clients.items():
                try:
                    conn.sendall(encoded)
                except:
                    pass # Handle cleanup in recv loop

    def send_input(self, input_data):
        # Client sending input
        if self.sock:
            self._send_raw(self.sock, input_data)

    def get_events(self):
        with self.lock:
            events = self.input_queue[:]
            self.input_queue.clear()
        return events
