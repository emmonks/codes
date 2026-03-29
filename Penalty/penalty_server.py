import socket, threading, random, os, time

# --- ESTRUTURAS DE DADOS ---
historico_partidas = []
vitorias = {}
estatisticas = {}

def inicializar_jogador(nome):
    if nome not in estatisticas:
        estatisticas[nome] = {"gols": 0, "defesas": 0, "trave": 0, "travessao": 0, "fora": 0}
    if nome not in vitorias: vitorias[nome] = 0

def registrar_lance(batedor, goleiro, chu, defe, resultado):
    inicializar_jogador(batedor); inicializar_jogador(goleiro)
    # Log textual detalhado do lance
    log_txt = f"Batedor: {batedor:<10} (Mirou: {chu}) | Goleiro: {goleiro:<10} (Pulou: {defe}) -> {resultado}"
    
    if resultado == "GOL": estatisticas[batedor]["gols"] += 1
    elif resultado == "DEFESA": estatisticas[goleiro]["defesas"] += 1
    elif resultado == "TRAVE": estatisticas[batedor]["trave"] += 1
    elif resultado == "TRAVESSÃO": estatisticas[batedor]["travessao"] += 1
    elif resultado == "FORA": estatisticas[batedor]["fora"] += 1
    return log_txt

def gerenciar_penalty(p1_data, p2_data):
    c1, n1 = p1_data; c2, n2 = p2_data
    todas_posicoes = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "TRAVE", "TRAVESSÃO", "FORA"]

    while True:
        try:
            print(f"\n[PARTIDA] {n1} vs {n2} iniciada.")
            c1.send(f"SETUP:{n1}:{n2}|".encode()); c2.send(f"SETUP:{n1}:{n2}|".encode())
            placar = {n1: 0, n2: 0}; rodada = 1

            while True:
                b_sock, b_nome = (c1, n1) if rodada % 2 != 0 else (c2, n2)
                g_sock, g_nome = (c2, n2) if rodada % 2 != 0 else (c1, n1)
                
                if rodada == 11:
                    c1.send("MORTE_SUBITA|".encode()); c2.send("MORTE_SUBITA|".encode())

                b_sock.send("CHUTAR|".encode()); g_sock.send("DEFENDER|".encode())
                
                b_sock.settimeout(6.0); g_sock.settimeout(6.0)
                try: chu = b_sock.recv(1024).decode().strip()
                except: chu = random.choice(todas_posicoes)
                try: defe = g_sock.recv(1024).decode().strip()
                except: defe = str(random.randint(0, 8))
                b_sock.settimeout(None); g_sock.settimeout(None)
                
                if chu.isdigit():
                    res = "GOL" if int(chu) != int(defe) else "DEFESA"
                    if res == "GOL": placar[b_nome] += 1
                else: res = chu

                # Exibe o log textual da jogada
                log_lance = registrar_lance(b_nome, g_nome, chu, defe, res)
                tag = f"R{rodada}" if rodada <= 10 else f"ALT{rodada-10}"
                print(f"  {tag:5} | {log_lance} | Placar: {placar[n1]}x{placar[n2]}")
                
                pkg = f"LANCE:{b_nome}:{chu}:{g_nome}:{defe}:{res}|PLACAR:{placar[n1]}:{placar[n2]}|"
                c1.send(pkg.encode()); c2.send(pkg.encode())

                venc = None
                if rodada <= 10:
                    ch_rest_p1 = 5 - ((rodada // 2) + (rodada % 2))
                    ch_rest_p2 = 5 - (rodada // 2)
                    if placar[n1] > placar[n2] + ch_rest_p2: venc = n1
                    elif placar[n2] > placar[n1] + ch_rest_p1: venc = n2
                elif rodada % 2 == 0 and placar[n1] != placar[n2]:
                    venc = n1 if placar[n1] > placar[n2] else n2

                if venc:
                    vitorias[venc] += 1
                    historico_partidas.append(f"{n1} {placar[n1]} x {placar[n2]} {n2}")
                    print(f"[FIM] Vencedor: {venc} ({placar[n1]}x{placar[n2]})")
                    c1.send(f"FIM:{venc}|".encode()); c2.send(f"FIM:{venc}|".encode())
                    break
                rodada += 1

            # Lógica de Revanche Reativa
            time.sleep(1)
            c1.send("REPLAY?|".encode()); c2.send("REPLAY?|".encode())
            c1.settimeout(20); c2.settimeout(20)
            r1 = c1.recv(1024).decode().lower()
            r2 = c2.recv(1024).decode().lower()
            if 's' in r1 and 's' in r2: continue
            else: break
        except: break
    c1.close(); c2.close()

def comando_shutdown():
    while True:
        if input().strip().lower() == "shutdown":
            print("\n" + "═"*85 + "\nESTATÍSTICAS DO CAMPEONATO\n" + "═"*85)
            for n, v in sorted(vitorias.items(), key=lambda x: x[1], reverse=True):
                s = estatisticas.get(n, {"gols":0, "defesas":0, "trave":0, "travessao":0, "fora":0})
                print(f"{n:<18} | Vit: {v} | Gols: {s['gols']} | Def: {s['defesas']} | Erros: {s['trave']+s['travessao']+s['fora']}")
            os._exit(0)

def iniciar():
    print("\n" + "═"*85 + "\nPenalty em Rede - Server\n" + "═"*85)
    porta = int(input("Porta de escuta (ex: 5000): ") or 5000)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', porta)); s.listen(10)
    threading.Thread(target=comando_shutdown, daemon=True).start()
    print(f"[SVR] Aguardando conexões na porta {porta}...")
    print(f"[SVR] Digitar shutdown para encerrada o servidor a qualquer momento")
    while True:
        try:
            c1, _ = s.accept(); n1 = c1.recv(1024).decode(); c1.send("AGUARDE|".encode())
            c2, _ = s.accept(); n2 = c2.recv(1024).decode()
            threading.Thread(target=gerenciar_penalty, args=((c1,n1),(c2,n2)), daemon=True).start()
        except: break

if __name__ == "__main__": iniciar()