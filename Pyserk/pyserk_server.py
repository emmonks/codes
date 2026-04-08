import socket, select, json, time, random, math, threading, sys

WIDTH_ARENA, HEIGHT = 1150, 720
PLAYER_COLORS = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (255,0,255), (0,255,255), (255,255,255), (150,150,150)]

class Server:
    def __init__(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", port))
        self.sock.listen(10)
        self.sock.setblocking(False)
        self.inputs = [self.sock]
        self.clients = {} 
        self.running = True
        self.state = {
            "players": [], "walls": [], "robots": [], 
            "bullets": [], "items": [], "winner_name": None, 
            "explosions": [], "game_over": False
        }
        self.generate_map()
        self.spawn_horde()
        self.spawn_powerup()
        print(f"[*] SERVIDOR ON - PORTA {port} | Aguardando conexões...")
        threading.Thread(target=self.console_commands, daemon=True).start()

    def console_commands(self):
        while self.running:
            line = sys.stdin.readline().strip().lower()
            if line == "remap": self.reset_round()
            elif line == "shutdown": self.running = False; sys.exit()

    def generate_map(self):
        self.state["walls"] = [{"x": x, "y": 0} for x in range(0, WIDTH_ARENA, 40)] + \
                              [{"x": x, "y": HEIGHT-40} for x in range(0, WIDTH_ARENA, 40)] + \
                              [{"x": 0, "y": y} for y in range(40, HEIGHT-40, 40)] + \
                              [{"x": WIDTH_ARENA-40, "y": y} for y in range(40, HEIGHT-40, 40)]
        for _ in range(18):
            self.state["walls"].append({"x": random.randrange(80, WIDTH_ARENA-80, 40), 
                                        "y": random.randrange(80, HEIGHT-80, 40)})

    def spawn_horde(self):
        num = max(4, len(self.clients) * 3)
        self.state["robots"] = []
        for i in range(num):
            rx, ry = self.get_safe_spawn()
            self.state["robots"].append({
             "x": rx, "y": ry, 
            "alive": True, 
            "sniper": (i % 2 == 0), 
            "last_shoot": time.time() + random.uniform(1, 3)
        })

    def spawn_powerup(self):
        px, py = self.get_safe_spawn()
        self.state["items"] = [{"x": px, "y": py}]

    def reset_round(self, total=False):
        self.state.update({"bullets":[], "items":[], "explosions":[], "game_over":False, "winner_name":None})
    
        # Essas funções também devem ser atualizadas para usar o get_safe_spawn() internamente
        self.spawn_horde()
        self.spawn_powerup()
    
        for p in self.state["players"]:
        # 1. Buscamos uma coordenada que não colida com as paredes
            safe_x, safe_y = self.get_safe_spawn() 
        
        # 2. Aplicamos as coordenadas seguras ao jogador
            p.update({
                "alive": True, 
                "x": safe_x, 
                "y": safe_y, 
                "shots_left": 0, 
                "p_cross_active": False
            })
        
        if total: 
            p["score"] = 0
            
        print("[!] Jogo Reiniciado com posições seguras.")

    def update_physics(self):
        if self.state["game_over"]: return # Não processa física se o jogo acabou
        
        agora = time.time()
        self.state["explosions"] = [e for e in self.state["explosions"] if agora - e["t"] < 0.5]
        vivos = [p for p in self.state["players"] if p["alive"]]
        
        # IA Robôs com Desvio
        for r in [r for r in self.state["robots"] if r["alive"]]:
            if not r["sniper"] and vivos:
                alvo = min(vivos, key=lambda pl: math.hypot(pl["x"]-r["x"], pl["y"]-r["y"]))
                dx, dy = alvo["x"]-r["x"], alvo["y"]-r["y"]
                d = math.hypot(dx, dy)
                if d > 1:
                    nx = r["x"] + (dx/d) * 2.2
                    if not any(abs(nx - w["x"]) < 32 and abs(r["y"] - w["y"]) < 32 for w in self.state["walls"]): r["x"] = nx
                    ny = r["y"] + (dy/d) * 2.2
                    if not any(abs(r["x"] - w["x"]) < 32 and abs(ny - w["y"]) < 32 for w in self.state["walls"]): r["y"] = ny
            elif r["sniper"] and agora > r["last_shoot"]:
                for vx, vy in [(8,0), (-8,0), (0,8), (0,-8)]:
                    self.state["bullets"].append({"x":r["x"]+16, "y":r["y"]+16, "vx":vx, "vy":vy, "owner":"ROBOT", "color":(255,255,0)})
                r["last_shoot"] = agora + 3.0

        # Colisões e Tiros
        for p in vivos:
            for it in self.state["items"][:]:
                if math.hypot((p["x"]+16)-(it["x"]+16), (p["y"]+16)-(it["y"]+16)) < 35:
                    p["p_cross_active"], p["shots_left"] = True, 10
                    self.state["items"].remove(it)
                    threading.Timer(10, self.spawn_powerup).start()
            for r in [r for r in self.state["robots"] if r["alive"]]:
                if math.hypot(r["x"]-p["x"], r["y"]-p["y"]) < 30:
                    p["alive"] = False
                    self.state["explosions"].append({"x": p["x"], "y": p["y"], "t": agora})

        for b in self.state["bullets"][:]:
            b["x"] += b["vx"]; b["y"] += b["vy"]
            if any(abs(b["x"]-(w["x"]+20))<20 and abs(b["y"]-(w["y"]+20))<20 for w in self.state["walls"]):
                if b in self.state["bullets"]: self.state["bullets"].remove(b); continue
            
            for rob in [ro for ro in self.state["robots"] if ro["alive"]]:
                if b["owner"] != "ROBOT" and math.hypot(rob["x"]+16-b["x"], rob["y"]+16-b["y"]) < 25:
                    rob["alive"] = False; self.state["explosions"].append({"x":rob["x"], "y":rob["y"], "t":agora})
                    p_own = next((pl for pl in self.state["players"] if pl["name"] == b["owner"]), None)
                    if p_own: p_own["score"] += 10
                    if b in self.state["bullets"]: self.state["bullets"].remove(b)
                    break
            
            for pl in [p for p in self.state["players"] if p["alive"]]:
                if b["owner"] != pl["name"] and math.hypot(pl["x"]+16-b["x"], pl["y"]+16-b["y"]) < 25:
                    pl["alive"] = False; self.state["explosions"].append({"x":pl["x"], "y":pl["y"], "t":agora})
                    if b in self.state["bullets"]: self.state["bullets"].remove(b)
                    break

        # Término de Rodada
        if len(self.state["players"]) > 0:
            if not any(p["alive"] for p in self.state["players"]) or not any(r["alive"] for r in self.state["robots"]):
                # Avisa os clientes que o round acabou
                self.state["round_over"] = True
                self.broadcast_state() 
        
                # Pausa de 2 segundos para os alunos verem a mensagem
                time.sleep(2.0) 
        
                # Limpa a flag e reinicia
                self.state["round_over"] = False
                self.reset_round()
                

        for p in self.state["players"]:
            if p["score"] >= 300:
                self.state["game_over"] = True
                self.state["winner_name"] = p["name"]

    def broadcast_state(self):
        data = (json.dumps(self.state) + "###").encode('utf-8')
        for s in list(self.clients.keys()):
            try: s.sendall(data)
            except: self.remove(s)

    def handle_msg(self, s, d):
        if "RESTART_GAME" in d:
            self.reset_round(total=True)
            return

        p = next((p for p in self.state["players"] if p["name"] == self.clients.get(s)), None)
        if not p or not p["alive"] or self.state["game_over"]: return
        
        for m in d.split(";"):
            if m.startswith("IN|"):
                pts = m.split("|")
                if len(pts) < 5: continue
                dx, dy = (int(pts[2])-int(pts[1]))*6, (int(pts[4])-int(pts[3]))*6
                nx, ny = p["x"]+dx, p["y"]+dy
                if not any(abs(nx-w["x"])<30 and abs(ny-w["y"])<30 for w in self.state["walls"]): p["x"], p["y"] = nx, ny
                if dx or dy: p["last_dir"] = (dx*2, dy*2)
            elif "SHOOT" in m:
                dirs = [(12,0),(-12,0),(0,12),(0,-12)] if p["p_cross_active"] else [p.get("last_dir", (12,0))]
                for vx, vy in dirs:
                    self.state["bullets"].append({"x":p["x"]+16, "y":p["y"]+16, "vx":vx, "vy":vy, "owner":p["name"], "color":PLAYER_COLORS[p["sprite_id"]]})
                if p["p_cross_active"]: 
                    p["shots_left"] -= 1
                    if p["shots_left"] <= 0: p["p_cross_active"] = False
    
    def get_safe_spawn(self):
        while True:
            # Gera uma posição candidata
            tx = random.randint(80, WIDTH_ARENA - 80)
            ty = random.randint(80, HEIGHT - 80)
        
            # Verifica se colide com alguma parede (considerando o tamanho 32x32)
            collision = False
            for w in self.state["walls"]:
                if abs(tx - w["x"]) < 35 and abs(ty - w["y"]) < 35:
                    collision = True
                    break
        
            if not collision:
                return tx, ty

    def run(self):
        while self.running:
            r, _, _ = select.select(self.inputs, [], [], 0.02)
            for s in r:
                if s is self.sock:
                    c, a = s.accept(); c.setblocking(False); self.inputs.append(c)
                else:
                    try:
                        d = s.recv(4096).decode('utf-8')
                        if not d: self.remove(s); continue
                        if d.startswith("HELLO|"):
                            name = d.split("|")[1][:3].upper()
                            self.clients[s] = name
                            px, py = self.get_safe_spawn() # Busca posição segura aqui
                            self.state["players"].append({"name":name, "x":px, "y":py, "alive":True, "score":0, "sprite_id":len(self.state["players"])%8, "p_cross_active":False, "shots_left":0})
                        else: self.handle_msg(s, d)
                    except: self.remove(s)
            self.update_physics(); self.broadcast_state(); time.sleep(0.015)

    def remove(self, s):
        if s in self.clients:
            self.state["players"] = [p for p in self.state["players"] if p["name"] != self.clients[s]]
            del self.clients[s]
        if s in self.inputs: self.inputs.remove(s); s.close()

if __name__ == "__main__":
    import sys
    # Verifica se foi passado um argumento: python servidor.py <porta>
    porta = 5000
    if len(sys.argv) > 1:
        try:
            porta = int(sys.argv[1])
        except ValueError:
            print(f"[!] Porta inválida. Usando padrão {porta}")
            
    Server(porta).run()