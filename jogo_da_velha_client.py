import socket

def exibir_tabuleiro(t):
    print("\n %s | %s | %s \n-----------" % (t[0], t[1], t[2]))
    print(" %s | %s | %s \n-----------" % (t[3], t[4], t[5]))
    print(" %s | %s | %s \n" % (t[6], t[7], t[8]))

def verificar_vencedor(t):
    v = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
    for a, b, c in v:
        if t[a] == t[b] == t[c] != " ": return t[a]
    return "Empate" if " " not in t else None

def cliente():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ip = input("IP do Servidor: ")
    porta = int(input("Porta: "))
    sock.connect((ip, porta))

    # Aguarda sinal de início do servidor
    msg = sock.recv(1024).decode()
    if "Aguardando" in msg:
        print(msg)
        msg = sock.recv(1024).decode()

    meu_simbolo = msg.split(":")[1]
    seu_simbolo = "X" if meu_simbolo == "O" else "O"
    turno_meu = (meu_simbolo == "O")
    
    print("Você é o jogador: %s" % meu_simbolo)
    tabuleiro = [" "] * 9

    while True:
        exibir_tabuleiro(tabuleiro)
        venc = verificar_vencedor(tabuleiro)
        if venc:
            print("Resultado: %s" % venc)
            break

        if turno_meu:
            pos = input("Sua vez (%s). Escolha (0-8): " % meu_simbolo)
            tabuleiro[int(pos)] = meu_simbolo
            sock.send(pos.encode())
        else:
            print("Aguardando oponente...")
            pos = sock.recv(1024).decode()
            tabuleiro[int(pos)] = seu_simbolo
        
        turno_meu = not turno_meu

    sock.close()

if __name__ == "__main__":
    cliente()