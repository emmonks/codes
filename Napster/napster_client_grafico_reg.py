import socket, threading, pickle, os, time, sys
from tkinter import *
from tkinter import messagebox, filedialog, ttk

class NapsterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Napster P2P Acadêmico")
        self.root.geometry("850x700")
        self.client_logic = None
        self.setup_ui()

    def setup_ui(self):
        # Frame de Conexão
        self.conn_frame = LabelFrame(self.root, text="Conexão", padx=10, pady=10)
        self.conn_frame.pack(fill="x", padx=10, pady=5)
        
        Label(self.conn_frame, text="IP:").grid(row=0, column=0)
        self.ent_ip = Entry(self.conn_frame, width=12); self.ent_ip.insert(0, "127.0.0.1"); self.ent_ip.grid(row=0, column=1)
        Label(self.conn_frame, text="Porta:").grid(row=0, column=2)
        self.ent_port = Entry(self.conn_frame, width=6); self.ent_port.insert(0, "5000"); self.ent_port.grid(row=0, column=3)
        Label(self.conn_frame, text="Nick:").grid(row=0, column=4)
        self.ent_nick = Entry(self.conn_frame, width=12); self.ent_nick.grid(row=0, column=5)

        self.port_var = StringVar(value="auto")
        Radiobutton(self.conn_frame, text="P. Auto", variable=self.port_var, value="auto", command=self.upd_p).grid(row=1, column=0, columnspan=2)
        Radiobutton(self.conn_frame, text="Fixa:", variable=self.port_var, value="fix", command=self.upd_p).grid(row=1, column=2)
        self.ent_p2p = Entry(self.conn_frame, width=6, state="disabled"); self.ent_p2p.grid(row=1, column=3)
        
        self.btn_conn = Button(self.conn_frame, text="Conectar", command=self.connect, bg="#d9ffdb", width=10)
        self.btn_conn.grid(row=1, column=4, padx=5)
        self.btn_disco = Button(self.conn_frame, text="Desconectar", command=self.disconnect, bg="#ffdad9", state="disabled", width=10)
        self.btn_disco.grid(row=1, column=5, padx=5)

        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(expand=True, fill="both", padx=10, pady=5)

        # Aba: Busca (Com opção de Dono/Usuário)
        self.tab_s = Frame(self.tabs); self.tabs.add(self.tab_s, text="Busca")
        f_s = Frame(self.tab_s, pady=5); f_s.pack(fill="x")
        self.search_mode = StringVar(value="simple")
        Radiobutton(f_s, text="Simples", variable=self.search_mode, value="simple").pack(side="left")
        Radiobutton(f_s, text="Regex", variable=self.search_mode, value="regex").pack(side="left")
        
        Label(f_s, text=" Arquivo:").pack(side="left")
        self.ent_s = Entry(f_s, width=15); self.ent_s.pack(side="left", padx=5)
        
        Label(f_s, text=" Dono:").pack(side="left") # REINSERIDO
        self.ent_user = Entry(f_s, width=10); self.ent_user.pack(side="left", padx=5)
        
        Button(f_s, text="🔍 Buscar", command=self.do_search).pack(side="left", padx=5)

        self.list_res = Listbox(self.tab_s, font=("Consolas", 10)); self.list_res.pack(expand=True, fill="both", padx=5)
        self.prog = ttk.Progressbar(self.tab_s, orient=HORIZONTAL, mode='determinate'); self.prog.pack(fill="x", padx=5)
        Button(self.tab_s, text="⬇ Baixar", command=self.do_down).pack(pady=5)

        # Aba: Chat
        self.tab_chat = Frame(self.tabs); self.tabs.add(self.tab_chat, text="Chat Global")
        self.txt_chat = Text(self.tab_chat, state="disabled", height=15, wrap="word"); self.txt_chat.pack(expand=True, fill="both", padx=5, pady=5)
        f_c = Frame(self.tab_chat); f_c.pack(fill="x", padx=5, pady=5)
        self.ent_chat = Entry(f_c); self.ent_chat.pack(side="left", expand=True, fill="x", padx=5)
        self.ent_chat.bind("<Return>", lambda e: self.send_chat())
        Button(f_c, text="Enviar", command=self.send_chat).pack(side="right")

        # Aba: Arquivos Locais
        self.tab_l = Frame(self.tabs); self.tabs.add(self.tab_l, text="Arquivos Locais")
        self.tree = ttk.Treeview(self.tab_l, columns=('n','s','d'), show='headings')
        self.tree.heading('n', text='Nome'); self.tree.heading('s', text='Tamanho'); self.tree.heading('d', text='Data')
        self.tree.pack(expand=True, fill="both", padx=5, pady=5)
        Button(self.tab_l, text="🔄 Atualizar", command=self.refresh_l).pack()

    def upd_p(self): self.ent_p2p.config(state="normal" if self.port_var.get()=="fix" else "disabled")

    def connect(self):
        f = filedialog.askdirectory() or "shared"
        p = int(self.ent_p2p.get()) if self.port_var.get()=="fix" else 0
        if p == 0:
            st = socket.socket(); st.bind(('', 0)); p = st.getsockname()[1]; st.close()
        self.client_logic = NapsterClientLogic(self.ent_ip.get(), int(self.ent_port.get()), self.ent_nick.get(), f, p, self)
        self.btn_conn.config(state="disabled"); self.btn_disco.config(state="normal"); self.refresh_l()

    def disconnect(self):
        if self.client_logic: self.client_logic.stop(); self.client_logic = None
        self.btn_conn.config(state="normal"); self.btn_disco.config(state="disabled")

    def refresh_l(self):
        if self.client_logic:
            for i in self.tree.get_children(): self.tree.delete(i)
            if not os.path.exists(self.client_logic.folder): os.makedirs(self.client_logic.folder)
            for f in os.listdir(self.client_logic.folder):
                path = os.path.join(self.client_logic.folder, f)
                if os.path.isfile(path):
                    st = os.stat(path); dt = time.strftime('%d/%m/%y %H:%M', time.localtime(st.st_mtime))
                    self.tree.insert('', END, values=(f, st.st_size, dt))

    def do_search(self):
        if self.client_logic:
            self.client_logic.s.send(pickle.dumps({
                'type': 'search', 
                'query': self.ent_s.get(), 
                'user_filter': self.ent_user.get(), 
                'search_type': self.search_mode.get()
            }))

    def send_chat(self):
        msg = self.ent_chat.get()
        if msg and self.client_logic:
            self.client_logic.s.send(pickle.dumps({'type': 'chat', 'msg': msg}))
            self.append_chat("Você: {}".format(msg))
            self.ent_chat.delete(0, END)

    def append_chat(self, msg):
        self.txt_chat.config(state="normal"); self.txt_chat.insert(END, msg + "\n"); self.txt_chat.see(END); self.txt_chat.config(state="disabled")

    def do_down(self):
        idx = self.list_res.curselection()
        if idx and self.client_logic:
            t = self.client_logic.last_res[idx[0]]; filename = t[3]
            path = os.path.join(self.client_logic.folder, filename)
            if os.path.exists(path):
                if not messagebox.askyesno("Sobrescrever?", "Substituir '{}'?".format(filename)): return
            threading.Thread(target=self.client_logic.download_file, args=(t[1], t[2], filename), daemon=True).start()

class NapsterClientLogic:
    def __init__(self, s_ip, s_port, nick, folder, p2p_port, gui):
        self.gui, self.folder, self.nick, self.p2p_port = gui, folder, nick, p2p_port
        self.running, self.last_res = True, []
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); self.s.connect((s_ip, s_port))
        threading.Thread(target=self.rx, daemon=True).start()
        threading.Thread(target=self.p2p_srv, daemon=True).start()
        threading.Thread(target=self.upd, daemon=True).start()
        self.send_up()

    def stop(self): self.running = False; self.s.close()
    def send_up(self):
        if not self.running: return
        try:
            files = [f for f in os.listdir(self.folder) if os.path.isfile(os.path.join(self.folder, f))]
            self.s.send(pickle.dumps({'type': 'register_update', 'nick': self.nick, 'files': files, 'p2p_port': self.p2p_port}))
        except: pass

    def upd(self):
        while self.running: time.sleep(30); self.send_up()

    def rx(self):
        while self.running:
            try:
                data = self.s.recv(16384)
                if not data: break
                msg = pickle.loads(data)
                if msg.get('type') == 'chat': self.gui.root.after(0, self.gui.append_chat, msg['msg'])
                elif msg.get('type') == 'search_res':
                    self.last_res = msg['data']
                    self.gui.list_res.delete(0, END)
                    for r in self.last_res: self.gui.list_res.insert(END, "{} ({})".format(r[3], r[0]))
                elif msg.get('type') == 'error':
                    self.gui.root.after(0, lambda: messagebox.showwarning("Aviso", msg.get('msg')))
                    if msg.get('msg') in ['KICKED', 'SERVER_SHUTDOWN']: self.gui.root.after(0, self.gui.disconnect)
            except: break

    def p2p_srv(self):
        ps = socket.socket(socket.AF_INET, socket.SOCK_STREAM); ps.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ps.bind(('0.0.0.0', self.p2p_port)); ps.listen(5)
        while self.running:
            ps.settimeout(1.0)
            try:
                c, _ = ps.accept(); f = c.recv(1024).decode(); p = os.path.join(self.folder, f)
                if os.path.isfile(p):
                    c.send(str(os.path.getsize(p)).zfill(15).encode())
                    with open(p, 'rb') as fd: c.sendall(fd.read())
                c.close()
            except: continue

    def download_file(self, ip, port, filename):
        try:
            ds = socket.socket(socket.AF_INET, socket.SOCK_STREAM); ds.connect((ip, port))
            ds.send(filename.encode()); fsize = int(ds.recv(15).decode()); bytes_rec = 0
            with open(os.path.join(self.folder, filename), 'wb') as f:
                while bytes_rec < fsize:
                    chunk = ds.recv(4096); f.write(chunk); bytes_rec += len(chunk)
                    self.gui.root.after(0, lambda v=(bytes_rec/fsize*100): self.gui.prog.configure(value=v))
            ds.close(); self.s.send(pickle.dumps({'type': 'stat_download'})); self.send_up()
            self.gui.root.after(0, self.gui.refresh_l); self.gui.root.after(0, lambda: self.gui.prog.configure(value=0))
            messagebox.showinfo("OK", "Download concluído!")
        except Exception as e: messagebox.showerror("Erro", str(e))

if __name__ == "__main__":
    root = Tk(); app = NapsterGUI(root); root.mainloop()