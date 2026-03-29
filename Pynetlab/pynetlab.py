import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import socket
import threading
import time
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

class PythonNetLabV11:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Network Lab - Precisão Temporal & UDP Fix")
        self.root.geometry("1100x950")
        
        self.is_running = False
        self.main_socket = None
        self.metrics = {} 
        self.lock = threading.Lock()
        
        # --- Interface ---
        header = tk.Frame(root, bg="#2c3e50")
        header.pack(fill="x", padx=10, pady=5)
        tk.Label(header, text=f"IP LOCAL: {self.get_local_ip()}", fg="white", bg="#2c3e50", font=("Arial", 12, "bold")).pack(pady=10)

        config_frame = ttk.LabelFrame(root, text=" Configurações do Experimento ")
        config_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(config_frame, text="Papel:").grid(row=0, column=0, padx=5, pady=5)
        self.mode_var = tk.StringVar(value="Cliente")
        ttk.Combobox(config_frame, textvariable=self.mode_var, values=["Cliente", "Servidor"], state="readonly", width=12).grid(row=0, column=1)

        tk.Label(config_frame, text="Protocolo:").grid(row=0, column=2, padx=5)
        self.proto_var = tk.StringVar(value="TCP")
        ttk.Combobox(config_frame, textvariable=self.proto_var, values=["TCP", "UDP"], state="readonly", width=10).grid(row=0, column=3)

        tk.Label(config_frame, text="Porta:").grid(row=0, column=4, padx=5)
        self.port_entry = ttk.Entry(config_frame, width=8); self.port_entry.insert(0, "5001")
        self.port_entry.grid(row=0, column=5)

        tk.Label(config_frame, text="IP Servidor:").grid(row=1, column=0, padx=5, pady=5)
        self.ip_entry = ttk.Entry(config_frame, width=15); self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.grid(row=1, column=1)

        tk.Label(config_frame, text="Duração (s):").grid(row=1, column=2, padx=5)
        self.time_entry = ttk.Entry(config_frame, width=8); self.time_entry.insert(0, "10")
        self.time_entry.grid(row=1, column=3)

        tk.Label(config_frame, text="Threads:").grid(row=1, column=4, padx=5)
        self.threads_entry = ttk.Entry(config_frame, width=8); self.threads_entry.insert(0, "1")
        self.threads_entry.grid(row=1, column=5)

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)
        self.btn_start = tk.Button(btn_frame, text="INICIAR TESTE", command=self.toggle_test, bg="#27ae60", fg="white", font=("Arial", 10, "bold"), width=22)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        self.btn_export = tk.Button(btn_frame, text="EXPORTAR RELATÓRIO", command=self.export_report, bg="#f39c12", fg="white", font=("Arial", 10, "bold"), state=tk.DISABLED)
        self.btn_export.pack(side=tk.LEFT, padx=5)

        self.console = scrolledtext.ScrolledText(root, height=12, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10))
        self.console.pack(fill="x", padx=10, pady=5)

        self.fig, self.ax = plt.subplots(figsize=(8, 4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10)

    def log(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        self.console.insert(tk.END, f"[{ts}] {message}\n")
        self.console.see(tk.END)

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8", 80))
            res = s.getsockname()[0]; s.close()
            return res
        except: return "127.0.0.1"

    def toggle_test(self):
        if not self.is_running:
            self.is_running = True
            self.metrics.clear()
            self.ax.clear()
            self.canvas.draw()
            self.btn_start.config(text="PARAR / RESET", bg="#c0392b")
            self.btn_export.config(state=tk.DISABLED)
            threading.Thread(target=self.run_engine, daemon=True).start()
            self.update_ui_loop()
        else:
            self.is_running = False
            if self.main_socket: 
                try: self.main_socket.close() 
                except: pass
            self.btn_start.config(text="INICIAR TESTE", bg="#27ae60")

    def run_engine(self):
        try:
            mode = self.mode_var.get()
            proto = self.proto_var.get()
            port = int(self.port_entry.get())
            if mode == "Servidor": self.run_server(port, proto)
            else: self.run_client_manager(proto)
        except Exception as e:
            self.log(f"Erro na engine: {e}")
            self.is_running = False

    def run_server(self, port, proto):
        sock_type = socket.SOCK_STREAM if proto == "TCP" else socket.SOCK_DGRAM
        self.main_socket = socket.socket(socket.AF_INET, sock_type)
        self.main_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.main_socket.settimeout(1.0) # Evita travamento da console
        
        try:
            self.main_socket.bind(('0.0.0.0', port))
            self.log(f"Servidor {proto} aguardando na porta {port}...")
            
            if proto == "TCP":
                self.main_socket.listen(10)
                while self.is_running:
                    try:
                        conn, addr = self.main_socket.accept()
                        label = f"{addr[0]}:{addr[1]}"
                        threading.Thread(target=self.tcp_handler, args=(conn, label), daemon=True).start()
                    except socket.timeout: continue
            else:
                while self.is_running:
                    try:
                        data, addr = self.main_socket.recvfrom(65535)
                        label = f"{addr[0]}:{addr[1]}"
                        self.record_data(label, len(data))
                    except socket.timeout: continue
        except Exception as e:
            if self.is_running: self.log(f"Erro no servidor: {e}")
        finally:
            self.log("Servidor finalizado.")

    def tcp_handler(self, conn, label):
        self.record_data(label, 0) # Inicializa
        try:
            with conn:
                conn.settimeout(2.0)
                while self.is_running:
                    try:
                        data = conn.recv(131072)
                        if not data: break
                        self.record_data(label, len(data))
                    except socket.timeout: continue
        finally:
            with self.lock:
                if label in self.metrics: self.metrics[label]['active'] = False

    def run_client_manager(self, proto):
        ip = self.ip_entry.get(); port = int(self.port_entry.get())
        num = int(self.threads_entry.get()); dur = int(self.time_entry.get())
        self.log(f"Iniciando teste de {dur}s ({proto})...")
        threads = []
        for i in range(num):
            label = f"Local:T{i}"
            t = threading.Thread(target=self.client_sender, args=(ip, port, dur, proto, label), daemon=True)
            threads.append(t); t.start()
        
        for t in threads: t.join()
        
        time.sleep(1.5) # Tempo para a UI processar o último lote
        self.is_running = False
        self.root.after(0, self.finish_test_logs)

    def client_sender(self, ip, port, duration, proto, label):
        self.record_data(label, 0) # Inicializa métricas
        sock_type = socket.SOCK_STREAM if proto == "TCP" else socket.SOCK_DGRAM
        start_t = time.time()
        try:
            with socket.socket(socket.AF_INET, sock_type) as s:
                if proto == "TCP": 
                    s.settimeout(5.0)
                    s.connect((ip, port))
                
                while self.is_running and (time.time() - start_t < duration):
                    payload = b'X' * 32768
                    if proto == "TCP": s.sendall(payload)
                    else: s.sendto(payload, (ip, port))
                    self.record_data(label, len(payload))
        except Exception as e:
            self.log(f"Erro no cliente {label}: {e}")
        finally:
            time.sleep(1.1) # Mantém 'active' True para o último ciclo do update_ui
            with self.lock:
                if label in self.metrics: self.metrics[label]['active'] = False

    def record_data(self, label, size):
        with self.lock:
            if label not in self.metrics:
                self.metrics[label] = {
                    'inst_bytes': 0, 'history': [], 
                    'total_bytes': 0, 'active': True, 
                    'last_seen': time.time()
                }
            self.metrics[label]['inst_bytes'] += size
            self.metrics[label]['total_bytes'] += size
            self.metrics[label]['last_seen'] = time.time()

    def update_ui_loop(self):
        if not self.is_running: return
        
        now = time.time()
        timeout_val = 2.0 

        with self.lock:
            active_labels = list(self.metrics.keys())
            if active_labels:
                self.ax.clear()
                self.ax.set_title("Vazão em Tempo Real (Mbps)")
                self.ax.set_ylabel("Mbps"); self.ax.set_xlabel("Segundos")
                
                for label in active_labels:
                    data = self.metrics[label]
                    
                    # Timeout UDP no Servidor
                    if self.mode_var.get() == "Servidor" and self.proto_var.get() == "UDP":
                        if now - data['last_seen'] > timeout_val:
                            data['active'] = False

                    if data['active']:
                        mbps = (data['inst_bytes'] * 8) / 1_000_000
                        data['history'].append(mbps)
                        data['inst_bytes'] = 0
                        self.log(f"{label} >> {mbps:.2f} Mbps")
                    
                    if data['history']:
                        self.ax.plot(range(len(data['history'])), data['history'], label=str(label), marker='o', markersize=4)

                self.ax.legend(loc='upper right')
                self.ax.grid(True, alpha=0.3)
                self.canvas.draw()
        
        self.root.after(1000, self.update_ui_loop)

    def finish_test_logs(self):
        self.log("-" * 40)
        with self.lock:
            for label, data in self.metrics.items():
                hist = data['history']
                if hist:
                    avg = sum(hist) / len(hist)
                    self.log(f"RESULTADO FINAL [{label}]:")
                    self.log(f" > Vazão Média: {avg:.2f} Mbps")
                    self.log(f" > Total Transmitido: {data['total_bytes']/(1024*1024):.2f} MB")
        self.log("-" * 40)
        self.btn_start.config(text="INICIAR TESTE", bg="#27ae60")
        self.btn_export.config(state=tk.NORMAL)

    def export_report(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            with open(path, "w") as f:
                f.write(f"Relatório de Rede - {datetime.now()}\n")
                for l, d in self.metrics.items():
                    if d['history']:
                        f.write(f"{l}: Média {sum(d['history'])/len(d['history']):.2f} Mbps\n")
            messagebox.showinfo("Sucesso", "Relatório salvo.")

    def on_closing(self):
        self.is_running = False
        os._exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = PythonNetLabV11(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()