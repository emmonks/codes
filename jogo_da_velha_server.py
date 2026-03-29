import socket
import random

def servidor_dedicado():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    porta = int(input("Porta do servidor: "))
    servidor.bind(('', porta))
    servidor.listen(2)
    print("Servidor aguardando jogadores...")

    while True:
        # Conecta o primeiro jogador
        p1_conn, p1_addr = servidor.accept()
        print("Jogador 1 conectado:", p1_addr)
        p1_conn.send("Aguardando oponente...".encode())

        # Conecta o segundo jogador
        p2_conn, p2_addr = servidor.accept()
        print("Jogador 2 conectado:", p2_addr)

        # Sorteio: quem começa é 'O'
        jogadores = [p1_conn, p2_conn]
        random.shuffle(jogadores)
        p_o, p_x = jogadores[0], jogadores[1]

        p_o.send("START:O".encode())
        p_x.send("START:X".encode())

        tabuleiro = [" "] * 9
        turno_o = True

        while True:
            # Define quem joga agora e quem espera
            atual, oponente = (p_o, p_x) if turno_o else (p_x, p_o)
            
            try:
                # Recebe a jogada do jogador da vez
                jogada = atual.recv(1024).decode()
                # Repassa a jogada para o oponente
                oponente.send(jogada.encode())
                
                # Atualiza tabuleiro local para controle de fim de jogo (opcional no servidor)
                simbolo = "O" if turno_o else "X"
                tabuleiro[int(jogada)] = simbolo
                
                # Inverte o turno
                turno_o = not turno_o
            except:
                break # Conexão perdida

        print("Fim de partida ou desconexão.")
        p1_conn.close()
        p2_conn.close()

if __name__ == "__main__":
    servidor_dedicado()