import socket
import random

def exibir_tabuleiro(t):
    print("\n %s | %s | %s " % (t[0], t[1], t[2]))
    print("-----------")
    print(" %s | %s | %s " % (t[3], t[4], t[5]))
    print("-----------")
    print(" %s | %s | %s \n" % (t[6], t[7], t[8]))

def verificar_vencedor(t):
    vitorias = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
    for v in vitorias:
        if t[v[0]] == t[v[1]] == t[v[2]] != " ":
            return t[v[0]]
    if " " not in t:
        return "Empate"
    return None

def jogar():
    escolha = input("Deseja ser (S)ervidor ou (C)liente? ").upper()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    if escolha == 'S':
        porta = int(input("Defina a porta: "))
        sock.bind(('', porta))
        sock.listen(1)
        print("Aguardando oponente...")
        conn, addr = sock.accept()
        print("Conectado por:", addr)
    else:
        ip = input("IP do servidor: ")
        porta = int(input("Porta: "))
        sock.connect((ip, porta))
        conn = sock

    while True:
        tabuleiro = [" "] * 9
        # Sorteio (realizado pelo servidor e enviado ao cliente)
        if escolha == 'S':
            quem_comeca = random.choice(['S', 'C'])
            conn.send(quem_comeca.encode())
        else:
            quem_comeca = conn.recv(1024).decode()

        meu_simbolo = 'O' if (escolha == quem_comeca) else 'X'
        seu_simbolo = 'X' if meu_simbolo == 'O' else 'O'
        turno_meu = (quem_comeca == escolha)

        print("Eu sou: %s" % meu_simbolo)
        
        while True:
            exibir_tabuleiro(tabuleiro)
            vencedor = verificar_vencedor(tabuleiro)
            
            if vencedor:
                if vencedor == "Empate": print("Deu velha!")
                else: print("Vencedor: %s" % vencedor)
                break

            if turno_meu:
                jogada = -1
                while jogada not in range(9) or tabuleiro[jogada] != " ":
                    try:
                        jogada = int(input("Sua vez (%s). Escolha posição (0-8): " % meu_simbolo))
                    except ValueError: continue
                tabuleiro[jogada] = meu_simbolo
                conn.send(str(jogada).encode())
            else:
                print("Aguardando jogada do oponente...")
                jogada = int(conn.recv(1024).decode())
                tabuleiro[jogada] = seu_simbolo
            
            turno_meu = not turno_meu

        novo_jogo = input("Jogar novamente? (s/n): ").lower()
        conn.send(novo_jogo.encode())
        resposta_oponente = conn.recv(1024).decode()

        if novo_jogo != 's' or resposta_oponente != 's':
            print("Encerrando conexão...")
            break

    conn.close()
    sock.close()

if __name__ == "__main__":
    jogar()