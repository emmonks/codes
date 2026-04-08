import pygame, socket, json, sys, random, time

WIDTH_ARENA, WIDTH_TOTAL, HEIGHT = 1150, 1350, 720
pygame.init()
screen = pygame.display.set_mode((WIDTH_TOTAL, HEIGHT))
pygame.display.set_caption("Pyserk Client")

# Fontes
FONT_UI = pygame.font.SysFont("monospace", 22, bold=True)
FONT_BIG = pygame.font.SysFont("monospace", 60, bold=True)
FONT_NAME = pygame.font.SysFont("monospace", 14, bold=True) # Fonte reduzida conforme solicitado

def get_spr(path, color):
    try:
        img = pygame.image.load(path)
        return pygame.transform.scale(img, (32, 32))
    except:
        s = pygame.Surface((32, 32))
        s.fill(color)
        pygame.draw.rect(s, (255, 255, 255), (0, 0, 32, 32), 2)
        return s

def load_sound(path):
    try:
        # Tenta carregar o arquivo de som
        s = pygame.mixer.Sound(path)
        return s
    except Exception as e:
        # Se o arquivo não existir, exibe um aviso e retorna None
        # Isso evita que o jogo feche se faltar um arquivo .wav
        print(f" Atenção: Arquivo {path} não encontrado. O jogo seguirá sem este som.")
        return None

def login_screen(p_ip="127.0.0.1", p_port="5000", p_name=""):
    ip, port, name = p_ip, p_port, p_name # Use os parâmetros recebidos
    active = 2
    btn = pygame.Rect(WIDTH_TOTAL//2-100, 480, 200, 60)
    
    while True:
        screen.fill((20, 20, 40))
        title = FONT_BIG.render("PYSERK", True, (255, 255, 0))
        screen.blit(title, (WIDTH_TOTAL//2 - title.get_width()//2, 80))
        
        fields = [f"IP: {ip}", f"PORTA: {port}", f"NOME: {name}"]
        for i, f in enumerate(fields):
            color = (0, 255, 255) if i == active else (200, 200, 200)
            screen.blit(FONT_UI.render(f, True, color), (WIDTH_TOTAL//2-150, 250 + i*60))
        
        pygame.draw.rect(screen, (0, 200, 0), btn)
        screen.blit(FONT_UI.render("INICIAR", True, (255, 255, 255)), (btn.x + 50, btn.y + 15))
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN:
                if btn.collidepoint(e.pos) and len(name) == 3: return ip, int(port), name.upper()
                for i in range(3):
                    if pygame.Rect(WIDTH_TOTAL//2-150, 250+i*60, 300, 40).collidepoint(e.pos): active = i
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN and len(name) == 3: return ip, int(port), name.upper()
                if e.key == pygame.K_TAB: active = (active + 1) % 3
                if e.key == pygame.K_BACKSPACE:
                    if active == 0: ip = ip[:-1]
                    elif active == 1: port = port[:-1]
                    else: name = name[:-1]
                elif len(e.unicode) > 0:
                    if active == 0: ip += e.unicode
                    elif active == 1 and e.unicode.isdigit(): port += e.unicode
                    elif active == 2 and len(name) < 3: name += e.unicode.upper()

def play_match(ip, port, name):
   # ip, port, name = login_screen()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((ip, port))
        sock.sendall(f"HELLO|{name}".encode('utf-8'))
        sock.setblocking(False)
        # --- NOVO: Limpar lixo de conexão anterior ---
        time.sleep(0.2) # Pequena pausa para estabilizar
        try:
            # Descarta pacotes antigos que possam conter o "Game Over" da partida passada
            while True:
                lixo = sock.recv(40960)
                if not lixo: break
        except: pass
    except Exception as e:
        print(f"Erro: {e}"); return

    spr_players = [get_spr(f"player_{i}.png", (random.randint(50, 200), 100, 250)) for i in range(8)]
    spr_robots = {"red": get_spr("enemy_red.png", (255, 0, 0)), "yellow": get_spr("enemy_yellow.png", (255, 255, 0))}
    spr_item = get_spr("powerup_cross.png", (0, 255, 0))
    
    # --- NOVO: Inicialização e Carregamento de Áudio ---
    pygame.mixer.init()
    # Certifique-se de que os arquivos existam na mesma pasta do script
    snd_shoot = load_sound("shoot.wav")
    snd_round_over = load_sound("round_end.wav")
    snd_game_over = load_sound("game_over.wav")
    snd_move = load_sound("move2.wav") # Som de engrenagem para os robôs
    snd_explosion = load_sound("explosion.wav")
    snd_robot_shoot =  load_sound("shoot.wav")
    
    if snd_move:
        # O volume vai de 0.0 (mudo) até 1.0 (máximo)
        # 0.1 ou 0.2 costuma ser o ideal para sons de fundo/ambientes
        snd_move.set_volume(0.2)
    
    # Variáveis de controle de estado (Edge Detection)
    last_round_over = False
    last_game_over = False
    # Variável para rastrear quantas explosões já processamos
    last_explosion_count = 0
    last_robot_bullet_count = 0
    
    clock = pygame.time.Clock()
    buffer = ""
    
    last_round_over = False
    last_game_over = False
    last_explosion_count = 0
    last_robot_bullet_count = 0

    while True:
        try:
            data = sock.recv(40960).decode('utf-8')
            if data: buffer += data
        except BlockingIOError: pass
        except Exception: break # Conexão perdida

        if "###" in buffer:
            parts = buffer.split("###")
            buffer = parts.pop()
            for raw in parts:
                if not raw.strip(): continue
                st = json.loads(raw)
                # --- Lógica de Gatilho de Áudio (Detecção de Borda) ---
                curr_round_over = st.get("round_over", False)
                curr_game_over = st.get("game_over", False)
                
                current_explosions = st.get("explosions", [])
                # Se o número de explosões aumentou, disparar o som
                if len(current_explosions) > last_explosion_count:
                    if snd_explosion:
                        snd_explosion.play()
                # Atualiza o contador para o próximo frame
                last_explosion_count = len(current_explosions)

                # Toca se mudou de False para True (Início do evento)
                if curr_round_over and not last_round_over:
                    if snd_round_over: snd_round_over.play()
                
                if curr_game_over and not last_game_over:
                    if snd_game_over: snd_game_over.play()

                # Atualiza estados anteriores
                last_round_over = curr_round_over
                last_game_over = curr_game_over
                
                # --- Dentro do loop de processamento do JSON (st) ---

                # Filtra se existe pelo menos um robô VERMELHO (não sniper) vivo na arena
                robots_perseguidores = [r for r in st.get("robots", []) if r["alive"] and not r["sniper"]]

                # Só toca o som de movimento se houver robôs vermelhos ativos
                if robots_perseguidores and not curr_round_over and not curr_game_over:
                    if snd_move and not pygame.mixer.Channel(1).get_busy():
                        # Toca o som no canal 1 (com o volume baixo que definimos)
                        pygame.mixer.Channel(1).play(snd_move)
                else:
                    # Se todos os vermelhos morreram ou o round acabou, para o som de engrenagens imediatamente
                    pygame.mixer.Channel(1).stop()
                
                robot_bullets = [b for b in st.get("bullets", []) if b["owner"] == "ROBOT"]

                if len(robot_bullets) > last_robot_bullet_count:
                    if snd_robot_shoot:
                        snd_robot_shoot.play()

                last_robot_bullet_count = len(robot_bullets)

                if curr_game_over:
                    screen.fill((10, 10, 30))
                    msg = FONT_BIG.render(f"VENCEDOR: {st['winner_name']}", True, (255, 215, 0))
                    screen.blit(msg, (WIDTH_TOTAL//2 - msg.get_width()//2, 100))
                    
                    for i, p in enumerate(sorted(st["players"], key=lambda x: x["score"], reverse=True)):
                        txt = f"{i+1}. {p['name']} - {p['score']} PTS"
                        screen.blit(FONT_UI.render(txt, True, (255, 255, 255)), (WIDTH_TOTAL//2-120, 220 + i*40))
                    
                    screen.blit(FONT_UI.render("Pressione 'N' para NOVO JOGO", True, (0, 255, 0)), (WIDTH_TOTAL//2-180, 580))
                    pygame.display.flip()
                    pygame.event.clear()
                    
                    waiting = True
                    while waiting:
                        for e in pygame.event.get():
                            if e.type == pygame.QUIT: 
                                pygame.quit(); sys.exit()
                            
                            if e.type == pygame.KEYDOWN and e.key == pygame.K_n:
                                try:
                                    # 1. Notifica o servidor (opcional, já que o fechamento do socket também avisa)
                                    sock.sendall(b"RESTART_GAME;") 
                                    # 2. Fecha a conexão atual para garantir limpeza total
                                    sock.close() 
                                    # 3. Retorna para o loop externo (que abrirá o login_screen novamente)
                                    return 
                                except: 
                                    return 
                        
                        clock.tick(30)

                # Desenho do Jogo
                screen.fill((15, 15, 25))
                for w in st["walls"]: pygame.draw.rect(screen, (50, 50, 70), (w["x"], w["y"], 40, 40))
                for it in st["items"]: screen.blit(spr_item, (it["x"], it["y"]))
                
                # Explosões
                for ex in st.get("explosions", []):
                    pygame.draw.circle(screen, (255, 100, 0), (int(ex["x"])+16, int(ex["y"])+16), 25)
                    pygame.draw.circle(screen, (255, 255, 255), (int(ex["x"])+16, int(ex["y"])+16), 12)
                
                for r in st["robots"]:
                    if r["alive"]: screen.blit(spr_robots["yellow" if r["sniper"] else "red"], (r["x"], r["y"]))
                
                for b in st["bullets"]:
                    pygame.draw.circle(screen, tuple(b["color"]), (int(b["x"]), int(b["y"])), 5)
                
                for p in st["players"]:
                    if p["alive"]:
                        screen.blit(spr_players[p["sprite_id"]], (p["x"], p["y"]))
                        label = f"{p['name']} ({p['shots_left']})" if p.get("p_cross_active") else p["name"]
                        screen.blit(FONT_NAME.render(label, True, (255, 255, 255)), (p["x"], p["y"]-20))

                # UI Lateral
                pygame.draw.rect(screen, (30, 30, 50), (WIDTH_ARENA, 0, 200, HEIGHT))
                screen.blit(FONT_UI.render("RANKING", True, (255, 255, 0)), (WIDTH_ARENA + 45, 20))
                for i, p in enumerate(sorted(st["players"], key=lambda x: x["score"], reverse=True)):
                    screen.blit(FONT_UI.render(f"{p['name']}:{p['score']}", True, (255,255,255)), (WIDTH_ARENA+20, 70+i*30))
                # --- Dentro do loop principal do cliente, após desenhar jogadores/robôs ---

                if curr_round_over:
                    # Cria uma sobreposição semi-transparente ou apenas o texto centralizado
                    txt_surf = FONT_BIG.render("ROUND OVER", True, (255, 0, 0))
                    # Centraliza na Arena
                    x_pos = (WIDTH_ARENA // 2) - (txt_surf.get_width() // 2)
                    y_pos = (HEIGHT // 2) - (txt_surf.get_height() // 2)
                    
                    # Desenha um retângulo de fundo para dar destaque
                    pygame.draw.rect(screen, (0,0,0), (x_pos - 10, y_pos - 10, txt_surf.get_width() + 20, txt_surf.get_height() + 20))
                    screen.blit(txt_surf, (x_pos, y_pos))


                
                pygame.display.flip()

        # Comandos
        keys = pygame.key.get_pressed()
        cmd = f"IN|{int(keys[pygame.K_LEFT])}|{int(keys[pygame.K_RIGHT])}|{int(keys[pygame.K_UP])}|{int(keys[pygame.K_DOWN])};"
        try: sock.sendall(cmd.encode('utf-8'))
        except: break
            
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                try: 
                    sock.sendall(b"SHOOT;")
                    if snd_shoot: snd_shoot.play()
                except: break
        
        clock.tick(60)

if __name__ == "__main__":
    meu_ip, minha_porta, meu_nome = "127.0.0.1", 5000, ""
    
    # 1. Abre a tela de login APENAS na primeira vez
    meu_ip, minha_porta, meu_nome = login_screen(meu_ip, str(minha_porta), meu_nome)
    
    while True:
        # 2. Inicia a partida direto
        resultado = play_match(meu_ip, minha_porta, meu_nome)
        
        # Se por acaso a função play_match retornar algo que indique erro de conexão,
        # você poderia reabrir o login aqui, mas por enquanto vamos manter o loop direto.
        # O 'return' dentro do play_match (ao apertar 'N') fará o loop reiniciar aqui.
        print("Reiniciando partida direta...")