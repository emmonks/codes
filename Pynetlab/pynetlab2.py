import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import socket
import threading
import time
import os
import struct
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

class PythonNetLabV13:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Network Lab V1.3 - Multi-Threading Edition")
        self.root.geometry("1150x980")
        
        self.is_running = False
        self.main_socket = None
        self.metrics = {} 
        self.lock = threading.Lock()
        self.source_file_path = None
        
        # --- Interface ---
        header = tk.Frame(root, bg="#34495e")
        header.pack(fill="x", padx=10, pady=5)
        tk.Label(header, text=f"IP LOCAL: {self.get_local_ip()}", fg="white", bg="#34495e", font=("Arial", 12, "bold")).pack(pady=10)

        config_frame = ttk.LabelFrame(root, text=" Configurações do Experimento ")
        config_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(config_frame, text="Papel:").grid(row=0, column=0, padx=5, pady=5)
        self.mode_var = tk.StringVar(value="Cliente")
        ttk.Combobox(config_frame, textvariable=self.mode_var, values=["Cliente", "Servidor"], state="readonly", width=10).grid(row=0, column=1)

        tk.Label(config_frame, text="Protocolo:").grid(row=0, column=2, padx=5)
        self.proto_var = tk.StringVar(value="TCP")
        ttk.Combobox(config_frame, textvariable=self.proto_var, values=["TCP", "UDP"], state="readonly", width=10).grid(row=0, column=3)

        tk.Label(config_frame, text="Porta:").grid(row=0, column=4, padx=5)
        self.port_entry = ttk.Entry(config_frame, width=8); self.port_entry.insert(0, "5001")
        self.port_entry.grid(row=0, column=5)

        tk.Label(config_frame, text="Threads:").grid(row=0, column=6, padx=5)
        self.threads_entry = ttk.Entry(config_frame, width=8); self.threads_entry.insert(0, "1")
        self.threads_entry.grid(row=0, column=7)

        tk.Label(config_frame, text="IP Servidor:").grid(row=1, column=0, padx=5, pady=5)
        self.ip_entry = ttk.Entry(config_frame, width=15); self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.grid(row=1, column=1)

        tk.Label(config_frame, text="Buffer (Bytes):").grid(row=1, column=2, padx=5)
        self.buffer_entry = ttk.Entry(config_frame, width=10); self.buffer_entry.insert(0, "32768")
        self.buffer_entry.grid(row=1, column=3)

        tk.Label(config_frame, text="Duração (s):").grid(row=1, column=4, padx=5)
        self.time_entry = ttk.Entry(config_frame, width=8); self.time_entry.insert(0, "10")
        self.time_entry.grid(row=1, column=5)

        self.loss_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="Perda (UDP)", variable=self.loss_var).grid(row=1, column=6, columnspan=2)

        self.file_btn = ttk.Button(config_frame, text="Selecionar Arquivo Base", command=self.select_file)
        self.file_btn.grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        
        self.file_label = tk.Label(config_frame, text="Nenhum arquivo (Modo Tempo)", font=("Arial", 8, "italic"))
        self.file_label.grid(row=2, column=2, columnspan=4, sticky="w")

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
            res = s.getsockname()[0]; s.close(); return res
        except: return "127.0.0.1"

    def select_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.source_file_path = path
            size_mb = os.path.getsize(path) / (1024*1024)
            self.file_label.config(text=f"Arquivo: {os.path.basename(path)} ({size_mb:.2f} MB)")
        else:
            self.source_file_path = None
            self.file_label.config(text="Nenhum arquivo (Modo Tempo)")

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
            self.log(f"Erro Engine: {e}"); self.is_running = False

    def run_server(self, port, proto):
        sock_type = socket.SOCK_STREAM if proto == "TCP" else socket.SOCK_DGRAM
        self.main_socket = socket.socket(socket.AF_INET, sock_type)
        self.main_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.main_socket.settimeout(1.0)
        try:
            self.main_socket.bind(('0.0.0.0', port))
            self.log(f"Servidor {proto} na porta {port}...")
            if proto == "TCP":
                self.main_socket.listen(10)
                while self.is_running:
                    try:
                        conn, addr = self.main_socket.accept()
                        threading.Thread(target=self.tcp_handler, args=(conn, f"{addr[0]}:{addr[1]}"), daemon=True).start()
                    except socket.timeout: continue
            else:
                while self.is_running:
                    try:
                        data, addr = self.main_socket.recvfrom(65535)
                        if data == b"FIN":
                            with self.lock:
                                if f"{addr[0]}:{addr[1]}" in self.metrics: self.metrics[f"{addr[0]}:{addr[1]}"]['active'] = False
                        else: self.process_incoming_data(f"{addr[0]}:{addr[1]}", data)
                    except socket.timeout: continue
        finally: self.log("Servidor encerrado.")

    def tcp_handler(self, conn, label):
        self.record_metrics(label, 0)
        try:
            with conn:
                while self.is_running:
                    data = conn.recv(131072)
                    if not data: break
                    self.record_metrics(label, len(data))
        finally:
            with self.lock:
                if label in self.metrics: self.metrics[label]['active'] = False

    def process_incoming_data(self, label, data):
        seq = -1
        if self.loss_var.get() and len(data) >= 8:
            try: seq = struct.unpack('!Q', data[:8])[0]
            except: pass
        with self.lock:
            if label not in self.metrics:
                self.metrics[label] = {'inst_bytes': 0, 'history': [], 'total_bytes': 0, 'active': True, 'last_seen': time.time(), 'expected_seq': 0, 'lost_packets': 0, 'total_packets': 0}
            m = self.metrics[label]; m['inst_bytes'] += len(data); m['total_bytes'] += len(data); m['last_seen'] = time.time(); m['active'] = True
            if seq != -1:
                m['total_packets'] += 1
                if seq > m['expected_seq']: m['lost_packets'] += (seq - m['expected_seq'])
                m['expected_seq'] = seq + 1

    def run_client_manager(self, proto):
        try:
            ip = self.ip_entry.get(); port = int(self.port_entry.get())
            num_threads = int(self.threads_entry.get())
            dur = int(self.time_entry.get()); buf = int(self.buffer_entry.get())
            
            self.log(f"Iniciando {num_threads} threads...")
            client_threads = []
            for i in range(num_threads):
                t_label = f"T{i+1}:Saída"
                t = threading.Thread(target=self.client_sender, args=(ip, port, dur, proto, buf, t_label), daemon=True)
                client_threads.append(t); t.start()
            
            for t in client_threads: t.join()
            time.sleep(1.5); self.is_running = False
            self.root.after(0, self.finish_test_logs)
        except Exception as e: self.log(f"Erro Cliente: {e}"); self.is_running = False

    def client_sender(self, ip, port, duration, proto, buf_size, label):
        self.record_metrics(label, 0)
        sock_type = socket.SOCK_STREAM if proto == "TCP" else socket.SOCK_DGRAM
        start_t = time.time()
        seq_count = 0
        try:
            with socket.socket(socket.AF_INET, sock_type) as s:
                if proto == "TCP": s.settimeout(5.0); s.connect((ip, port))
                
                # MODO ARQUIVO
                if self.source_file_path and os.path.exists(self.source_file_path):
                    with open(self.source_file_path, "rb") as f:
                        while self.is_running:
                            chunk = f.read(buf_size)
                            if not chunk: break
                            payload = self.prepare_payload(chunk, proto, seq_count)
                            if proto == "TCP": s.sendall(payload)
                            else: s.sendto(payload, (ip, port))
                            self.record_metrics(label, len(payload))
                            seq_count += 1
                    if proto == "UDP": s.sendto(b"FIN", (ip, port))
                
                # MODO TEMPO
                else:
                    while self.is_running and (time.time() - start_t < duration):
                        chunk = b'X' * buf_size
                        payload = self.prepare_payload(chunk, proto, seq_count)
                        if proto == "TCP": s.sendall(payload)
                        else: s.sendto(payload, (ip, port))
                        self.record_metrics(label, len(payload))
                        seq_count += 1
        except Exception as e: self.log(f"Erro {label}: {e}")
        finally:
            with self.lock:
                if label in self.metrics: self.metrics[label]['active'] = False

    def prepare_payload(self, chunk, proto, seq):
        if proto == "UDP" and self.loss_var.get():
            header = struct.pack('!Q', seq)
            return header + chunk[8:] if len(chunk) > 8 else header
        return chunk

    def record_metrics(self, label, size):
        with self.lock:
            if label not in self.metrics:
                self.metrics[label] = {'inst_bytes': 0, 'history': [], 'total_bytes': 0, 'active': True, 'last_seen': time.time(), 'expected_seq': 0, 'lost_packets': 0, 'total_packets': 0}
            self.metrics[label]['inst_bytes'] += size; self.metrics[label]['total_bytes'] += size; self.metrics[label]['last_seen'] = time.time()

    def update_ui_loop(self):
        if not self.is_running: return
        now = time.time()
        with self.lock:
            self.ax.clear()
            self.ax.set_title("Vazão por Thread (Mbps)")
            has_data = False
            for label, m in self.metrics.items():
                if self.mode_var.get() == "Servidor" and self.proto_var.get() == "UDP":
                    if now - m['last_seen'] > 3.0: m['active'] = False
                if m['active']:
                    mbps = (m['inst_bytes'] * 8) / 1_000_000
                    m['history'].append(mbps); m['inst_bytes'] = 0
                    perda = f" | Perda: {(m['lost_packets']/(m['lost_packets']+m['total_packets'])*100):.1f}%" if self.proto_var.get()=="UDP" and self.loss_var.get() and m['total_packets']>0 else ""
                    self.log(f"{label}: {mbps:.2f} Mbps{perda}")
                if m['history']:
                    self.ax.plot(m['history'], label=str(label), marker='o', markersize=3)
                    has_data = True
            if has_data: self.ax.legend(loc='upper right')
            self.ax.grid(True, alpha=0.3); self.canvas.draw()
        self.root.after(1000, self.update_ui_loop)

    def finish_test_logs(self):
        self.log("="*40 + "\nRESULTADO ACUMULADO:")
        total_vazao = 0
        with self.lock:
            for l, m in self.metrics.items():
                if m['history']:
                    avg = sum(m['history'])/len(m['history']); total_vazao += avg
                    self.log(f"[{l}] Média: {avg:.2f} Mbps | Total: {m['total_bytes']/(1024*1024):.2f} MB")
        self.log(f"VAZÃO AGREGADA: {total_vazao:.2f} Mbps\n" + "="*40)
        self.btn_start.config(text="INICIAR TESTE", bg="#27ae60"); self.btn_export.config(state=tk.NORMAL)

    def export_report(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            with open(path, "w") as f:
                f.write(f"Relatório NetLab - {datetime.now()}\n")
                for l, m in self.metrics.items():
                    if m['history']: f.write(f"{l}: {sum(m['history'])/len(m['history']):.2f} Mbps\n")
            messagebox.showinfo("Sucesso", "Salvo.")

if __name__ == "__main__":
    root = tk.Tk(); app = PythonNetLabV13(root)
    root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0)); root.mainloop()