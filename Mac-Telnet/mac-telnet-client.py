import socket
import struct
import sys

ETH_TYPE = b'\x88\xb5'

def get_mac(ifname):
    import fcntl
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack('256s', bytes(ifname, 'utf-8')[:15]))
        return info[18:24]
    except: return b'\x00'*6

def resolve_name_to_mac(s, interface, my_mac, name):
    print("Resolvendo MAC para o nome: " + name)
    pkt = b'\xff'*6 + my_mac + ETH_TYPE + ("QUERY_NAME:" + name).encode()
    s.send(pkt)
    try:
        resp = s.recv(2048)
        data = resp[14:].decode().split('|')
        if data[0] == "PONG" and data[1] == name:
            return data[2] # Retorna o MAC em string
    except socket.timeout:
        return None

def run_client(interface, target):
    my_mac = get_mac(interface)
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x88B5))
    s.bind((interface, 0))
    s.settimeout(2.0)

    # 1. Modo Descoberta
    if target == "-l":
        s.send(b'\xff'*6 + my_mac + ETH_TYPE + b"DISCOVER")
        try:
            resp = s.recv(2048)
            print("Servidor encontrado: " + resp[14:].decode())
        except socket.timeout:
            print("Nenhum servidor na rede.")
        return

    # 2. Resolução de Nome (se não for formato de MAC)
    if ":" not in target:
        mac_resolved = resolve_name_to_mac(s, interface, my_mac, target)
        if mac_resolved:
            print("Nome resolvido! MAC: " + mac_resolved)
            target = mac_resolved
        else:
            print("Erro: Não foi possível localizar o nó " + target)
            return

    # 3. Shell Interativo
    dst_mac = bytes.fromhex(target.replace(':', ''))
    print("Conectado a {}...".format(target))
    
    while True:
        cmd = input("mac-telnet@{} $ ".format(target))
        if cmd.lower() in ['exit', 'quit']: break
        if not cmd.strip(): continue

        s.send(dst_mac + my_mac + ETH_TYPE + cmd.encode())
        try:
            resp = s.recv(2048)
            print(resp[14:].decode())
        except socket.timeout:
            print("Timeout.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: sudo python3 mac_client.py <interface> [-l | <MAC> | <HOSTNAME>]")
    else:
        run_client(sys.argv[1], sys.argv[2])