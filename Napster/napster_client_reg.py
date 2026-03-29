import socket, threading, pickle, os, time, sys

class NapsterClientConsole:
    def __init__(self, s_ip, s_port, nick, folder, p2p_port):
        self.server_addr = (s_ip, s_port)
        self.nick, self.p2p_port = nick, p2p_port
        self.folder = folder if folder else "shared"
        self.running, self.last_results = True, []
        
        if not os.path.exists(self.folder): os.makedirs(self.folder)
        
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect(self.server_addr)
        
        threading.Thread(target=self.receive_thread, daemon=True).start()
        threading.Thread(target=self.p2p_server_thread, daemon=True).start()
        threading.Thread(target=self.auto_update_loop, daemon=True).start()
        self.send_update()

    def send_update(self):
        try:
            files = [f for f in os.listdir(self.folder) if os.path.isfile(os.path.join(self.folder, f))]
            self.s.send(pickle.dumps({'type': 'register_update', 'nick': self.nick, 'files': files, 'p2p_port': self.p2p_port}))
        except: pass

    def auto_update_loop(self):
        while self.running: 
            time.sleep(30)
            self.send_update()

    def receive_thread(self):
        while self.running:
            try:
                data = self.s.recv(16384)
                if not data: break
                msg = pickle.loads(data)
                if msg['type'] == 'chat': 
                    print("\n[CHAT] {}\n> ".format(msg['msg']), end="")
                elif msg['type'] == 'search_res': 
                    self.last_results = msg['data']
                elif msg['type'] == 'error':
                    print("\n[AVISO] {}".format(msg['msg']))
                    if msg['msg'] in ['NICK_DUPLICADO', 'KICKED', 'SERVER_SHUTDOWN']: 
                        os._exit(0)
            except: break

    def p2p_server_thread(self):
        ps = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ps.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ps.bind(('0.0.0.0', self.p2p_port))
        ps.listen(5)
        while self.running:
            ps.settimeout(1.0)
            try:
                c, _ = ps.accept()
                fname = c.recv(1024).decode()
                path = os.path.join(self.folder, fname)
                if os.path.isfile(path):
                    c.send(str(os.path.getsize(path)).zfill(15).encode())
                    with open(path, 'rb') as f: c.sendall(f.read())
                c.close()
            except: continue

    def download_file(self, ip, port, filename):
        dest_path = os.path.join(self.folder, filename)
        
        # Lógica de Sobrescrita Adicionada
        if os.path.exists(dest_path):
            resp = input("\n[!] O arquivo '{}' ja existe. Sobrescrever? (y/n): ".format(filename))
            if resp.lower() != 'y':
                print("Download cancelado pelo usuario.")
                return

        try:
            ds = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ds.connect((ip, port))
            ds.send(filename.encode())
            fsize = int(ds.recv(15).decode())
            bytes_rec = 0
            with open(dest_path, 'wb') as f:
                while bytes_rec < fsize:
                    chunk = ds.recv(4096)
                    f.write(chunk)
                    bytes_rec += len(chunk)
            
            self.s.send(pickle.dumps({'type': 'stat_download'}))
            self.send_update()
            print("\n[OK] Download de '{}' finalizado.".format(filename))
        except Exception as e: 
            print("\n[ERRO P2P] {}".format(e))

def menu():
    print("=== NAPSTER CONSOLE CLIENT ===")
    srv_ip = input("IP Servidor: ")
    srv_port = int(input("Porta Servidor: "))
    nick = input("Nick: ")
    folder = input("Pasta Shared (Enter para 'shared'): ")
    
    print("Configuracao de Porta P2P:")
    print("1: Porta Aleatoria (Recomendado) | 2: Porta Fixa")
    p_opt = input("> ")
    if p_opt == '2':
        p2p_port = int(input("Porta P2P desejada: "))
    else:
        s_temp = socket.socket()
        s_temp.bind(('', 0))
        p2p_port = s_temp.getsockname()[1]
        s_temp.close()
        print("Porta P2P selecionada: {}".format(p2p_port))
    
    cli = NapsterClientConsole(srv_ip, srv_port, nick, folder, p2p_port)

    while True:
        print("\n1:Busca Simples | 2:Busca Regex | 3:Busca Usuario | 4:Arquivos Locais | 5:Chat | 6:Sair")
        cmd = input("> ")
        
        if cmd in ['1', '2', '3']:
            stype = 'regex' if cmd == '2' else 'simple'
            reg = input(r"Termo de busca/Regex: ") if cmd != '3' else ""
            usr = input("Nick do usuario alvo: ") if cmd == '3' else ""
            
            cli.s.send(pickle.dumps({'type': 'search', 'query': reg, 'user_filter': usr, 'search_type': stype}))
            time.sleep(1.2) # Aguarda retorno do servidor
            
            if not cli.last_results:
                print("Nenhum arquivo encontrado.")
                continue

            print("\nResultados encontrados:")
            for i, f in enumerate(cli.last_results):
                print("{}. {} (Dono: {})".format(i, f[3], f[0]))
            
            idx = input("\nIndice p/ download ou 'c' para cancelar: ")
            if idx.lower() == 'c':
                print("Operacao cancelada.")
                continue
            
            if idx.isdigit() and int(idx) < len(cli.last_results):
                target = cli.last_results[int(idx)]
                cli.download_file(target[1], target[2], target[3])
        
        elif cmd == '4':
            print("\nArquivos em '{}':".format(cli.folder))
            files = [f for f in os.listdir(cli.folder) if os.path.isfile(os.path.join(cli.folder, f))]
            if not files:
                print("Pasta vazia.")
            for f in files:
                size = os.path.getsize(os.path.join(cli.folder, f))
                print("- {} ({} bytes)".format(f, size))
        
        elif cmd == '5':
            msg = input("Mensagem para o Chat Global: ")
            if msg:
                cli.s.send(pickle.dumps({'type': 'chat', 'msg': msg}))
        
        elif cmd == '6':
            print("Encerrando...")
            os._exit(0)

if __name__ == "__main__":
    menu()