import sys
import base64
import hashlib
import threading
import time
import tkinter as tk
from tkinter import filedialog
from scapy.all import IP, ICMP, send, sniff, conf
ICMP_TYPE_CUSTOM = 42
CHUNK_SIZE = 768 

class ICMPLabTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Lab Redes: ICMP Transfer")
        self.received_data = bytearray()
        self.is_receiving = False
        
        # --- UI ---
        tk.Label(root, text="Configuração Loopback/Rede", font=('Arial', 10, 'bold')).pack(pady=5)
        
        frame_ip = tk.Frame(root)
        frame_ip.pack()
        tk.Label(frame_ip, text="IP Destino:").pack(side=tk.LEFT)
        self.ent_ip = tk.Entry(frame_ip)
        self.ent_ip.pack(side=tk.LEFT)
        self.ent_ip.insert(0, "127.0.0.1")

        self.btn_modo = tk.Button(root, text="LIGAR RECEPTOR", bg="red", fg="white", 
                                  command=self.toggle_receptor, font=('Arial', 9, 'bold'))
        self.btn_modo.pack(pady=10, fill=tk.X, padx=50)

        self.txt_log = tk.Text(root, height=12, width=50, bg="black", fg="lightgreen", font=("Consolas", 9))
        self.txt_log.pack(padx=5, pady=5)

        self.ent_msg = tk.Entry(root, width=40)
        self.ent_msg.pack(padx=5, pady=5)
        
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Enviar Texto", command=self.enviar_texto).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Enviar Arquivo", command=self.enviar_arquivo).pack(side=tk.LEFT, padx=2)

    def log(self, msg):
        # Uso do after() para garantir que a UI atualize vindo de outra thread
        self.root.after(0, lambda: self.txt_log.insert(tk.END, msg + "\n"))
        self.root.after(0, lambda: self.txt_log.see(tk.END))

    def toggle_receptor(self):
        if not self.is_receiving:
            self.is_receiving = True
            self.btn_modo.config(text="RECEPTOR ATIVO (OUVINDO...)", bg="green")
            self.received_data = bytearray() 
            self.log("[SISTEMA] Aguardando pacotes...")
            threading.Thread(target=self.sniffer_thread, daemon=True).start()
        else:
            self.is_receiving = False
            self.btn_modo.config(text="LIGAR RECEPTOR", bg="red")

    def sniffer_thread(self):
        # No loopback, o Scapy às vezes precisa que a interface seja especificada
        # No Windows use conf.iface. No Linux pode ser 'lo'
        iface_name = None
        if sys.platform.startswith("linux"):
            iface_name = "lo" 

        sniff(iface=iface_name, filter="icmp", prn=self.processar, stop_filter=lambda x: not self.is_receiving)

    def processar(self, pkt):
        # Verificação rigorosa do pacote
        if pkt.haslayer(ICMP) and pkt[ICMP].type == ICMP_TYPE_CUSTOM:
            try:
                payload_raw = pkt[ICMP].load.decode('utf-8', errors='ignore')
                if ":" not in payload_raw: return
                
                tag, conteudo = payload_raw.split(":", 1)
                origem = pkt[IP].src

                if tag == "CHAT":
                    self.log(f"MENSAGEM de {origem}: {conteudo}")
                
                elif tag == "FILE":
                    part_bytes = base64.b64decode(conteudo)
                    self.received_data.extend(part_bytes)
                    # ACK Hash
                    h = hashlib.sha256(part_bytes).hexdigest()[:6]
                    self.log(f"Chunk recebido. Hash: {h}")
                    # Opcional: Enviar ACK de volta
                    send(IP(dst=origem)/ICMP(type=ICMP_TYPE_CUSTOM)/f"ACK:{h}".encode(), verbose=False)

                elif tag == "END":
                    # FINALIZAÇÃO E ESCRITA EM DISCO
                    filename = f"recebido_{int(time.time())}.dat"
                    with open(filename, "wb") as f:
                        f.write(self.received_data)
                    self.log(f"\n[!] ARQUIVO SALVO: {filename}")
                    self.log(f"[!] Total: {len(self.received_data)} bytes.")
                    self.received_data = bytearray()

            except Exception as e:
                self.log(f"Erro no processamento: {e}")

    def enviar_texto(self):
        dest = self.ent_ip.get()
        msg = self.ent_msg.get()
        if dest and msg:
            try:
                # Criamos o pacote
                pkt = IP(dst=dest)/ICMP(type=ICMP_TYPE_CUSTOM)/f"CHAT:{msg}".encode()
                
                # Enviamos usando o socket de Camada 3 (Raw L3 Socket)
                # Isso evita que o Scapy tente resolver o MAC via ARP
                send(pkt, verbose=False, socket=conf.L3socket())
                
                self.log(f"Você: {msg}")
                self.ent_msg.delete(0, tk.END)
            except Exception as e:
                self.log(f"Erro ao enviar texto: {e}")

    def enviar_arquivo(self):
        dest = self.ent_ip.get()
        caminho = filedialog.askopenfilename()
        
        if not dest or not caminho: 
            return
        
        def thread_upload():
            try:
                self.log(f"Iniciando envio de: {caminho}")
                with open(caminho, "rb") as f:
                    while chunk := f.read(CHUNK_SIZE):
                        b64 = base64.b64encode(chunk).decode()
                        pkt = IP(dst=dest)/ICMP(type=ICMP_TYPE_CUSTOM)/f"FILE:{b64}".encode()
                        
                        # Uso do socket L3 também para os fragmentos do arquivo
                        send(pkt, verbose=False, socket=conf.L3socket())
                        time.sleep(0.05) # Delay para estabilidade no CORE/Loopback
                
                # Envio do pacote sinalizador de fim (END)
                pkt_end = IP(dst=dest)/ICMP(type=ICMP_TYPE_CUSTOM)/"END:final".encode()
                send(pkt_end, verbose=False, socket=conf.L3socket())
                
                self.log("Arquivo enviado com sucesso.")
            except Exception as e:
                self.log(f"Erro no envio do arquivo: {e}")
            
        # Iniciamos a thread de upload para não travar a GUI
        threading.Thread(target=thread_upload, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = ICMPLabTool(root)
    root.mainloop()