import pygame, socket, pickle, math, sys, time, os

pygame.mixer.pre_init(44100, -16, 2, 512) # Menos buffer = som mais rápido
pygame.init(); pygame.mixer.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
font = pygame.font.SysFont("Consolas", 18, bold=True)
fontp = pygame.font.SysFont("Consolas", 14, bold=True)
font_lg = pygame.font.SysFont("Impact", 70)


def resource_path(relative_path):
    """ Retorna o caminho absoluto para o recurso, compatível com PyInstaller """
    try:
        # PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
    
#snd_gol = pygame.mixer.Sound("gol.wav") if os.path.exists("gol.wav") else None
#snd_kick = pygame.mixer.Sound("chute.wav") if os.path.exists("chute.wav") else None
# Carregamento com ajuste de volume
if os.path.exists(resource_path("gol.wav")):
    snd_gol = pygame.mixer.Sound(resource_path("gol.wav"))
    snd_gol.set_volume(0.8)
else:
    snd_gol = None

if os.path.exists(resource_path("chute.wav")):
    snd_kick = pygame.mixer.Sound(resource_path("chute.wav"))
    snd_kick.set_volume(0.5) # Chute um pouco mais baixo que o gol
else:
    snd_kick = None
if os.path.exists(resource_path("defesa.wav")):
    snd_defesa = pygame.mixer.Sound(resource_path("defesa.wav"))
    snd_defesa.set_volume(0.5) # Chute um pouco mais baixo que o gol
else:
    snd_defesa = None
# --- Na seção de sons do Cliente ---
snd_roubo = pygame.mixer.Sound(resource_path("roubo.wav")) if os.path.exists(resource_path("roubo.wav")) else None
# --- Sons no Cliente ---
snd_apito = pygame.mixer.Sound(resource_path("apito.wav")) if os.path.exists(resource_path("apito.wav")) else None

ultimo_gol_visto = False


def load_img(p, s):
    try: return pygame.transform.scale(pygame.image.load(resource_path(p)).convert_alpha(), s)
    except: surf = pygame.Surface(s); surf.fill((150,0,0)); return surf

spr_p = load_img("jogador1.png", (35, 35)); spr_b = load_img("bola.png", (15, 15))
spr_goalies = [load_img("goalkeeper_1a.png", (50, 25)), load_img("goalkeeper_2a.png", (50, 25)), 
               load_img("goalkeeper_3a.png", (25, 50)), load_img("goalkeeper_4a.png", (25, 50))]
               

# --- NO CLIENTE ---

def draw_net(rect, side_name, impact_timer, horizontal=True):
    # Cores e Offset de Impacto
    color_net = (255, 255, 255) if impact_timer > 0 else (200, 200, 200)
    color_trave = (255, 255, 255) # Trave sempre branca
    offset = min(impact_timer // 2, 8) 
    
    # Prepara o retângulo da rede com o efeito de offset
    net_rect = rect.copy()
    if impact_timer > 0:
        if side_name == "NORTE": net_rect.y -= offset
        elif side_name == "SUL":   net_rect.y += offset
        elif side_name == "OESTE": net_rect.x -= offset
        elif side_name == "LESTE":  net_rect.x += offset

    # --- 1. DESENHA A ESTRUTURA DAS TRAVES (LINHAS BRANCAS ESPESSAS) ---
    trave_width = 4 # Espessura da trave branca
    
    if side_name == "NORTE":
        # Trave Norte: Rede e trave ficam 'para cima' do campo (y<20)
        # Linha do fundo (horizontal)
        pygame.draw.line(screen, color_trave, (net_rect.x, net_rect.y), (net_rect.x + net_rect.w, net_rect.y), trave_width)
        # Laterais (verticais) - vão da linha do fundo até a linha do campo (y=20)
        pygame.draw.line(screen, color_trave, (net_rect.x, net_rect.y), (net_rect.x, rect.y + rect.h), trave_width)
        pygame.draw.line(screen, color_trave, (net_rect.x + net_rect.w, net_rect.y), (net_rect.x + net_rect.w, rect.y + rect.h), trave_width)
        
    elif side_name == "SUL":
        # Trave Sul: Rede fica 'para baixo' do campo (y>580)
        # Linha do fundo (horizontal)
        pygame.draw.line(screen, color_trave, (net_rect.x, net_rect.y + net_rect.h), (net_rect.x + net_rect.w, net_rect.y + net_rect.h), trave_width)
        # Laterais (verticais) - vão da linha do campo (y=580) até a linha do fundo
        pygame.draw.line(screen, color_trave, (net_rect.x, rect.y), (net_rect.x, net_rect.y + net_rect.h), trave_width)
        pygame.draw.line(screen, color_trave, (net_rect.x + net_rect.w, rect.y), (net_rect.x + net_rect.w, net_rect.y + net_rect.h), trave_width)

    elif side_name == "OESTE":
        # Trave Oeste: Rede fica 'para esquerda' do campo (x<20)
        # Linha do fundo (vertical)
        pygame.draw.line(screen, color_trave, (net_rect.x, net_rect.y), (net_rect.x, net_rect.y + net_rect.h), trave_width)
        # Laterais (horizontais) - vão da linha do fundo até a linha do campo (x=20)
        pygame.draw.line(screen, color_trave, (net_rect.x, net_rect.y), (rect.x + rect.w, net_rect.y), trave_width)
        pygame.draw.line(screen, color_trave, (net_rect.x, net_rect.y + net_rect.h), (rect.x + rect.w, net_rect.y + net_rect.h), trave_width)

    elif side_name == "LESTE":
        # Trave Leste: Rede fica 'para direita' do campo (x>780)
        # Linha do fundo (vertical)
        pygame.draw.line(screen, color_trave, (net_rect.x + net_rect.w, net_rect.y), (net_rect.x + net_rect.w, net_rect.y + net_rect.h), trave_width)
        # Laterais (horizontais) - vão da linha do campo (x=780) até a linha do fundo
        pygame.draw.line(screen, color_trave, (rect.x, net_rect.y), (net_rect.x + net_rect.w, net_rect.y), trave_width)
        pygame.draw.line(screen, color_trave, (rect.x, net_rect.y + net_rect.h), (net_rect.x + net_rect.w, net_rect.y + net_rect.h), trave_width)


    # --- 2. DESENHA A REDE (LINHAS FINAS) SOBRE A ESTRUTURA ---
    step = 5 # Espaçamento da rede
    
    # Desenha o fundo da rede (preenchimento leve para contraste)
    pygame.draw.rect(screen, (0, 0, 0, 50), net_rect) 

    if horizontal: # Norte e Sul
        # Linhas Verticais da rede
        for x in range(net_rect.x, net_rect.x + net_rect.w, step):
            pygame.draw.line(screen, color_net, (x, net_rect.y), (x, net_rect.y + net_rect.h), 1)
        # Linhas Horizontais da rede
        for y in range(net_rect.y, net_rect.y + net_rect.h, step):
            pygame.draw.line(screen, color_net, (net_rect.x, y), (net_rect.x + net_rect.w, y), 1)
    else: # Oeste e Leste
        # Linhas Horizontais da rede
        for y in range(net_rect.y, net_rect.y + net_rect.h, step):
            pygame.draw.line(screen, color_net, (net_rect.x, y), (net_rect.x + net_rect.w, y), 1)
        # Linhas Verticais da rede
        for x in range(net_rect.x, net_rect.x + net_rect.w, step):
            pygame.draw.line(screen, color_net, (x, net_rect.y), (x, net_rect.y + net_rect.h), 1)

def draw_field(net_timers, map_type="SOLID"):
    # Cores de base
    green_dark = (34, 139, 34)
    green_light = (50, 160, 50)
    
    # Preenche o fundo com a cor escura primeiro
    screen.fill(green_dark)
    
    # --- DESENHO DOS PADRÕES ---
    if map_type == "STRIPES":
        # Desenha listras verticais
        stripe_width = 80 # Largura de cada faixa
        for x in range(20, 780, stripe_width * 2):
            pygame.draw.rect(screen, green_light, (x, 20, stripe_width, 560))
            
    elif map_type == "CHECKERBOARD":
        # Desenha quadrantes (tabuleiro)
        tile_size = 100 # Tamanho do quadrado
        for row in range(0, 6): # 6 linhas
            for col in range(0, 8): # 8 colunas
                if (row + col) % 2 == 0:
                    # Ajusta as coordenadas para dentro da linha branca (20, 20)
                    rect = (20 + col*95, 20 + row*93, 95, 93)
                    pygame.draw.rect(screen, green_light, rect)

    # --- LINHAS DO CAMPO (Desenha por cima do padrão) ---
    pygame.draw.rect(screen, (255, 255, 255), (20, 20, 760, 560), 3) # Bordas
    pygame.draw.circle(screen, (255, 255, 255), (400, 300), 80, 3) # Círculo Central
    pygame.draw.circle(screen, (255, 255, 255), (400, 300), 5)    # Ponto Central
    pygame.draw.line(screen, (255, 255, 255), (400, 20), (400, 580), 3) # Linha de Meio

    # Áreas (Usando as medidas de 10px de folga que definimos antes)
    areas = [
        pygame.Rect(290, 20, 220, 60),   # Norte
        pygame.Rect(290, 520, 220, 60),  # Sul
        pygame.Rect(20, 190, 60, 220),   # Oeste
        pygame.Rect(720, 190, 60, 220)   # Leste
    ]
    for r in areas: 
        pygame.draw.rect(screen, (255, 255, 255), r, 2)
    
    # Desenha Redes
    draw_net(pygame.Rect(300, 5, 200, 15), "NORTE", net_timers["NORTE"])
    draw_net(pygame.Rect(300, 580, 200, 15), "SUL", net_timers["SUL"])
    draw_net(pygame.Rect(5, 200, 15, 200), "OESTE", net_timers["OESTE"], False)
    draw_net(pygame.Rect(780, 200, 15, 200), "LESTE", net_timers["LESTE"], False)
    
net = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
net.settimeout(10) # Timeout inicial para conexão    

def login_screen():
    # --- PARTE 1: CARREGAMENTO (Fora do loop) ---
    spr_logo = load_img("logo_4goal.png", (300, 150)) if os.path.exists(resource_path("logo_4goal.png")) else None
    
    # Inicia a música da tela inicial
    if os.path.exists(resource_path("fundo_musical.ogg")): # Verifique o nome do seu arquivo
        pygame.mixer.music.load(resource_path("fundo_musical.ogg"))
        pygame.mixer.music.set_volume(0.4) # Volume mais baixo para não atrapalhar
        pygame.mixer.music.play(-1) # -1 faz a música tocar em loop
    
    inputs = {"Nome": "ABC", "IP": "127.0.0.1", "Porta": "5555"}
    keys_list = list(inputs.keys())
    active_idx = 0
    btn = pygame.Rect(300, 450, 200, 60)
    input_rects = {}
    
    while True:
        screen.fill((20, 30, 20))
        
        # --- PARTE 2: EXIBIÇÃO (Dentro do loop) ---
        if spr_logo:
            # Centraliza a logo no topo
            screen.blit(spr_logo, (WIDTH//2 - 150, 20))
            
        y = 180
    #    title = font_lg.render("4GOAL", True, (255, 255, 255))
    #    screen.blit(title, (WIDTH//2 - title.get_width()//2, 40))
        
        for i, (k, v) in enumerate(inputs.items()):
            color = (0, 255, 0) if i == active_idx else (200, 200, 200)
            lbl = font.render(f"{k}:", True, (150, 150, 150)); txt = font.render(v, True, color)
            field_rect = pygame.Rect(300, y, 220, 35); input_rects[k] = field_rect
            if i == active_idx: pygame.draw.rect(screen, color, field_rect, 1)
            screen.blit(lbl, (230, y + 8)); screen.blit(txt, (310, y + 8)); y += 70
        pygame.draw.rect(screen, (0, 150, 0), btn, border_radius=12)
        btn_txt = font.render("CONECTAR", True, (255, 255, 255))
        screen.blit(btn_txt, (btn.centerx - btn_txt.get_width()//2, btn.centery - 10))
        # --- CRÉDITOS ---
        # Renderiza o seu nome no rodapé da tela
        creditos_txt = font.render("Desenvolvido por: emmonks - 2026", True, (100, 100, 100))
        screen.blit(creditos_txt, (WIDTH//2 - creditos_txt.get_width()//2, HEIGHT - 30))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN:
                for k, rect in input_rects.items():
                    if rect.collidepoint(e.pos): active_idx = keys_list.index(k)
                if btn.collidepoint(e.pos):
                    pygame.mixer.music.stop() # PARA A MÚSICA IMEDIATAMENTE
                    return inputs
            if e.type == pygame.KEYDOWN:
                active_key = keys_list[active_idx]
                if e.key == pygame.K_RETURN:
                    pygame.mixer.music.stop() # PARA A MÚSICA IMEDIATAMENTE
                    
                    return inputs
                if e.key == pygame.K_TAB: active_idx = (active_idx + 1) % len(keys_list)
                elif e.key == pygame.K_BACKSPACE: inputs[active_key] = inputs[active_key][:-1]
                else:
                    char = e.unicode.upper()
                    if active_key == "Nome" and len(inputs[active_key]) < 3: inputs[active_key] += char
                    elif active_key in ["IP", "Porta"] and len(inputs[active_key]) < 15:
                        if char in "0123456789.:": inputs[active_key] += char

def main():
    cfg = login_screen()
    
    # 1. TENTATIVA DE CONEXÃO INICIAL
    try: 
        print(f"Tentando conectar em {cfg['IP']}:{cfg['Porta']}...")
        net.connect((cfg["IP"], int(cfg["Porta"])))
        
        # Recebe ID ou -1 (Campo Cheio)
        response = net.recv(1024).decode()
        p_id = int(response)
        
        if p_id == -1:
            screen.fill((50, 0, 0))
            msg = font_lg.render("CAMPO CHEIO!", True, (255, 255, 255))
            screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 30))
            msg = font.render("Por favor, tente novamente mais tarde", True, (255, 255, 255))
            screen.blit(msg, (WIDTH//2 - msg.get_width()//2, 350))
            pygame.display.flip()
            time.sleep(3)
            return
            
        # Remove o timeout para não cair durante o jogo
        net.settimeout(None) 
            
    except Exception as e:
        print(f"Erro fatal de conexão: {e}")
        return

    # 2. CONFIGURAÇÕES E CACHE
    player_cache = {}

    ultimo_apito_visto = False
    ultimo_roubo_visto = False
    ultima_defesa_vista = False
    ultimo_gol_visto = False # Caso ainda não tenha essa
    ultimo_kick_visto = False

    spr_zagueiros = [
        load_img("zagueiro_bigode.png", (35, 35)),
        load_img("zagueiro_barba.png", (35, 35))
    ]
    
    my_pos = [400, 300]
    in_posse = False
    aim_angle = 0
    goal_timer = 0
    goal_name = ""
    net_timers = {"NORTE": 0, "SUL": 0, "OESTE": 0, "LESTE": 0}
    gs = None # Estado do jogo inicial

    # 3. LOOP PRINCIPAL
    while True:
        #draw_field(net_timers)
        if gs:
            draw_field(net_timers, gs.get("map_type", "SOLID"))
        else:
            # Se ainda não recebeu dados, desenha o básico
            draw_field(net_timers)
        keys = pygame.key.get_pressed()
        
        

        # Movimentação local
        if not in_posse:
            if keys[pygame.K_LEFT]:  my_pos[0] -= 7
            if keys[pygame.K_RIGHT]: my_pos[0] += 7
            if keys[pygame.K_UP]:    my_pos[1] -= 7
            if keys[pygame.K_DOWN]:  my_pos[1] += 7
            my_pos[0] = max(20, min(my_pos[0], 745))
            my_pos[1] = max(20, min(my_pos[1], 545))
        else:
            if keys[pygame.K_LEFT]:  aim_angle -= 0.1
            if keys[pygame.K_RIGHT]: aim_angle += 0.1

        # Lógica de Chute (Prepara o dado para enviar uma única vez)
        kick_to_send = None
        if gs and gs.get("ball_owner") == p_id:
            if not in_posse: 
                in_posse, p_start = True, time.time()
            
            t_kick = max(0, 2.0 - (time.time() - p_start))
            
            # Desenha a mira na tela
            pygame.draw.line(screen, (255, 255, 0), gs["ball_pos"], 
                             (gs["ball_pos"][0] + math.cos(aim_angle)*60, 
                              gs["ball_pos"][1] + math.sin(aim_angle)*60), 4)
            
            if keys[pygame.K_LCTRL] or t_kick <= 0:
                in_posse = False
                kick_to_send = aim_angle
                if snd_kick:
                    # play(0) garante que ele toque apenas uma vez por ativação
                    # Se quiser evitar que o som se repita rápido demais:
                    if not pygame.mixer.Channel(1).get_busy():
                        pygame.mixer.Channel(1).play(snd_kick)
        else:
            in_posse = False

        # 4. COMUNICAÇÃO (ENVIAR E RECEBER)
        try:
            # Envia posição, nome, chute (se houver) e pedido de restart
            data_out = {
                "pos": my_pos, 
                "name": cfg["Nome"], 
                "kick": kick_to_send, 
                "restart": keys[pygame.K_r]
            }
            net.send(pickle.dumps(data_out))
            
            # Recebe o novo estado do jogo (Buffer aumentado para 16kb)
            raw = net.recv(16384)
            if not raw: 
                print("Conexão perdida com o servidor.")
                break
            gs = pickle.loads(raw)
            
            # --- Lógica de Sons com Detecção de Mudança de Estado ---
            #print(gs.keys())
            if gs:
                # APITO
                if gs.get("whistle_event"):
                    if not ultimo_apito_visto:
                        if snd_apito: snd_apito.play()
                        ultimo_apito_visto = True
                else:
                    ultimo_apito_visto = False

                # ROUBO DE BOLA
                if gs.get("steal_event"):
                    if not ultimo_roubo_visto:
                        if snd_roubo: snd_roubo.play()
                        ultimo_roubo_visto = True
                else:
                    ultimo_roubo_visto = False

                # DEFESA DO GOLEIRO
                if gs.get("save_event"):
                    if not ultima_defesa_vista:
                        if snd_defesa: snd_defesa.play()
                        ultima_defesa_vista = True
                else:
                    ultima_defesa_vista = False

                if gs.get("kick_event"):
                    if not ultimo_kick_visto:
                        if snd_kick: snd_kick.play()
                        ultimo_kick_visto = True
                else:
                    ultimo_kick_visto = False        
            
            # Processar Eventos do Servidor (Gols e Efeitos)
                if gs.get("goal_event"):
                    if not ultimo_gol_visto:
                        goal_name = gs.get("last_goal_name", "ALGUÉM")
                        goal_timer = 120
                        if snd_gol:
                            # Canal 0 reservado para o Gol (prioridade)
                            pygame.mixer.Channel(0).play(snd_gol)
                            #goal_timer, goal_name = 100, gs["last_goal_name"]
                            side = gs.get("last_goal_side")
                        if side in net_timers: 
                            net_timers[side] = 30
                        ultimo_gol_visto = True
                else:
                    ultimo_gol_visto = False

            if goal_timer > 0:
                goal_timer -= 1
            
            for k in net_timers:
                if net_timers[k] > 0: net_timers[k] -= 1

        except Exception as e:
            print(f"Erro de comunicação: {e}")
            break

        # 5. RENDERIZAÇÃO DOS ELEMENTOS DO SERVIDOR
        if gs:
            # Zagueiros
            for i, d in enumerate(gs.get("defenders", [])):
                sprite_z = spr_zagueiros[i % len(spr_zagueiros)]
                screen.blit(sprite_z, d["pos"])

            # Goleiros
            for i, g in enumerate(gs["goalies"]): 
                if i < len(spr_goalies):
                    screen.blit(spr_goalies[i], g["pos"])

            # Jogadores (com Cache de Sprites)
            for pid, p in gs["players"].items():
                if pid not in gs["scores"]: 
                    continue
                name_to_draw = p["name"]
                color_to_draw = (255, 255, 255) # Branco

                champ_id = gs.get("current_champion_id")
                # DESTAQUE PARA O CAMPEÃO ATUAL
                if champ_id is not None and str(pid) == str(champ_id):
                    name_to_draw = f"*{name_to_draw}"
                    color_to_draw = (255, 215, 0) # Dourado

                # Busca o sprite correto definido pelo servidor no dicionário 'scores'
                sprite_name = gs["scores"].get(pid, {}).get("sprite", "jogador1.png")
                
                if sprite_name not in player_cache:
                    player_cache[sprite_name] = load_img(sprite_name, (35, 35))
                
                screen.blit(player_cache[sprite_name], p["pos"])

                # 5. DESENHA O TEXTO (Usando as variáveis agora garantidas)
                name_surf = font.render(name_to_draw, True, color_to_draw)
                screen.blit(name_surf, (p["pos"][0], p["pos"][1]-22))
            
            # Bola
            if gs["ball_owner"] is not None:
                pygame.draw.circle(screen, (255, 255, 0), gs["ball_pos"], 12, 2)
            screen.blit(spr_b, (gs["ball_pos"][0]-7, gs["ball_pos"][1]-7))
            
            # UI (Placar e Tempo)
            # --- UI: TABELA DE PERFORMANCE (TOP RIGHT) ---
            # --- UI: TABELA DE PERFORMANCE (TOP RIGHT) ---
            # Configurações de Posição
            start_x = WIDTH - 220  # Ajustado para não ficar colado na borda
            y = 5
            
            # Largura das colunas: Nome é maior, números são estreitos
            col_name_w = 60
            col_data_w = 40
            
            # Cabeçalhos
            headers = ["PID", "R", "T", "V"]
            colors = [(200,200,200), (255,255,255), (255,255,0), (0,255,255)]
            
            # 1. Renderiza Cabeçalho com alinhamento fixo
            for i, h in enumerate(headers):
                h_surf = fontp.render(h, True, colors[i])
                # A primeira coluna usa start_x, as próximas usam o espaçamento acumulado
                pos_x = start_x if i == 0 else start_x + col_name_w + (i-1) * col_data_w
                screen.blit(h_surf, (pos_x, y))
            
            y += 20
            # Linha separadora discreta
      #      pygame.draw.line(screen, (255, 255, 255), (start_x, y), (WIDTH - 20, y), 1)
            y += 7

            # Ranking por Vitórias
            ranking = sorted(gs["scores"].values(), key=lambda x: x.get('vitorias', 0), reverse=True)

            for s in ranking[:6]:
                is_champ = False
                for pid, score_data in gs["scores"].items():
                    if score_data == s and pid == gs.get("current_champion_id"):
                        is_champ = True
                        break
                # Coluna 1: Nome (Trancado em 3 letras)
                # Coluna 1: Nome
                name_val = s['name'].upper()
                if is_champ:
                    name_val = f"* {name_val}"
                # Se for campeão, desenha o nome em dourado no placar também
                color_row = (255, 215, 0) if is_champ else (255, 255, 255)
                
                name_txt = fontp.render(name_val, True, color_row)
                screen.blit(name_txt, (start_x, y))
                
                # Colunas de Dados (R, T, V)
                # Usamos a mesma lógica de pos_x do cabeçalho para alinhar
                
                # R - Round
                r_val = str(s.get('gols_round', 0))
                r_txt = fontp.render(r_val, True, (255, 255, 255))
                screen.blit(r_txt, (start_x + col_name_w, y))
                
                # T - Total
                t_val = str(s.get('gols', 0))
                t_txt = fontp.render(t_val, True, (255, 255, 0))
                screen.blit(t_txt, (start_x + col_name_w + col_data_w, y))
                
                # V - Vitórias
                v_val = str(s.get('vitorias', 0))
                v_txt = fontp.render(v_val, True, (0, 255, 255))
                screen.blit(v_txt, (start_x + col_name_w + 2 * col_data_w, y))
                
                y += 22

            # Tempo de Jogo (Canto superior esquerdo, sem fundo)
            timer_txt = fontp.render(f"TEMPO: {int(gs['time_left'])}s", True, (255, 255, 255))
            screen.blit(timer_txt, (20, 5))

            # Mensagens de Fim de Jogo ou Gol
            if goal_timer > 0:
                # Sombra do texto para legibilidade
                shadow = font_lg.render(f"GOL DE {goal_name}!", True, (0, 0, 0))
                msg = font_lg.render(f"GOL DE {goal_name}!", True, (255, 255, 0))
    
                pos_x = WIDTH // 2 - msg.get_width() // 2
                pos_y = HEIGHT // 2 - 50
    
                screen.blit(shadow, (pos_x + 4, pos_y + 4)) # Sombra
                screen.blit(msg, (pos_x, pos_y))
            
            if gs["status"] == "ENDED":
                msg_fim = font_lg.render("FIM DE JOGO!", True, (255,0,0))
                screen.blit(msg_fim, (WIDTH//2 - msg_fim.get_width()//2, 200))
                msg_r = font.render("Pressione 'R' para reiniciar", True, (255,255,255))
                screen.blit(msg_r, (WIDTH//2 - msg_r.get_width()//2, 300))
            # --- NO CLIENTE (Tela de Fim de Torneio) ---
            if gs.get("tournament_ended"):
                # Escurece o fundo
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 200))
                screen.blit(overlay, (0,0))
                
                campeao_nome = gs["scores"][gs["current_champion_id"]]["name"]
                txt_campeao = font_lg.render(f"CAMPEÃO: {campeao_nome}", True, (255, 215, 0))
                screen.blit(txt_campeao, (WIDTH//2 - txt_campeao.get_width()//2, HEIGHT//2 - 100))
                
                msg_r = font.render("Pressione 'R' para INICIAR NOVO CAMPEONATO", True, (255,255,255))
                screen.blit(msg_r, (WIDTH//2 - msg_r.get_width()//2, HEIGHT//2 + 50))

        # 6. FINALIZAÇÃO DO FRAME
        pygame.display.flip()
        pygame.time.Clock().tick(60)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                try:
                    # Avisa o servidor que estamos saindo (ajuda a limpar o slot na hora)
                    net.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                net.close()
                pygame.quit()
                sys.exit()





if __name__ == "__main__": main()