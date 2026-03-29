import socket, threading, tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext

class ClientePenaltyGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pênaltis Online - Modo Fila")
        self.root.geometry("500x950")
        self.root.configure(bg="#1b5e20")
        
        self.sock = None
        self.pode_jogar = False
        self.tempo_restante = 5
        self.cronometro_ativo = False
        self.lances_contagem = 0 
        self.nome_local = ""
        self.ip_servidor = "127.0.0.1"
        self.porta_servidor = 5000

        # --- Elementos Visuais ---
        self.lbl_funcao = tk.Label(self.root, text="AGUARDANDO...", font=("Arial", 20, "bold"), fg="#ffeb3b", bg="#1b5e20")
        self.lbl_funcao.pack(pady=5)
        
        self.f_placar = tk.Frame(self.root, bg="#1b5e20")
        self.f_placar.pack(pady=5)
        self.lbl_p1_nome = tk.Label(self.f_placar, text="P1", font=("Arial", 10, "bold"), fg="white", bg="#1b5e20")
        self.lbl_p1_nome.grid(row=0, column=0)
        self.lbl_score = tk.Label(self.f_placar, text="0 x 0", font=("Arial", 28, "bold"), fg="#ffeb3b", bg="#1b5e20")
        self.lbl_score.grid(row=0, column=1, padx=20)
        self.lbl_p2_nome = tk.Label(self.f_placar, text="P2", font=("Arial", 10, "bold"), fg="white", bg="#1b5e20")
        self.lbl_p2_nome.grid(row=0, column=2)

        self.cv_status = tk.Canvas(self.root, width=440, height=40, bg="#1b5e20", highlightthickness=0)
        self.cv_status.pack(pady=5)
        self.bolas_p1 = [self.cv_status.create_oval(10+i*30, 10, 30+i*30, 30, fill="#424242", outline="white") for i in range(5)]
        self.bolas_p2 = [self.cv_status.create_oval(290+i*30, 10, 310+i*30, 30, fill="#424242", outline="white") for i in range(5)]

        self.cv_gol = tk.Canvas(self.root, width=400, height=220, bg="#1b5e20", highlightthickness=0)
        self.cv_gol.pack(pady=5)
        self.alvos_coords = {}
        self.ids_trave = {}
        self.desenhar_trave_base()

        self.log_eventos = scrolledtext.ScrolledText(self.root, width=55, height=10, font=("Courier", 10), bg="#000", fg="#0f0")
        self.log_eventos.pack(pady=10, padx=10)

        self.f_btn = tk.Frame(self.root, bg="#1b5e20")
        self.f_btn.pack()
        self.btns = [tk.Button(self.f_btn, text=str(i), width=8, height=3, font=("Arial", 10, "bold"),
                               command=lambda x=i: self.enviar(x), state='disabled') for i in range(9)]
        for i, b in enumerate(self.btns): b.grid(row=i//3, column=i%3, padx=2, pady=2)

        self.lbl_local = tk.Label(self.root, text="VOCÊ: ---", font=("Arial", 12, "bold"), fg="#81c784", bg="#0d2e10", pady=5)
        self.lbl_local.pack(fill="x", side="bottom")

        if self.conectar_primeira_vez():
            self.root.mainloop()

    def limpar_tudo(self):
        """Reseta toda a interface para um novo jogo"""
        self.lances_contagem = 0
        self.lbl_score.config(text="0 x 0")
        self.lbl_funcao.config(text="AGUARDANDO...")
        for b in self.bolas_p1 + self.bolas_p2: self.cv_status.itemconfig(b, fill="#424242")
        self.desenhar_trave_base()
        self.log_eventos.config(state="normal")
        self.log_eventos.delete("1.0", tk.END)
        self.log_eventos.config(state="disabled")
        self.escrever_log("SISTEMA: Novo jogo iniciado.")

    def escrever_log(self, texto):
        self.log_eventos.config(state="normal")
        self.log_eventos.insert(tk.END, texto + "\n")
        self.log_eventos.see(tk.END)
        self.log_eventos.config(state="disabled")

    def desenhar_trave_base(self):
        self.cv_gol.delete("all")
        self.ids_trave["ESQ"] = self.cv_gol.create_line(60, 200, 60, 40, width=10, fill="white")
        self.ids_trave["DIR"] = self.cv_gol.create_line(340, 200, 340, 40, width=10, fill="white")
        self.ids_trave["TOPO"] = self.cv_gol.create_line(55, 40, 345, 40, width=10, fill="white")
        pos = [(100,70),(200,70),(300,70),(100,120),(200,120),(300,120),(100,170),(200,170),(300,170)]
        for i, (x,y) in enumerate(pos):
            self.alvos_coords[str(i)] = (x, y)
            self.cv_gol.create_oval(x-20, y-20, x+20, y+20, outline="white", width=1)
            self.cv_gol.create_text(x, y, text=str(i), fill="white", font=("Arial", 10, "bold"))

    def conectar_primeira_vez(self):
        self.nome_local = simpledialog.askstring("Login", "Nome:")
        if not self.nome_local: return False
        self.ip_servidor = simpledialog.askstring("IP", "Servidor:", initialvalue="127.0.0.1")
        self.porta_servidor = simpledialog.askinteger("Porta", "Porta:", initialvalue=5000)
        return self.tentar_conexao()

    def tentar_conexao(self):
        if self.sock: self.sock.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.ip_servidor, self.porta_servidor))
            self.sock.send(self.nome_local.encode())
            self.lbl_local.config(text=f"VOCÊ: {self.nome_local.upper()}")
            threading.Thread(target=self.ouvir, daemon=True).start()
            self.limpar_tudo()
            return True
        except:
            messagebox.showerror("Erro", "Servidor offline.")
            return False

    def enviar(self, v):
        if self.pode_jogar:
            try:
                self.sock.send(str(v).encode())
                self.pode_jogar = self.cronometro_ativo = False
                for b in self.btns: b.config(state='disabled')
            except: pass

    def tick(self):
        if self.cronometro_ativo and self.tempo_restante > 0:
            self.escrever_log(f"TEMPO: {'.' * self.tempo_restante}")
            self.tempo_restante -= 1
            self.root.after(1000, self.tick)

    def marcar_lance(self, chu, defe, res):
        if self.lances_contagem == 10:
            for b in self.bolas_p1 + self.bolas_p2: self.cv_status.itemconfig(b, fill="#424242")
            self.lances_contagem = 0

        self.cv_gol.delete("persistente")
        self.cv_gol.itemconfig(self.ids_trave["ESQ"], fill="white")
        self.cv_gol.itemconfig(self.ids_trave["DIR"], fill="white")
        self.cv_gol.itemconfig(self.ids_trave["TOPO"], fill="white")

        if defe.isdigit() and defe in self.alvos_coords:
            x, y = self.alvos_coords[defe]
            self.cv_gol.create_oval(x-24, y-24, x+24, y+24, fill="#00e5ff", tags="persistente")
        
        if chu.isdigit() and chu in self.alvos_coords:
            x, y = self.alvos_coords[chu]
            offset = 5 if chu == defe else 0
            self.cv_gol.create_oval(x-20+offset, y-20+offset, x+20-offset, y+20-offset, fill="#ff9800", tags="persistente")
        elif chu == "FORA":
            self.cv_gol.itemconfig(self.ids_trave["ESQ"], fill="black")
            self.cv_gol.itemconfig(self.ids_trave["DIR"], fill="black")
            self.cv_gol.itemconfig(self.ids_trave["TOPO"], fill="black")
        elif chu == "TRAVE" or chu == "TRAVESSÃO":
            tag_trave = "TOPO" if chu == "TRAVESSÃO" else "ESQ" # Simplificado para visual
            self.cv_gol.itemconfig(self.ids_trave["ESQ"], fill="#f44336")
            self.cv_gol.itemconfig(self.ids_trave["DIR"], fill="#f44336")
            if chu == "TRAVESSÃO": self.cv_gol.itemconfig(self.ids_trave["TOPO"], fill="#f44336")

        cor_bolinha = "#4caf50" if res == "GOL" else "#f44336"
        idx = (self.lances_contagem // 2)
        if idx < 5:
            if self.lances_contagem % 2 == 0: self.cv_status.itemconfig(self.bolas_p1[idx], fill=cor_bolinha)
            else: self.cv_status.itemconfig(self.bolas_p2[idx], fill=cor_bolinha)
        self.lances_contagem += 1

    def ouvir(self):
        while True:
            try:
                data = self.sock.recv(2048).decode()
                if not data: break
                for msg in data.split("|"):
                    if not msg: continue
                    if msg.startswith("SETUP:"):
                        p = msg.split(":")
                        self.lbl_p1_nome.config(text=p[1]); self.lbl_p2_nome.config(text=p[2])
                        self.limpar_tudo()
                    
                    elif msg in ["CHUTAR", "DEFENDER"]:
                        self.pode_jogar = self.cronometro_ativo = True
                        self.tempo_restante = 5
                        self.lbl_funcao.config(text=msg, fg="#ffeb3b")
                        self.escrever_log(f"\n>>> VEZ DE {msg} <<<")
                        self.tick()
                        for b in self.btns: b.config(state='normal')
                    
                    elif msg.startswith("LANCE:"):
                        p = msg.split(":")
                        if len(p) >= 6:
                            self.marcar_lance(p[2], p[4], p[5])
                            self.escrever_log(f"LANCE: Chute {p[2]} | Defesa {p[4]} -> {p[5]}")

                    elif msg.startswith("PLACAR:"):
                        p = msg.split(":"); self.lbl_score.config(text=f"{p[1]} x {p[2]}")
                    
                    elif msg.startswith("FIM:"):
                        venc = msg.split(':')[1]
                        messagebox.showinfo("Fim", f"Vencedor: {venc}")
                    
                    elif msg.startswith("REPLAY?"):
                        resp = messagebox.askyesno("Revanche", "Deseja revanche? (Se não, voltará para a fila)")
                        if resp:
                            self.sock.send("s".encode())
                        else:
                            self.sock.send("n".encode())
                            self.tentar_conexao() # Volta para a fila
                            return
            except: break
        
        # Se sair do loop, o oponente caiu ou recusou
        resp = messagebox.askyesno("Oponente saiu", "O oponente saiu do jogo. Voltar para a fila?")
        if resp: self.tentar_conexao()
        else: self.root.destroy()

if __name__ == "__main__":
    ClientePenaltyGUI()