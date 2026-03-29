import socket, threading, pickle, os, sys, time, re

class NapsterServer:
    def __init__(self):
        print("=== SERVIDOR NAPSTER ADMINISTRATIVO ===")
        try:
            self.port = int(input("Porta de escuta [5000]: ") or "5000")
        except:
            self.port = 5000
            
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('0.0.0.0', self.port))
        self.server.listen(15)
        
        self.clients = {} 
        self.total_downloads = 0
        self.start_time = time.time()
        self.running = True

    def log(self, tag, message):
        timestamp = time.strftime('%H:%M:%S')
        print("\n[{}] [{}] {}\nSERVDOR> ".format(timestamp, tag, message), end="")

    def show_help(self):
        print("\n" + "="*45)
        print("      COMANDOS DE ADMINISTRAÇÃO")
        print("="*45)
        print("stats    - Resumo de usuários e downloads")
        print("listall  - Lista todos os arquivos da rede")
        print("kick <n> - Expulsa usuário pelo Nick")
        print("help     - Mostra esta lista")
        print("shutdown - Encerra o servidor")
        print("="*45 + "\n")

    def get_stats_report(self):
        uptime = time.strftime("%H:%M:%S", time.gmtime(time.time() - self.start_time))
        report = "\n" + "="*30 + "\n"
        report += "--- RELATÓRIO DE SESSÃO ---\n"
        report += "Tempo de Atividade: {}\n".format(uptime)
        report += "Total de Downloads: {}\n".format(self.total_downloads)
        report += "Usuários Ativos no momento: {}\n".format(len(self.clients))
        report += "="*30 + "\n"
        return report

    def handle_client(self, conn, addr):
        nick = "Desconhecido"
        try:
            while self.running:
                data = conn.recv(16384)
                if not data: break
                req = pickle.loads(data)

                if req['type'] == 'register_update':
                    temp_nick = req['nick']
                    if any(info['nick'].lower() == temp_nick.lower() for c, info in self.clients.items() if c != conn):
                        conn.send(pickle.dumps({'type': 'error', 'msg': 'NICK_DUPLICADO'}))
                        continue
                    
                    is_new = conn not in self.clients
                    self.clients[conn] = {'nick': temp_nick, 'ip': addr[0], 'p2p_port': req['p2p_port'], 'files': req['files']}
                    nick = temp_nick
                    if is_new: self.log("CONEXÃO", "Usuário '{}' entrou".format(nick))
                    conn.send(pickle.dumps({'type': 'success'}))

                elif req['type'] == 'search':
                    q, u, stype = req.get('query', ""), req.get('user_filter', "").lower(), req.get('search_type', 'simple')
                    self.log("BUSCA", "'{}' buscou '{}'".format(nick, q))
                    res = []
                    try:
                        if stype == 'regex': pattern = re.compile(q or ".*", re.IGNORECASE)
                        for c, info in self.clients.items():
                            if u and u != info['nick'].lower(): continue
                            for f in info['files']:
                                if (stype == 'regex' and pattern.search(f)) or (stype == 'simple' and q.lower() in f.lower()):
                                    res.append((info['nick'], info['ip'], info['p2p_port'], f))
                    except: pass
                    conn.send(pickle.dumps({'type': 'search_res', 'data': res}))

                elif req['type'] == 'stat_download':
                    self.total_downloads += 1
                    self.log("P2P", "Download concluído por '{}'".format(nick))

                elif req['type'] == 'chat':
                    msg = pickle.dumps({'type': 'chat', 'msg': "{}: {}".format(nick, req['msg'])})
                    for c in self.clients:
                        if c != conn: c.send(msg)
        except: pass
        finally:
            if conn in self.clients: del self.clients[conn]
            conn.close()

    def console_cmd(self):
        self.show_help()
        while self.running:
            try:
                line = input("SERVDOR> ").strip().split(" ", 1)
                cmd = line[0].lower()
                if not cmd: continue

                if cmd == 'stats':
                    print(self.get_stats_report())
                elif cmd == 'listall':
                    print("\n--- TODOS OS ARQUIVOS NA REDE ---")
                    for c, i in self.clients.items():
                        print("[{}] {}".format(i['nick'], i['files']))
                    print("-" * 30)
                elif cmd == 'kick' and len(line) > 1:
                    target = line[1].lower()
                    for c, info in list(self.clients.items()):
                        if info['nick'].lower() == target:
                            c.send(pickle.dumps({'type': 'error', 'msg': 'KICKED'})); c.close()
                elif cmd == 'help':
                    self.show_help()
                elif cmd == 'shutdown':
                    print("\n[!] Notificando clientes e encerrando...")
                    msg_shutdown = pickle.dumps({'type': 'error', 'msg': 'SERVER_SHUTDOWN'})
                    for c in list(self.clients.keys()):
                        try:
                            c.send(msg_shutdown)
                            c.close()
                        except: pass
                    print(self.get_stats_report())
                    self.running = False
                    time.sleep(1)
                    os._exit(0)
            except: break

    def run(self):
        threading.Thread(target=self.console_cmd, daemon=True).start()
        self.log("SISTEMA", "Servidor ativo na porta {}".format(self.port))
        while self.running:
            try:
                conn, addr = self.server.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr)).start()
            except: break

if __name__ == "__main__": NapsterServer().run()