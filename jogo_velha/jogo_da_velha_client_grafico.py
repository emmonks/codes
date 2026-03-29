import socket
import threading
import tkinter as tk
from tkinter import messagebox

class ClienteVelhaGrafico:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Jogo da Velha em Rede")
        self.window.geometry("300x450")
        
        # Estado do Jogo
        self.nome_usuario = ""
        self.ip_servidor = ""
        self.porta_servidor = ""
        self.meu_simbolo = ""
        self.oponente = ""
        self.minha_vez = False
        self.botoes = []
        
        self.setup_login_ui()
        
    def setup_login_ui(self):
        self.frame_login = tk.Frame(self.window)
        self.frame_login.pack(expand=True)
        
        tk.Label(self.frame_login, text="Seu Nome:").pack()
        self.ent_nome = tk.Entry(self.frame_login)
        self.ent_nome.pack(pady=5)
        self.ent_nome.insert(0, "Jogador")

        tk.Label(self.frame_login, text="IP do Servidor:").pack()
        self.ent_ip = tk.Entry(self.frame_login)
        self.ent_ip.pack(pady=5)
        self.ent_ip.insert(0, "127.0.0.1")

        tk.Label(self.frame_login, text="Porta:").pack()
        self.ent_porta = tk.Entry(self.frame_login)
        self.ent_porta.pack(pady=5)
        self.ent_porta.insert(0, "5000")

        tk.Button(self.frame_login, text="Conectar", command=self.conectar, bg="green", fg="white").pack(pady=20)

    def conectar(self):
        self.nome_usuario = self.ent_nome.get()
        self.ip_servidor = self.ent_ip.get()
        self.porta_servidor = int(self.ent_porta.get())
        self.iniciar_sessao()

    def iniciar_sessao(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.ip_servidor, self.porta_servidor))
            self.sock.send(self.nome_usuario.encode())
            
            if hasattr(self, 'frame_login'): self.frame_login.pack_forget()
            self.build_board()
            
            threading.Thread(target=self.receber_dados, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def build_board(self):
        for widget in self.window.winfo_children(): widget.destroy()
        
        self.status_label = tk.Label(self.window, text="Aguardando...", font=('Arial', 10, 'bold'))
        self.status_label.pack(pady=10)
        
        self.grid_frame = tk.Frame(self.window)
        self.grid_frame.pack()
        
        self.botoes = []
        for i in range(9):
            btn = tk.Button(self.grid_frame, text=" ", font=('Arial', 20, 'bold'), 
                           height=2, width=5, command=lambda x=i: self.clique_botao(x))
            btn.grid(row=i//3, column=i%3)
            self.botoes.append(btn)

    def clique_botao(self, idx):
        if self.minha_vez and self.botoes[idx]['text'] == " ":
            self.sock.send(str(idx).encode())
            self.minha_vez = False
            self.atualizar_status()

    def receber_dados(self):
        while True:
            try:
                data = self.sock.recv(1024).decode()
                if not data: break

                # Tratamento de Framing (Delimitador |)
                mensagens = data.split("|")
                for msg in mensagens:
                    if not msg: continue
                    
                    if msg == "AGUARDE":
                        self.window.after(0, lambda: self.status_label.config(text="Aguardando oponente..."))
                    
                    elif msg.startswith("START:"):
                        _, s, op = msg.split(":")
                        self.meu_simbolo, self.oponente = s, op
                        self.seu_simbolo = "X" if s == "O" else "O"
                        self.minha_vez = (s == "O")
                        self.window.after(0, self.atualizar_status)
                    
                    elif msg.startswith("OK:"):
                        idx = int(msg.split(":")[1])
                        self.window.after(0, lambda i=idx: self.marcar(i, self.meu_simbolo, "blue"))
                        self.window.after(0, self.atualizar_status)

                    elif msg.startswith("OPONENTE:"):
                        idx = int(msg.split(":")[1])
                        self.window.after(0, lambda i=idx: self.marcar(i, self.seu_simbolo, "red"))
                        self.minha_vez = True
                        self.window.after(0, self.atualizar_status)

                    elif msg.startswith("FIM:"):
                        res = msg.split(":")[1]
                        # Pequeno delay para o usuário ver a última jogada antes do alerta
                        self.window.after(500, lambda r=res: self.mostrar_fim(r))
                        return # Encerra a thread de escuta
            except:
                break

    def marcar(self, idx, sim, cor):
        self.botoes[idx].config(text=sim, fg=cor)

    def atualizar_status(self):
        txt = "SUA VEZ (%s)" % self.meu_simbolo if self.minha_vez else "Vez de %s" % self.oponente
        cor = "blue" if self.minha_vez else "red"
        self.status_label.config(text=txt, fg=cor)

    def mostrar_fim(self, res):
        self.minha_vez = False # Garante bloqueio
        if res == "Empate": m = "Empate!"
        elif res == self.meu_simbolo: m = "VOCÊ VENCEU!"
        else: m = "VOCÊ PERDEU!"
        
        if messagebox.askyesno("Fim", m + "\n\nJogar novamente?"):
            self.sock.close()
            self.iniciar_sessao()
        else:
            self.window.destroy()

if __name__ == "__main__":
    ClienteVelhaGrafico().window.mainloop()