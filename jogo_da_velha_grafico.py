import socket
import threading
import tkinter as tk
from tkinter import messagebox

class JogoDaVelhaRedes:
    def __init__(self, root):
        self.root = root
        self.root.title("Jogo da Velha - Redes")
        self.conn = None
        
        self.tabuleiro = [" "] * 9
        self.botoes = []
        self.meu_simbolo = ""
        self.seu_simbolo = ""
        self.turno_meu = False
        self.papel = "" 

        self.container = tk.Frame(self.root)
        self.container.pack(padx=20, pady=20)
        self.tela_configuracao()

    def tela_configuracao(self):
        self.limpar_tela()
        tk.Label(self.container, text="Configuração de Partida", font=('Arial', 12, 'bold')).pack(pady=10)
        
        self.var_papel = tk.StringVar(value="S")
        f_radio = tk.Frame(self.container); f_radio.pack()
        tk.Radiobutton(f_radio, text="Servidor", variable=self.var_papel, value="S", command=self.atualizar_foco).pack(side=tk.LEFT)
        tk.Radiobutton(f_radio, text="Cliente", variable=self.var_papel, value="C", command=self.atualizar_foco).pack(side=tk.LEFT)

        tk.Label(self.container, text="IP (para cliente):").pack()
        self.ent_ip = tk.Entry(self.container); self.ent_ip.insert(0, "127.0.0.1"); self.ent_ip.pack()
        tk.Label(self.container, text="Porta:").pack()
        self.ent_porta = tk.Entry(self.container); self.ent_porta.insert(0, "5000"); self.ent_porta.pack()

        self.btn_iniciar = tk.Button(self.container, text="Conectar", command=self.conectar, bg="lightblue", width=15)
        self.btn_iniciar.pack(pady=10)
        self.atualizar_foco()

    def atualizar_foco(self):
        estado = 'disabled' if self.var_papel.get() == "S" else 'normal'
        self.ent_ip.config(state=estado)

    def conectar(self):
        self.papel = self.var_papel.get()
        ip = self.ent_ip.get()
        porta = int(self.ent_porta.get())
        self.btn_iniciar.config(state='disabled', text="Aguardando...")
        threading.Thread(target=self.gerenciar_conexao, args=(ip, porta), daemon=True).start()

    def gerenciar_conexao(self, ip, porta):
        try:
            if self.papel == 'S':
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('', porta))
                s.listen(1)
                self.conn, _ = s.accept()
            else:
                self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.conn.connect((ip, porta))
            
            # Loop Principal de Partidas (Igual ao seu while True do console)
            while True:
                self.root.after(0, self.montar_tabuleiro_gui)
                self.executar_partida()
                
                # Sincronização de "Jogar Novamente"
                # A versão gráfica pergunta e envia 's' ou 'n'
                resposta = messagebox.askyesno("Fim", "Deseja jogar novamente?")
                msg_envio = 's' if resposta else 'n'
                self.conn.send(msg_envio.encode())
                
                resposta_oponente = self.conn.recv(1024).decode()
                if msg_envio != 's' or resposta_oponente != 's':
                    break
            
            self.conn.close()
            self.root.after(0, self.tela_configuracao)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erro", str(e)))
            self.root.after(0, self.tela_configuracao)

    def executar_partida(self):
        self.tabuleiro = [" "] * 9
        # Sorteio (Servidor envia, Cliente recebe)
        if self.papel == 'S':
            import random
            quem_comeca = random.choice(['S', 'C'])
            self.conn.send(quem_comeca.encode())
        else:
            quem_comeca = self.conn.recv(1024).decode()

        self.meu_simbolo = 'O' if (self.papel == quem_comeca) else 'X'
        self.seu_simbolo = 'X' if self.meu_simbolo == 'O' else 'O'
        self.turno_meu = (quem_comeca == self.papel)
        self.root.after(0, lambda: self.root.title("Eu sou: " + self.meu_simbolo))
        self.atualizar_status_gui()

        while True:
            vencedor = self.verificar_vencedor()
            if vencedor:
                self.root.after(0, lambda: self.mostrar_resultado(vencedor))
                return # Sai da partida e volta para o gerenciar_conexao

            if not self.turno_meu:
                dados = self.conn.recv(1024).decode()
                if not dados: break
                idx = int(dados)
                self.tabuleiro[idx] = self.seu_simbolo
                self.root.after(0, lambda i=idx: self.botoes[i].config(text=self.seu_simbolo))
                self.turno_meu = True
                self.atualizar_status_gui()

    def realizar_jogada_local(self, indice):
        if self.turno_meu and self.tabuleiro[indice] == " ":
            self.tabuleiro[indice] = self.meu_simbolo
            self.botoes[indice].config(text=self.meu_simbolo)
            self.conn.send(str(indice).encode())
            self.turno_meu = False
            self.atualizar_status_gui()

    def montar_tabuleiro_gui(self):
        self.limpar_tela()
        self.botoes = []
        self.label_status = tk.Label(self.container, text="", font=('Arial', 10, 'bold'))
        self.label_status.grid(row=0, column=0, columnspan=3, pady=5)
        for i in range(9):
            btn = tk.Button(self.container, text="", font=('Arial', 20), width=4, height=2,
                            command=lambda i=i: self.realizar_jogada_local(i))
            btn.grid(row=(i//3)+1, column=i%3, padx=2, pady=2)
            self.botoes.append(btn)

    def atualizar_status_gui(self):
        msg = "SUA VEZ" if self.turno_meu else "ESPERANDO..."
        cor = "green" if self.turno_meu else "red"
        self.root.after(0, lambda: self.label_status.config(text=msg, fg=cor))

    def mostrar_resultado(self, vencedor):
        res = "Deu velha!" if vencedor == "Empate" else "Vencedor: " + vencedor
        self.label_status.config(text=res, fg="blue")

    def limpar_tela(self):
        for widget in self.container.winfo_children(): widget.destroy()

    def verificar_vencedor(self):
        v = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
        for a, b, c in v:
            if self.tabuleiro[a] == self.tabuleiro[b] == self.tabuleiro[c] != " ": return self.tabuleiro[a]
        return "Empate" if " " not in self.tabuleiro else None

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("300x420")
    app = JogoDaVelhaRedes(root)
    root.mainloop()