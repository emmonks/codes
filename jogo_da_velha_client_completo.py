import socket

def exibir_tabuleiro(t):
    print("\n %s | %s | %s \n-----------" % (t[0], t[1], t[2]))
    print(" %s | %s | %s \n-----------" % (t[3], t[4], t[5]))
    print(" %s | %s | %s \n" % (t[6], t[7], t[8]))

def obter_jogada(tabuleiro, simbolo):
    while True:
        try:
            pos = int(input("Sua vez (%s). Escolha (0-8): " % simbolo))
            if 0 <= pos <= 8 and tabuleiro[pos] == " ": return str(pos)
            print("Posição inválida!")
        except ValueError: print("Digite um número.")

def rodar_cliente():
    nome = input("Seu nome: ")
    ip = input("IP do Servidor: ")
    porta = int(input("Porta: "))
    
    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((ip, porta))
            sock.send(nome.encode())
            tabuleiro = [" "] * 9
            finalizado = False

            while not finalizado:
                data = sock.recv(1024).decode()
                if not data: break

                # Processa cada mensagem separada por |
                mensagens = data.split("|")
                for msg in mensagens:
                    if not msg: continue
                    
                    if msg == "AGUARDE":
                        print("Aguardando oponente...")
                    elif msg.startswith("START:"):
                        _, meu_simbolo, oponente = msg.split(":")
                        seu_simbolo = "X" if meu_simbolo == "O" else "O"
                        print("\nContra: %s | Você: %s" % (oponente, meu_simbolo))
                        exibir_tabuleiro(tabuleiro)
                        if meu_simbolo == "O":
                            sock.send(obter_jogada(tabuleiro, meu_simbolo).encode())
                    elif msg.startswith("OK:"):
                        tabuleiro[int(msg.split(":")[1])] = meu_simbolo
                        exibir_tabuleiro(tabuleiro)
                    elif msg.startswith("OPONENTE:"):
                        tabuleiro[int(msg.split(":")[1])] = seu_simbolo
                        exibir_tabuleiro(tabuleiro)
                        # SÓ pede jogada se NÃO houver uma mensagem de FIM logo após no mesmo buffer
                        if "FIM:" not in data:
                            sock.send(obter_jogada(tabuleiro, meu_simbolo).encode())
                    elif msg.startswith("FIM:"):
                        res = msg.split(":")[1]
                        if res == "Empate": print("\nEMPATE!")
                        else: print("\n%s VENCEU!" % ("VOCÊ" if res == meu_simbolo else "OPONENTE"))
                        finalizado = True
                        break
            sock.close()
            if input("\nJogar novamente? (s/n): ").lower() != 's': break
        except Exception as e:
            print("Erro:", e)
            break

if __name__ == "__main__":
    rodar_cliente()