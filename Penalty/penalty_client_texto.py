import socket
import threading
import sys
import time
import os

class ClientePenaltyCLI:
    def __init__(self):
        self.sock = None
        self.pode_jogar = False
        self.nome_local = ""
        self.ip_servidor = "127.0.0.1"
        self.porta_servidor = 5000
        self.running = True
        
        # Dados de jogo
        self.p1_bolas = ["."] * 5
        self.p2_bolas = ["."] * 5
        self.lances_contagem = 0

        print("\n" + "="*40)
        print("      PÊNALTIS ONLINE - MODO TEXTO")
        print("="*40)

        # Solicita dados apenas na primeira vez
        self.nome_local = input("Seu Nome: ")
        self.ip_servidor = input("IP do Servidor [127.0.0.1]: ") or "127.0.0.1"
        try:
            p = input("Porta [5000]: ")
            self.porta_servidor = int(p) if p else 5000
        except: self.porta_servidor = 5000

        if self.conectar():
            self.loop_entrada()

    def exibir_placar_visual(self):
        p1 = " ".join(["({0})".format(b) for b in self.p1_bolas])
        p2 = " ".join(["({0})".format(b) for b in self.p2_bolas])
        print("\nSTATUS DAS COBRANÇAS:")
        print("P1: {0}".format(p1))
        print("P2: {0}".format(p2))
        print("-" * 30)

    def desenhar_gol(self):
        print("\n      _______________________")
        print("     | [0]     [1]     [2] |")
        print("     |                     |")
        print("     | [3]     [4]     [5] |")
        print("     |                     |")
        print("     | [6]     [7]     [8] |")
        print("     |_____           _____|")
        print("           |_________|\n")

    def conectar(self):
        """Estabelece conexão e inicia a thread de escuta"""
        if self.sock:
            try: self.sock.close()
            except: pass
            
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.ip_servidor, self.porta_servidor))
            self.sock.send(self.nome_local.encode())
            print("\n[SISTEMA] Conectado! Aguardando oponente na fila...")
            
            # Reseta o estado local para novo jogo
            self.p1_bolas = ["."] * 5
            self.p2_bolas = ["."] * 5
            self.lances_contagem = 0
            self.pode_jogar = False
            
            # Thread de escuta (sempre daemon para fechar com o main)
            t = threading.Thread(target=self.ouvir, daemon=True)
            t.start()
            return True
        except Exception as e:
            print("\n[ERRO] Falha ao conectar: {0}".format(e))
            return False

    def ouvir(self):
        while self.running:
            try:
                data = self.sock.recv(2048).decode()
                if not data: break
                
                for msg in data.split("|"):
                    if not msg: continue
                    
                    if msg.startswith("SETUP:"):
                        p = msg.split(":")
                        self.p1_bolas = ["."] * 5
                        self.p2_bolas = ["."] * 5
                        self.lances_contagem = 0
                        print("\n" + "#"*40 + "\n JOGO: {0} VS {1}\n".format(p[1], p[2]) + "#"*40)

                    elif msg in ["CHUTAR", "DEFENDER"]:
                        self.pode_jogar = True
                        self.exibir_placar_visual()
                        print("\n--> SUA VEZ DE {0}! <--".format(msg))
                        self.desenhar_gol()
                        print("Escolha (0-8): ", end="", flush=True)

                    elif msg.startswith("LANCE:"):
                        p = msg.split(":")
                        res = p[5]
                        marcador = "O" if res == "GOL" else "X"
                        
                        idx = self.lances_contagem // 2
                        if idx < 5:
                            if self.lances_contagem % 2 == 0: self.p1_bolas[idx] = marcador
                            else: self.p2_bolas[idx] = marcador
                        self.lances_contagem += 1
                        
                        print("\n[LANCE] Chute:{0} | Defesa:{1} | Resultado:{2}".format(p[2], p[4], res))

                    elif msg.startswith("PLACAR:"):
                        p = msg.split(":")
                        print("[PLACAR ATUAL] {0} x {1}".format(p[1], p[2]))

                    elif msg.startswith("FIM:"):
                        self.exibir_placar_visual()
                        print("\n" + "*"*40 + "\n VENCEDOR: {0}\n".format(msg.split(':')[1]) + "*"*40)

                    elif msg.startswith("REPLAY?"):
                        print("\n[?] Revanche? (s/n). 'n' volta para a fila: ", end="", flush=True)
                        self.pode_jogar = True 

            except: break
        
        if self.running:
            print("\n[SISTEMA] Oponente desconectado ou fim da sessão.")

    def loop_entrada(self):
        while self.running:
            if self.pode_jogar:
                jogada = input().strip().lower()
                if not jogada: continue
                try:
                    if jogada == 's':
                        self.sock.send("s".encode())
                        self.pode_jogar = False
                    elif jogada == 'n':
                        self.sock.send("n".encode())
                        print("\n[SISTEMA] Voltando para a fila de espera...")
                        self.conectar() # Reconecta para entrar na fila novamente
                    elif jogada.isdigit() and 0 <= int(jogada) <= 8:
                        self.sock.send(jogada.encode())
                        self.pode_jogar = False
                    else:
                        print("Digite 0-8 ou s/n.")
                except: 
                    self.conectar()
            else:
                time.sleep(0.2)

if __name__ == "__main__":
    try:
        ClientePenaltyCLI()
    except KeyboardInterrupt:
        os._exit(0)