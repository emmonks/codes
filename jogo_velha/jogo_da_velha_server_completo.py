import socket
import threading
import random
import os

def verificar_vencedor(t):
    v = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
    for a, b, c in v:
        if t[a] == t[b] == t[c] != " ": return t[a]
    return "Empate" if " " not in t else None

def gerenciar_partida(p1_data, p2_data, sala_id):
    jogadores = [p1_data, p2_data]
    random.shuffle(jogadores)
    (p_o, addr_o, nome_o), (p_x, addr_x, nome_x) = jogadores[0], jogadores[1]
    
    # Mapeamento para o log saber quem é quem
    nomes = {"O": nome_o, "X": nome_x}
    
    try:
        p_o.send(("START:O:" + nome_x + "|").encode())
        p_x.send(("START:X:" + nome_o + "|").encode())
        
        tabuleiro = [" "] * 9
        turno_o = True
        print("\n[SALA %s] Partida Iniciada: %s (O) vs %s (X)" % (sala_id, nome_o, nome_x))

        while True:
            atual, oponente = (p_o, p_x) if turno_o else (p_x, p_o)
            simbolo_atual = "O" if turno_o else "X"
            nome_atual = nomes[simbolo_atual]
            
            data = atual.recv(1024).decode()
            if not data: break

            try:
                jogada = int(data)
                tabuleiro[jogada] = simbolo_atual
                
                # LOG DA JOGADA NO CONSOLE
                print("[SALA %s] %s (%s) jogou na posição %d" % (sala_id, nome_atual, simbolo_atual, jogada))
                
                res = verificar_vencedor(tabuleiro)
                if res:
                    # Envia pacotes de fim
                    atual.send(("OK:%d|FIM:%s|" % (jogada, res)).encode())
                    oponente.send(("OPONENTE:%d|FIM:%s|" % (jogada, res)).encode())
                    
                    # LOG DO VENCEDOR COM NOME
                    if res == "Empate":
                        print("[SALA %s] Fim de jogo: EMPATE" % sala_id)
                    else:
                        print("[SALA %s] Fim de jogo: VITORIA DE %s (%s)" % (sala_id, nomes[res], res))
                    break
                else:
                    atual.send(("OK:%d|" % jogada).encode())
                    oponente.send(("OPONENTE:%d|" % jogada).encode())
                    turno_o = not turno_o
            except ValueError:
                continue
    except Exception as e:
        print("[SALA %s] Erro/Desconexão: %s" % (sala_id, e))
    finally:
        p_o.close()
        p_x.close()

def iniciar_servidor():
    porta = int(input("Defina a porta do servidor: "))
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(('', porta))
    servidor.listen(10)
    print("[STATUS] Servidor rodando na porta %d. Digite 'shutdown' para parar." % porta)

    # Thread para comando de encerramento
    def cmd():
        while True:
            if input().lower() == 'shutdown': os._exit(0)
    threading.Thread(target=cmd, daemon=True).start()

    contador = 1
    while True:
        try:
            c1, a1 = servidor.accept()
            n1 = c1.recv(1024).decode()
            c1.send("AGUARDE|".encode())
            
            c2, a2 = servidor.accept()
            n2 = c2.recv(1024).decode()
            
            # Cada par de jogadores ganha sua própria Thread (Sala)
            threading.Thread(target=gerenciar_partida, args=((c1, a1, n1), (c2, a2, n2), str(contador))).start()
            contador += 1
        except:
            break

if __name__ == "__main__":
    iniciar_servidor()