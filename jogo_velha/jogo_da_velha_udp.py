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
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # SOCK_DGRAM para UDP

    if escolha == 'S':
        porta = int(input("Defina a porta para ouvir: "))
        sock.bind(('', porta))
        print("Aguardando contato do cliente...")
        # O servidor precisa receber o primeiro "Oi" para saber o IP/Porta do cliente
        data, addr_oponente = sock.recvfrom(1024)
        print("Conectado com o cliente em:", addr_oponente)
    else:
        ip = input("IP do servidor: ")
        porta = int(input("Porta: "))
        addr_oponente = (ip, porta)
        # Cliente envia primeiro pacote para o servidor registrar seu endereço
        sock.sendto("CONECTAR".encode(), addr_oponente)

    while True:
        tabuleiro = [" "] * 9
        
        # Sorteio (Servidor decide e envia)
        if escolha == 'S':
            quem_comeca = random.choice(['S', 'C'])
            sock.sendto(quem_comeca.encode(), addr_oponente)
        else:
            msg, addr = sock.recvfrom(1024)
            quem_comeca = msg.decode()

        meu_simbolo = 'O' if (escolha == quem_comeca) else 'X'
        seu_simbolo = 'X' if meu_simbolo == 'O' else 'O'
        turno_meu = (quem_comeca == escolha)

        print("--- NOVO JOGO ---")
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
                        jogada = int(input("Sua vez (%s). Posição (0-8): " % meu_simbolo))
                    except ValueError: continue
                tabuleiro[jogada] = meu_simbolo
                sock.sendto(str(jogada).encode(), addr_oponente)
            else:
                print("Aguardando oponente...")
                msg, addr = sock.recvfrom(1024)
                tabuleiro[int(msg.decode())] = seu_simbolo
            
            turno_meu = not turno_meu

        # Reiniciar ou Encerrar
        msg_fim = input("Deseja jogar novamente? (s/n): ").lower()
        sock.sendto(msg_fim.encode(), addr_oponente)
        
        print("Aguardando resposta do oponente...")
        resp, addr = sock.recvfrom(1024)
        if msg_fim != 's' or resp.decode() != 's':
            print("Encerrando...")
            break

    sock.close()

if __name__ == "__main__":
    jogar()