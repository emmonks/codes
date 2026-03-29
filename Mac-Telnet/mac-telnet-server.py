import socket
import struct
import subprocess
import sys
import os

ETH_TYPE = b'\x88\xb5'

def get_mac(ifname):
    import fcntl
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack('256s', bytes(ifname, 'utf-8')[:15]))
        return info[18:24]
    except: return None

def run_server(interface, verbose):
    my_mac = get_mac(interface)
    # Obtém o nome do nó no CORE (ex: n1, n2...)
    node_name = socket.gethostname()
    
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x88B5))
    s.bind((interface, 0))
    
    print("Servidor MAC-Telnet em: " + interface)
    print("Hostname: {} | MAC: {}".format(node_name, ':'.join('%02x' % b for b in my_mac)))

    while True:
        packet, addr = s.recvfrom(2048)
        src_mac = packet[6:12]
        payload = packet[14:].decode('utf-8', errors='ignore')

        if verbose:
            print("[LOG] Recebido: " + payload)

        # Resposta de Descoberta ou Resolução de Nome
        if payload == "DISCOVER" or payload == "QUERY_NAME:" + node_name:
            response = "PONG|{}|{}".format(node_name, ':'.join('%02x' % b for b in my_mac))
        elif payload.startswith("QUERY_NAME:"):
            continue # Ignora se a pergunta não for para mim
        else:
            try:
                response = subprocess.check_output(payload, shell=True, stderr=subprocess.STDOUT).decode()
            except Exception as e:
                response = "Erro: " + str(e)

        resp_packet = src_mac + my_mac + ETH_TYPE + response.encode()
        s.send(resp_packet)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: sudo python3 mac_server.py <interface> [-v]")
    else:
        run_server(sys.argv[1], "-v" in sys.argv)