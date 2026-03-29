import socket
import threading
import time
import sys
import os
import argparse

class NetLab:
    def __init__(self, args):
        self.args = args
        self.is_running = True
        self.monitor_ativo = False
        self.metrics = {}
        self.lock = threading.Lock()
        self.start_time = 0

    def record_metrics(self, label, size):
        with self.lock:
            if not self.monitor_ativo:
                self.monitor_ativo = True
                self.start_time = time.time()
            
            if label not in self.metrics:
                self.metrics[label] = {'total_bytes': 0, 'inst_bytes': 0}
            self.metrics[label]['total_bytes'] += size
            self.metrics[label]['inst_bytes'] += size

    # --- LÓGICA DO SERVIDOR ---
    def start_server(self):
        sock_type = socket.SOCK_STREAM if self.args.proto == "TCP" else socket.SOCK_DGRAM
        s = socket.socket(socket.AF_INET, sock_type)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            s.bind(('', self.args.port))
            if self.args.proto == "TCP":
                s.listen(5)
                sys.stdout.write("[SVR] Aguardando conexao TCP na porta {0}...\n".format(self.args.port))
            else:
                sys.stdout.write("[SVR] Aguardando pacotes UDP na porta {0}...\n".format(self.args.port))
            
            sys.stdout.write("[SVR] Pressione 'q' + Enter para encerrar o servidor.\n")
            sys.stdout.flush()

            # Thread para o monitor e thread para o comando de saída
            threading.Thread(target=self.monitor).start()
            threading.Thread(target=self.wait_for_quit).start()

            if self.args.proto == "TCP":
                while self.is_running:
                    s.settimeout(1.0)
                    try:
                        conn, addr = s.accept()
                        t = threading.Thread(target=self.handle_tcp_client, args=(conn, addr))
                        t.daemon = True
                        t.start()
                    except socket.timeout:
                        continue
            else:
                self.handle_udp_server(s)

        except Exception as e:
            if self.is_running:
                sys.stdout.write("\n[Erro Servidor]: {0}\n".format(e))
        finally:
            s.close()

    def handle_tcp_client(self, conn, addr):
        label = "{0}:{1}".format(addr[0], addr[1])
        try:
            while self.is_running:
                data = conn.recv(self.args.buffer)
                if not data: break
                self.record_metrics(label, len(data))
        finally:
            conn.close()

    def handle_udp_server(self, s):
        while self.is_running:
            s.settimeout(1.0)
            try:
                data, addr = s.recvfrom(self.args.buffer)
                label = "{0}:{1}".format(addr[0], addr[1])
                self.record_metrics(label, len(data))
            except socket.timeout:
                continue

    # --- LÓGICA DO CLIENTE ---
    def client_sender(self, label):
        sock_type = socket.SOCK_STREAM if self.args.proto == "TCP" else socket.SOCK_DGRAM
        buf_size = self.args.buffer
        s = socket.socket(socket.AF_INET, sock_type)
        
        try:
            if self.args.proto == "TCP":
                s.settimeout(5.0)
                s.connect((self.args.ip, self.args.port))

            while self.is_running:
                if not self.args.file and self.monitor_ativo:
                    if (time.time() - self.start_time > self.args.time):
                        break
                
                chunk = b'X' * buf_size
                if self.args.proto == "TCP": 
                    s.sendall(chunk)
                else: 
                    s.sendto(chunk, (self.args.ip, self.args.port))
                
                self.record_metrics(label, len(chunk))
        except Exception as e:
            sys.stdout.write("\n[Erro Cliente {0}]: {1}\n".format(label, e))
        finally:
            s.close()

    def wait_for_quit(self):
        while self.is_running:
            cmd = sys.stdin.readline().strip().lower()
            if cmd == 'q':
                sys.stdout.write("\nEncerrando NetLab...\n")
                self.is_running = False
                os._exit(0)

    # --- MONITOR ---
    def monitor(self):
        while self.is_running:
            if not self.monitor_ativo:
                time.sleep(0.1)
                continue
            
            time.sleep(1)
            total_mbps = 0
            with self.lock:
                for label in list(self.metrics.keys()):
                    m = self.metrics[label]
                    mbps = (m['inst_bytes'] * 8) / 1000000.0
                    total_mbps += mbps
                    m['inst_bytes'] = 0
            
            elapsed = int(time.time() - self.start_time)
            stats = "\rTempo: {0:3d}s | Vazao Total: {1:8.2f} Mbps".format(elapsed, total_mbps)
            sys.stdout.write(stats)
            sys.stdout.flush()
            
            if self.args.mode == "client" and elapsed >= self.args.time:
                self.is_running = False

    def run(self):
        if self.args.mode == "server":
            self.start_server()
        else:
            sys.stdout.write("[CLI] Iniciando teste para {0}...\n".format(self.args.ip))
            threads = []
            for i in range(self.args.threads):
                label = "T{0}".format(i+1)
                t = threading.Thread(target=self.client_sender, args=(label,))
                t.daemon = True
                t.start()
                threads.append(t)
            
            self.monitor()
            for t in threads: t.join()
            sys.stdout.write("\n\n--- TESTE FINALIZADO ---\n")
            sys.stdout.flush()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NetLab Unificado V3")
    parser.add_argument("--mode", choices=["client", "server"], required=True)
    parser.add_argument("--ip", help="IP do Servidor")
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--proto", choices=["TCP", "UDP"], default="TCP")
    parser.add_argument("--time", type=int, default=10)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--buffer", type=int, default=32768)
    parser.add_argument("--file", help="Arquivo para enviar")

    args = parser.parse_args()
    NetLab(args).run()
