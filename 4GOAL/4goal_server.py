import socket, threading, pickle, math, time, random, sys, pygame, signal, argparse

WIDTH, HEIGHT = 800, 600
BALL_SPEED = 23
ROUND_DURATION = 45

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", type=int, default=5555)
parser.add_argument("-v", "--vitorias", type=int, default=5) # Padrão 5 vitórias
parser.add_argument("-z", "--zagueiros", type=int, choices=[0, 1], default=1) # 1=Sim, 0=Não
args = parser.parse_args()

WIN_LIMIT = args.vitorias
PORT = args.port
USA_ZAGUEIROS = bool(args.zagueiros) # Converte 0/1 para False/True

# --- NOVO: Lista de imagens disponíveis ---
PLAYER_SPRITES = ["jogador1.png", "jogador2.png", "jogador3.png", "jogador4.png", "jogador5.png", "jogador6.png"]

class GoalieLogic:
    def __init__(self, x, y, w, h, axis):
        self.rect = pygame.Rect(x, y, w, h)
        self.axis = axis
        self.randomize_level()

    def randomize_level(self):
        self.level = random.randint(0, 3)
        stats = {0: {"base": 3.0, "react": 0.2}, 1: {"base": 4.5, "react": 0.4},
                 2: {"base": 6.5, "react": 0.6}, 3: {"base": 8.5, "react": 0.9}}
        self.base_speed = stats[self.level]["base"]; self.react_factor = stats[self.level]["react"]

    def update(self, ball_pos, ball_vel):
        target = ball_pos[0] if self.axis == 'h' else ball_pos[1]
        current = self.rect.centerx if self.axis == 'h' else self.rect.centery
        if abs(current - target) > 5:
            move = self.base_speed if current < target else -self.base_speed
            if self.axis == 'h': self.rect.x = max(min(self.rect.x + move, 500 - self.rect.w), 300)
            else: self.rect.y = max(min(self.rect.y + move, 400 - self.rect.h), 200)

class DefenderLogic:
    def __init__(self, x, y, x_min=0, x_max=800):
        self.rect = pygame.Rect(x, y, 35, 35)
        self.speed = 2
        self.x_min = x_min
        self.x_max = x_max

    def update(self, ball_pos, ball_owner):
        # O zagueiro só persegue a bola se ela estiver dentro da sua zona X
        target_x = max(self.x_min, min(ball_pos[0], self.x_max))
        target_y = ball_pos[1]
        
        # --- ADICIONADO: Margem de tolerância (10px) para evitar tremedeira ---
        if abs(self.rect.centerx - target_x) > 10:
            if self.rect.centerx < target_x:
                self.rect.x += self.speed
            else:
                self.rect.x -= self.speed
                
        if abs(self.rect.centery - target_y) > 10:
            if self.rect.centery < target_y:
                self.rect.y += self.speed
            else:
                self.rect.y -= self.speed

        # Lógica de Desarme (Espirro)
        if ball_owner is not None:
            dist = math.hypot(self.rect.centerx - ball_pos[0], self.rect.centery - ball_pos[1])
            if dist < 30:
                angle = random.uniform(0, 2*math.pi)
                game_state["ball_vel"] = [math.cos(angle)*25, math.sin(angle)*25]
                game_state["ball_owner"] = None

def update_defender_count():
    if not USA_ZAGUEIROS:
        game_state["defenders"] = []
        return
    num_players = len(game_state["players"])
    
    if num_players <= 3:
        # Apenas 1 zagueiro no centro, campo inteiro
        game_state["defenders"] = [DefenderLogic(400, 300, 0, 800)]
    else:
        # 2 zagueiros: um na esquerda (Oeste), outro na direita (Leste)
        game_state["defenders"] = [
            DefenderLogic(200, 300, 0, 400),   # Zagueiro Oeste
            DefenderLogic(600, 300, 400, 800)  # Zagueiro Leste
        ]

game_state = {
    "players": {}, "last_seen": {}, "ball_pos": [400, 300], "ball_vel": [0, 0],
    "ball_owner": None, "last_kicker": None, "last_goal_name": "", "goal_event": False,
    "goalies": [GoalieLogic(375, 15, 50, 25, 'h'), GoalieLogic(375, 560, 50, 25, 'h'),
                GoalieLogic(15, 275, 25, 50, 'v'), GoalieLogic(760, 275, 25, 50, 'v')],
    "defenders": [],
    "ultimo_vencedor_anuncio": "",
    "goal_timer": 0 ,
    "steal_event": False,
    "save_event": False,
    "whistle_event": False,
    "current_champion_id": None, # ID do jogador que ganhou o último troféu
    "tournament_ended": False,    # Trava o jogo quando alguém atinge o WIN_LIMIT
    "map_type": random.choice(["STRIPES", "CHECKERBOARD", "SOLID"]),
    "scores": {}, "time_left": ROUND_DURATION, "status": "PLAYING", "active": True
}


def physics_loop():
    last_t = time.time()
    while game_state["active"]:
        if game_state["status"] == "PLAYING":
            dt = time.time() - last_t
            last_t = time.time()
            game_state["time_left"] -= dt
            if game_state["time_left"] <= 0 and game_state["status"] == "PLAYING":
                game_state["status"] = "ENDED"
                game_state["whistle_event"] = True
                # Encontrar quem fez mais gols NESTE round
                vencedor_id = None
                max_gols_round = -1

                for pid, s in game_state["scores"].items():
                    if s["gols_round"] > max_gols_round:
                        max_gols_round = s["gols_round"]
                        vencedor_id = pid
                    elif s["gols_round"] == max_gols_round: # Empate
                        vencedor_id = None # Opcional: tratar empate
            
                if vencedor_id is not None and max_gols_round > 0:
                    game_state["scores"][vencedor_id]["vitorias"] += 1
                    nome_vencedor = game_state["scores"][vencedor_id]["name"]
                    game_state["ultimo_vencedor_anuncio"] = nome_vencedor
                    
                    # Checagem de Campeão (Agora dentro do bloco único)
                    if game_state["scores"][vencedor_id]["vitorias"] >= WIN_LIMIT:
                        game_state["tournament_ended"] = True
                        game_state["current_champion_id"] = vencedor_id
                        print(f"TORNEIO ENCERRADO! Campeão: {nome_vencedor}")
                else:
                    game_state["ultimo_vencedor_anuncio"] = "EMPATE"
            
            # --- MOVIMENTAÇÃO DA BOLA ---
            if game_state["ball_owner"] is None:
                game_state["ball_pos"][0] += game_state["ball_vel"][0]
                game_state["ball_pos"][1] += game_state["ball_vel"][1]
                
                # Atrito
                game_state["ball_vel"][0] *= 0.99
                game_state["ball_vel"][1] *= 0.99

                # Bordas
                if game_state["ball_pos"][0] <= 20:
                    game_state["ball_pos"][0] = 20; game_state["ball_vel"][0] *= -0.8
                elif game_state["ball_pos"][0] >= 780:
                    game_state["ball_pos"][0] = 780; game_state["ball_vel"][0] *= -0.8
                
                if game_state["ball_pos"][1] <= 20:
                    game_state["ball_pos"][1] = 20; game_state["ball_vel"][1] *= -0.8
                elif game_state["ball_pos"][1] >= 580:
                    game_state["ball_pos"][1] = 580; game_state["ball_vel"][1] *= -0.8
            
            
            # --- CLAMPING DOS JOGADORES ---
            for p_id in list(game_state["players"].keys()):
                p = game_state["players"][p_id]
                p["pos"][0] = max(20, min(p["pos"][0], 745))
                p["pos"][1] = max(20, min(p["pos"][1], 545))

            # --- GOLEIROS E COLISÃO ---
            # --- GOLEIROS E COLISÃO (AJUSTADO) ---
            ball_r = pygame.Rect(game_state["ball_pos"][0]-8, game_state["ball_pos"][1]-8, 16, 16)

            for g in game_state["goalies"]:
                g.update(game_state["ball_pos"], game_state["ball_vel"])
                
                if ball_r.colliderect(g.rect):
                    # Define qual eixo inverter: se o goleiro é vertical (v), rebate no X (0). 
                    # Se horizontal (h), rebate no Y (1).
                    idx = 0 if g.axis == 'v' else 1
                    
                    # Inverte a direção e REDUZ a força (0.5 = 50% da velocidade original)
                    game_state["ball_vel"][idx] *= -0.5
                    game_state["save_event"] = True
                    
                    # Amortece levemente o outro eixo também para um efeito mais realista
                    outro_idx = 1 - idx
                    game_state["ball_vel"][outro_idx] *= 0.8

                    # --- LÓGICA ANTI-GRUDE ---
                    # Move a bola para fora do retângulo do goleiro imediatamente
                    # para evitar colisões múltiplas no mesmo ciclo
                    overlap = 0
                    if g.axis == 'v':
                        # Se bateu na esquerda ou direita do goleiro
                        if game_state["ball_pos"][0] < g.rect.centerx:
                            game_state["ball_pos"][0] = g.rect.left - 9
                        else:
                            game_state["ball_pos"][0] = g.rect.right + 9
                    else:
                        # Se bateu em cima ou embaixo do goleiro
                        if game_state["ball_pos"][1] < g.rect.centery:
                            game_state["ball_pos"][1] = g.rect.top - 9
                        else:
                            game_state["ball_pos"][1] = g.rect.bottom + 9
            
            #if not game_state["defenders"]: 
            #    update_defender_count() # Garante que haja pelo menos um se a lista estiver vazia

            for d in game_state["defenders"]:
                d.update(game_state["ball_pos"], game_state["ball_owner"])
            

            # --- DETECÇÃO DE GOL ---
            nets = [
                (pygame.Rect(300, 0, 200, 20), "NORTE"),
                (pygame.Rect(300, 580, 200, 20), "SUL"),
                (pygame.Rect(0, 200, 20, 200), "OESTE"),
                (pygame.Rect(780, 200, 20, 200), "LESTE")
            ]
            
            POSICOES_RESET = [
                (200, 150), (600, 150),  # Topo esquerda e direita
                (400, 300),              # Centro
                (200, 450), (600, 450)   # Baixo esquerda e direita
            ]
            for net_rect, side_name in nets:
                if ball_r.colliderect(net_rect):
                    game_state["whistle_event"] = True
                    game_state["goal_event"] = True
                    # 1. Identifica quem marcou PRIMEIRO
                    scorer_id = game_state.get("last_kicker")
                    nome_marcador = "ZAGUEIRO" # Default caso seja gol contra ou sem dono

                    if scorer_id in game_state["scores"]:
                        scorer = game_state["scores"][scorer_id]
                        scorer["gols"] += 1
                        scorer["gols_round"] += 1
                        nome_marcador = scorer["name"]

                    # 2. Atualiza o estado de Gol
                    game_state["goal_event"] = True
                    game_state["goal_end_time"] = time.time() + 2.0
                    game_state["last_goal_name"] = nome_marcador

                    # 3. Reset Físico (Isso evita que a bola fique presa)
                    nova_pos = random.choice(POSICOES_RESET)
                    game_state["ball_pos"] = list(nova_pos)
                    game_state["ball_vel"] = [0, 0]
                    game_state["ball_owner"] = None
                    game_state["last_kicker"] = None
                    
                    print(f"GOL DE {nome_marcador} na rede {side_name}!")
                    break


            agora = time.time()
        
        for pid in list(game_state["last_seen"].keys()):
            if agora - game_state["last_seen"][pid] > 10: 
                print(f"Limpando rastro do jogador {pid} por inatividade.")
                if pid in game_state["players"]: del game_state["players"][pid]
                if pid in game_state["last_seen"]: del game_state["last_seen"][pid]
                if pid in game_state["scores"]: del game_state["scores"][pid]
                update_defender_count()

        if game_state.get("goal_event"):
            if time.time() > game_state.get("goal_end_time", 0):
                game_state["goal_event"] = False

        time.sleep(0.016)
        game_state["steal_event"] = False
        game_state["save_event"] = False
        game_state["whistle_event"] = False


def handle_client(conn, addr, p_id):
    conn.settimeout(5.0)
    name = f"P{p_id}"
    try:
        # --- Limite de 6 jogadores ---
        if len(game_state["players"]) >= 6:
            conn.send(str(-1).encode())
            conn.close()
            return
            
        conn.send(str(p_id).encode())
        game_state["last_seen"][p_id] = time.time()
        sprite_idx = p_id % len(PLAYER_SPRITES)
        if p_id not in game_state["scores"]: 
                    sprite_idx = p_id % len(PLAYER_SPRITES)
                    game_state["scores"][p_id] = {
                        "name": name, 
                        "gols": 0, 
                        "vitorias": 0,
                        "gols_round": 0,
                        "sprite": PLAYER_SPRITES[sprite_idx]
                    }
        update_defender_count()
        
        while game_state["active"]:
            try:
                raw = conn.recv(16384)
                if not raw: break
                
                data = pickle.loads(raw)
                game_state["last_seen"][p_id] = time.time()
                
#                name = data["name"][:3]
                client_name = data.get("name", f"P{p_id}")[:3]


                
                # Verificar se o nome já existe
                name_exists = any(p["name"] == client_name for id_p, p in game_state["players"].items() if id_p != p_id)
                if name_exists:
                    client_name = f"{client_name}{p_id}"
                # 3. ATUALIZAÇÃO CRÍTICA: Sincroniza o nome no placar (scores)
                if p_id in game_state["scores"]:
                    game_state["scores"][p_id]["name"] = client_name
                # Atualiza no dicionário de players também
                game_state["players"][p_id] = {"pos": data["pos"], "name": client_name}
                
                # 4. Atualiza a variável local 'name' para o restante da lógica
                name = client_name
                
                #if p_id not in game_state["scores"]: 
                #    sprite_idx = p_id % len(PLAYER_SPRITES)
                #    game_state["scores"][p_id] = {
                #        "name": name, 
                #        "gols": 0, 
                #        "vitorias": 0,
                #        "gols_round": 0,
                #        "sprite": PLAYER_SPRITES[sprite_idx]
                #    }
                
                # --- LÓGICA DE RESTART ---
                if data.get("restart") and game_state["status"] == "ENDED":
                    if game_state["tournament_ended"]:
                        for p in game_state["scores"].values():
                            p["gols"] = 0
                            p["vitorias"] = 0
                            p["gols_round"] = 0
                        game_state["tournament_ended"] = False
                        #game_state["current_champion_id"] = None
                    
                    game_state["time_left"], game_state["status"] = ROUND_DURATION, "PLAYING"
                    game_state["whistle_event"] = True
                    game_state["ultimo_vencedor_anuncio"] = ""
                    for p in game_state["scores"].values():
                        p["gols_round"] = 0

                p_pos = data["pos"]
                p_center = [p_pos[0] + 17, p_pos[1] + 17]
                dist_bola = math.hypot(p_center[0] - game_state["ball_pos"][0], 
                                       p_center[1] - game_state["ball_pos"][1])

                # --- LÓGICA DE POSSE ---
                if game_state["ball_owner"] == p_id:
                    if data["kick"] is not None:
                        angle = data["kick"]
                        game_state["ball_vel"] = [math.cos(angle)*BALL_SPEED, math.sin(angle)*BALL_SPEED]
                        game_state["ball_owner"], game_state["last_kicker"] = None, p_id
                    else:
                        game_state["ball_pos"] = [p_center[0], p_center[1]]
                        game_state["ball_vel"] = [0, 0]
                else:
                    if game_state["ball_owner"] is None:
                        if dist_bola < 35:
                            game_state["ball_owner"] = p_id
                    else:
                        if dist_bola < 30:
                            angle_espirro = random.uniform(0, 2 * math.pi)
                            forca_espirro = random.uniform(16, 24)
                            game_state["ball_vel"] = [math.cos(angle_espirro) * forca_espirro, 
                                                      math.sin(angle_espirro) * forca_espirro]
                            game_state["ball_owner"] = None
                            game_state["steal_event"] = True
                            game_state["last_kicker"] = p_id 

                game_state["players"][p_id] = {"pos": p_pos, "name": name}

                # --- VERIFICAÇÃO DE INATIVIDADE ---
                if time.time() - game_state["last_seen"].get(p_id, 0) > 10:
                    print(f"Jogador {p_id} kickado por inatividade.")
                    break 

                # Envio de resposta
                reply = {**game_state, 
                         "goalies": [{"pos": g.rect.topleft} for g in game_state["goalies"]],
                         "defenders": [{"pos": d.rect.topleft} for d in game_state["defenders"]]}
                
                conn.sendall(pickle.dumps(reply))
           #     if time.time() > game_state.get("goal_timer", 0):
           #         game_state["goal_event"] = False

            except socket.timeout:
                continue # Apenas tenta o próximo loop se o socket travar
            except (EOFError, pickle.UnpicklingError):
                continue # Ignora pacotes corrompidos

    except Exception as e:
        print(f"Erro na thread do jogador {p_id}: {e}")
    
    finally: 
        # --- LIMPEZA CRÍTICA ---
        print(f"Conexão encerrada para o jogador {p_id}. Liberando slot.")
        if p_id in game_state["players"]: del game_state["players"][p_id]
        if p_id in game_state["last_seen"]: del game_state["last_seen"][p_id]
        if p_id in game_state["scores"]: del game_state["scores"][p_id]
        if game_state["ball_owner"] == p_id: game_state["ball_owner"] = None
        
        update_defender_count()
        conn.close()

if __name__ == "__main__":
    # Removemos o input() e usamos a variável PORT que vem do argparse lá do topo
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", PORT))
        s.listen()
        s.settimeout(1.0)
        print(f"Servidor iniciado na porta {PORT}")
        print(f"Limite de vitórias para o título: {WIN_LIMIT}")
    except Exception as e:
        print(f"Erro ao iniciar servidor: {e}")
        sys.exit()

    threading.Thread(target=physics_loop, daemon=True).start()
    
    # --- NOVO LOOP DE ACEITAÇÃO NO MAIN ---
    try:
        while True:
            try:
                c, a = s.accept()
                
                # Procura o primeiro slot livre entre 0 e 5
                p_id_disponivel = None
                for i in range(6):
                    if i not in game_state["players"]:
                        p_id_disponivel = i
                        break
                
                if p_id_disponivel is not None:
                    print(f"Novo jogador conectado: {a} atribuído ao slot {p_id_disponivel}")
                    threading.Thread(target=handle_client, args=(c, a, p_id_disponivel), daemon=True).start()
                else:
                    print(f"Tentativa de conexão de {a} recusada: Servidor Lotado.")
                    # Opcional: enviar um sinal de erro antes de fechar
                    c.send(str(-1).encode()) 
                    c.close()
                    
            except socket.timeout: 
                continue
    except KeyboardInterrupt: 
        sys.exit()