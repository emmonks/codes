import socket
import threading
import sys

class ServidorChat:
    def __init__(self):
        self.clientes = {}   # {socket: nickname}
        self.canais = {"#default": []}
        self.rodando = True
        self.sock = None
        self.porta = 5005

    def log(self, mensagem):
        print("[LOG] {}".format(mensagem))

    def broadcast_canal(self, canal, mensagem, remetente_sock=None):
        for cliente in self.canais.get(canal, []):
            if cliente != remetente_sock:
                try:
                    cliente.send(mensagem.encode())
                except:
                    self.remover_cliente(cliente)

    def enviar_privado(self, nick_destino, mensagem, remetente_nick):
        for sock, nick in self.clientes.items():
            if nick.lower() == nick_destino.lower():
                try:
                    sock.send("[PV de {}]: {}".format(remetente_nick, mensagem).encode())
                    return True
                except:
                    return False
        return False

    def gerenciar_cliente(self, conn, addr):
        try:
            # O servidor agora apenas espera o nick ser enviado pelo cliente
            nick = conn.recv(1024).decode().strip()
            
            # Se o cliente enviar algo vazio ou erro, desconecta
            if not nick: return

            self.clientes[conn] = nick
            self.canais["#default"].append(conn)
            
            self.log("Usuário '{}' conectado".format(nick))
            self.broadcast_canal("#default", "--> {} entrou no canal #default".format(nick))
            canal_atual = "#default"

            # Agora entra no loop de comandos
            while self.rodando:
                data = conn.recv(1024).decode()
                if not data: break

                # COMANDO: /join
                if data.startswith("/join "):
                    novo_canal = data.split(" ")[1]
                    if conn in self.canais[canal_atual]:
                        self.canais[canal_atual].remove(conn)
                    if novo_canal not in self.canais:
                        self.canais[novo_canal] = []
                        self.log("Novo canal criado: {}".format(novo_canal))
                    self.canais[novo_canal].append(conn)
                    self.log("'{}' moveu para {}".format(nick, novo_canal))
                    canal_atual = novo_canal
                    conn.send("Você entrou em {}".format(canal_atual).encode())
                
                # COMANDO: /msg (Privado) - CORRIGIDO
                elif data.startswith("/msg "):
                    partes = data.split(" ", 2)
                    if len(partes) >= 3:
                        destino, msg_pv = partes[1], partes[2]
                        sucesso = self.enviar_privado(destino, msg_pv, nick)
                        if sucesso:
                            conn.send("[PV para {}]: {}".format(destino, msg_pv).encode())
                        else:
                            conn.send("Erro: Usuário '{}' não encontrado.".format(destino).encode())
                
                # COMANDO: /list - NOVO
                elif data.strip() == "/list":
                    lista_canais = ", ".join(self.canais.keys())
                    lista_users = ", ".join(self.clientes.values())
                    res = "\n--- LISTA IRC ---\nCanais: {}\nUsuários: {}\n----------------".format(lista_canais, lista_users)
                    conn.send(res.encode())
                
                # MENSAGEM COMUM
                else:
                    msg_formatada = "[{} @ {}]: {}".format(nick, canal_atual, data)
                    self.broadcast_canal(canal_atual, msg_formatada, conn)
        except:
            pass
        finally:
            self.remover_cliente(conn)

    def remover_cliente(self, conn):
        if conn in self.clientes:
            nick = self.clientes[conn]
            for c in self.canais:
                if conn in self.canais[c]: self.canais[c].remove(conn)
            del self.clientes[conn]
            conn.close()
            self.log("Usuário '{}' saiu.".format(nick))

    def comando_servidor(self):
        while self.rodando:
            cmd = input().strip().lower()
            if cmd == "shutdown":
                self.log("Desligando...")
                self.rodando = False
                # Trigger para destravar o accept()
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect(('127.0.0.1', self.porta))
                    s.close()
                except: pass
                self.sock.close()
                sys.exit()

    def iniciar(self):
        self.porta = int(input("Porta do servidor: "))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', self.porta))
        self.sock.listen(5)
        self.log("Iniciado na porta {}".format(self.porta))
        threading.Thread(target=self.comando_servidor, daemon=True).start()
        
        while self.rodando:
            try:
                conn, addr = self.sock.accept()
                if not self.rodando: break
                threading.Thread(target=self.gerenciar_cliente, args=(conn, addr), daemon=True).start()
            except: break

if __name__ == "__main__":
    ServidorChat().iniciar()