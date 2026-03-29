import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import time

class NetcatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PyNetcat Educacional v2.9 - Lab Redes")
        
        self.is_running = False
        self.socket = None
        self.last_client_addr = None
        self.active_clients = [] 
        self.known_clients = set() 
        
        # --- Interface ---
        setup_frame = tk.LabelFrame(root, text="Configurações de Rede")
        setup_frame.pack(fill="x", padx=10, pady=5)

        self.ent_ip = tk.Entry(setup_frame, width=12); self.ent_ip.insert(0, "127.0.0.1"); self.ent_ip.grid(row=0, column=0)
        self.ent_port = tk.Entry(setup_frame, width=6); self.ent_port.insert(0, "8080"); self.ent_port.grid(row=0, column=1)
        
        self.var_proto = tk.StringVar(value="TCP")
        ttk.Combobox(setup_frame, textvariable=self.var_proto, values=["TCP", "UDP"], width=5).grid(row=0, column=2)

        self.var_mode = tk.StringVar(value="Servidor")
        ttk.Combobox(setup_frame, textvariable=self.var_mode, values=["Servidor", "Cliente"], width=10).grid(row=0, column=3)

        self.var_app_proto = tk.StringVar(value="Protocolo Alo")
        ttk.Combobox(setup_frame, textvariable=self.var_app_proto, 
                     values=["RAW", "Protocolo Alo", "HTTP Get", "Time Protocol"], width=15).grid(row=0, column=4)

        self.btn_start = tk.Button(setup_frame, text="Iniciar", command=self.start_connection, bg="green", fg="white", width=7)
        self.btn_start.grid(row=0, column=5, padx=2)
        
        self.btn_stop = tk.Button(setup_frame, text="Parar", command=self.stop_connection, bg="red", fg="white", state="disabled", width=7)
        self.btn_stop.grid(row=0, column=6, padx=2)

        self.log_area = scrolledtext.ScrolledText(root, height=6, state='disabled', fg="blue", font=("Consolas", 9))
        self.log_area.pack(fill="both", padx=10, pady=2)

        self.data_area = scrolledtext.ScrolledText(root, height=12, state='disabled', font=("Consolas", 10))
        self.data_area.pack(fill="both", padx=10, pady=5)

        send_frame = tk.Frame(root)
        send_frame.pack(fill="x", padx=10, pady=5)
        self.ent_msg = tk.Entry(send_frame); self.ent_msg.pack(side="left", fill="x", expand=True)
        tk.Button(send_frame, text="Enviar / Simular", command=self.send_data).pack(side="right")

    def log(self, msg):
        self.log_area.config(state='normal'); self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n"); self.log_area.see(tk.END); self.log_area.config(state='disabled')

    def display_data(self, msg, direction="IN", addr=None):
        self.data_area.config(state='normal')
        tag = "in" if direction == "IN" else "out"
        self.data_area.tag_config("in", foreground="darkblue")
        self.data_area.tag_config("out", foreground="darkgreen")
        
        if direction == "IN":
            prefix = f"<< RECEBIDO DE {addr[0]}:{addr[1]}" if addr else "<< RECEBIDO"
        else:
            prefix = ">> ENVIADO"
            
        self.data_area.insert(tk.END, f"{prefix}\n{msg}\n{'-'*40}\n", tag)
        self.data_area.see(tk.END); self.data_area.config(state='disabled')

    def start_connection(self):
        self.is_running = True
        self.known_clients.clear()
        self.btn_start.config(state="disabled"); self.btn_stop.config(state="normal")
        threading.Thread(target=self.run_logic, daemon=True).start()

    def stop_connection(self):
        self.is_running = False
        if self.socket:
            try: self.socket.close()
            except: pass
        for c in self.active_clients:
            try: c.close()
            except: pass
        self.active_clients = []
        self.log("Serviço encerrado.")
        self.btn_start.config(state="normal"); self.btn_stop.config(state="disabled")

    def run_logic(self):
        kind = socket.SOCK_STREAM if self.var_proto.get() == "TCP" else socket.SOCK_DGRAM
        self.socket = socket.socket(socket.AF_INET, kind)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            ip, port = self.ent_ip.get(), int(self.ent_port.get())
            if self.var_mode.get() == "Servidor":
                self.socket.bind((ip, port))
                if self.var_proto.get() == "TCP":
                    self.socket.listen(5); self.log(f"Servidor TCP em {ip}:{port}")
                    while self.is_running:
                        client, addr = self.socket.accept()
                        self.active_clients.append(client)
                        self.last_client_addr = addr
                        self.log(f"Conexão TCP de {addr[0]}:{addr[1]}")
                        if self.var_app_proto.get() == "Protocolo Alo":
                            banner = "220 Bem-vindo ao Servidor ALO (TCP)\r\n"
                            client.send(banner.encode()); self.display_data(banner, "OUT")
                        threading.Thread(target=self.handle_tcp_client, args=(client, addr), daemon=True).start()
                else:
                    self.log(f"Servidor UDP em {ip}:{port}")
                    while self.is_running:
                        data, addr = self.socket.recvfrom(4096)
                        self.last_client_addr = addr
                        self.process_logic(data, addr, is_udp=True)
            else: # MODO CLIENTE
                if self.var_proto.get() == "TCP":
                    self.socket.connect((ip, port))
                    self.log(f"Conectado ao servidor.")
                    while self.is_running:
                        data = self.socket.recv(4096)
                        if not data: break
                        self.display_data(data.decode(), "IN", addr=(ip, port))
                else:
                    # CLIENTE UDP: Fazemos um bind em porta 0 (qualquer porta livre) para abrir a escuta
                    self.socket.bind(('', 0))
                    local_port = self.socket.getsockname()[1]
                    self.log(f"Cliente UDP escutando na porta local: {local_port}")
                    while self.is_running:
                        try:
                            data, addr = self.socket.recvfrom(4096)
                            if data: self.display_data(data.decode(), "IN", addr=addr)
                        except: break
        except Exception as e:
            if self.is_running: self.log(f"Erro: {e}")
            self.stop_connection()

    def handle_tcp_client(self, client_socket, addr):
        try:
            while self.is_running:
                data = client_socket.recv(4096)
                if not data: break
                self.process_logic(data, addr, client_socket)
        except: pass
        finally:
            if client_socket in self.active_clients: self.active_clients.remove(client_socket)
            client_socket.close()

    def process_logic(self, data, addr, sock_ref=None, is_udp=False):
        msg = data.decode().strip()
        if not msg: return # Ignora pacotes vazios de keep-alive
        
        app_mode = self.var_app_proto.get()
        self.display_data(msg, "IN", addr=addr)
        
        # Lógica de Resposta Automática
        response = None
        if is_udp and app_mode == "Protocolo Alo" and addr not in self.known_clients:
            banner = f"220 Bem-vindo ao ALO UDP\r\n"
            self.socket.sendto(banner.encode(), addr); self.display_data(banner, "OUT")
            self.known_clients.add(addr)

        if app_mode == "Protocolo Alo":
            if msg.upper() == "ALÔ!": response = "250 Alô com sucesso"
            else: response = "500 Erro de Sintaxe"
        elif app_mode == "HTTP Get" and msg.upper().startswith("GET"):
            response = "HTTP/1.1 200 OK\r\n\r\n<html><body>Resposta UDP OK</body></html>"
        elif app_mode == "Time Protocol":
            response = f"TIME: {time.ctime()}"

        if response:
            self.display_data(response, "OUT")
            try:
                if is_udp: self.socket.sendto(response.encode(), addr)
                else: sock_ref.send(response.encode())
            except: pass

    def send_data(self):
        content = self.ent_msg.get()
        app_mode = self.var_app_proto.get()
        
        if not content:
            if app_mode == "HTTP Get": content = "GET / HTTP/1.1\r\n\r\n"
            elif app_mode == "Protocolo Alo": content = "Alô!"
            elif app_mode == "Time Protocol": content = "GET_TIME"
            else: return

        try:
            dest_ip, dest_port = self.ent_ip.get(), int(self.ent_port.get())
            if self.var_mode.get() == "Cliente":
                if self.var_proto.get() == "TCP": self.socket.send(content.encode())
                else: self.socket.sendto(content.encode(), (dest_ip, dest_port))
            else: # Servidor
                if self.var_proto.get() == "TCP" and self.active_clients:
                    self.active_clients[-1].send(content.encode())
                elif self.var_proto.get() == "UDP" and self.last_client_addr:
                    self.socket.sendto(content.encode(), self.last_client_addr)
            
            self.display_data(content, "OUT")
            self.ent_msg.delete(0, tk.END)
        except Exception as e: self.log(f"Erro: {e}")

if __name__ == "__main__":
    root = tk.Tk(); app = NetcatGUI(root); root.mainloop()