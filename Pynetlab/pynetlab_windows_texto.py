import socket
import threading
import time
import sys
import struct
import os
import argparse

class CLIClient:
    def __init__(self, args):
        self.args = args
        self.is_running = True
        self.metrics = {}
        self.lock = threading.Lock()

    def record_metrics(self, label, size):
        with self.lock:
            if label not in self.metrics:
                self.metrics[label] = {'total_bytes': 0, 'inst_bytes': 0}
            self.metrics[label]['total_bytes'] += size
            self.metrics[label]['inst_bytes'] += size

    def prepare_payload(self, chunk, seq):
        if self.args.proto == "UDP" and not self.args.no_loss:
            header = struct.pack('!Q', seq)
            return header + chunk[8:] if len(chunk) > 8 else header
        return chunk

    def client_sender(self, label):
        sock_type = socket.SOCK_STREAM if self.args.proto == "TCP" else socket.SOCK_DGRAM
        start_t = time.time()
        seq_count = 0
        buf_size = self.args.buffer

        try:
            with socket.socket(socket.AF_INET, sock_type) as s:
                if self.args.proto == "TCP":
                    s.settimeout(5.0)
                    s.connect((self.args.ip, self.args.port))

                # MODO ARQUIVO
                if self.args.file and os.path.exists(self.args.file):
                    with open(self.args.file, "rb") as f:
                        while self.is_running:
                            chunk = f.read(buf_size)
                            if not chunk: break
                            payload = self.prepare_payload(chunk, seq_count)
                            if self.args.proto == "TCP": s.sendall(payload)
                            else: s.sendto(payload, (self.args.ip, self.args.port))
                            self.record_metrics(label, len(payload))
                            seq_count += 1
                    if self.args.proto == "UDP": s.sendto(b"FIN", (self.args.ip, self.args.port))
                
                # MODO TEMPO
                else:
                    while self.is_running and (time.time() - start_t < self.args.time):
                        chunk = b'X' * buf_size
                        payload = self.prepare_payload(chunk, seq_count)
                        if self.args.proto == "TCP": s.sendall(payload)
                        else: s.sendto(payload, (self.args.ip, self.args.port))
                        self.record_metrics(label, len(payload))
                        seq_count += 1
        except Exception as e:
            print(f"\n[Erro {label}]: {e}")
        finally:
            self.is_running = False

    def monitor(self):
        print(f"\n{'#'*50}")
        print(f" Teste Iniciado: {self.args.ip}:{self.args.port} ({self.args.proto})")
        print(f" Threads: {self.args.threads} | Buffer: {self.args.buffer} bytes")
        print(f"{'#'*50}\n")
        
        start_time = time.time()
        try:
            while self.is_running:
                time.sleep(1)
                total_mbps = 0
                with self.lock:
                    for label, m in self.metrics.items():
                        mbps = (m['inst_bytes'] * 8) / 1_000_000
                        total_mbps += mbps
                        m['inst_bytes'] = 0
                
                elapsed = int(time.time() - start_time)
                sys.stdout.write(f"\rTempo: {elapsed:3d}s | Vazão Total: {total_mbps:8.2f} Mbps")
                sys.stdout.flush()
        except KeyboardInterrupt:
            self.is_running = False

    def run(self):
        threads = []
        for i in range(self.args.threads):
            t = threading.Thread(target=self.client_sender, args=(f"T{i+1}",))
            threads.append(t)
            t.start()

        self.monitor()
        for t in threads: t.join()

        print("\n\n--- TESTE FINALIZADO ---")
        total_final = sum(m['total_bytes'] for m in self.metrics.values())
        print(f"Volume Total: {total_final/(1024*1024):.2f} MB")
        print(f"{'#'*50}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Python NetLab CLI Client")
    parser.add_argument("--ip", required=True, help="IP do Servidor")
    parser.add_argument("--port", type=int, default=5001, help="Porta (Padrão 5001)")
    parser.add_argument("--proto", choices=["TCP", "UDP"], default="TCP", help="Protocolo")
    parser.add_argument("--time", type=int, default=10, help="Duração em segundos")
    parser.add_argument("--threads", type=int, default=1, help="Número de threads")
    parser.add_argument("--buffer", type=int, default=32768, help="Tamanho do buffer em bytes")
    parser.add_argument("--file", help="Caminho do arquivo para envio")
    parser.add_argument("--no-loss", action="store_true", help="Desativa cabeçalho de seq number (UDP)")

    args = parser.parse_args()
    client = CLIClient(args)
    client.run()