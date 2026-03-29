import socket
import threading
import sys
import tty
import termios
import select

def receber_mensagens(sock, fd_original, settings_original):
    """Thread corrigida para tratar múltiplas linhas no modo Raw"""
    global buffer_digitacao
    while True:
        try:
            data = sock.recv(2048) # Aumentado para suportar listas grandes
            if not data: break
            
            # 1. Decodifica e trata todas as quebras de linha
            mensagem = data.decode().replace('\n', '\r\n')
            
            # 2. Limpa a linha do prompt atual
            sys.stdout.write('\r\033[K')
            
            # 3. Imprime a mensagem (garantindo que termine em nova linha com retorno)
            if not mensagem.endswith('\r\n'):
                mensagem += '\r\n'
            
            sys.stdout.write(mensagem)
            
            # 4. Redesenha o prompt na margem esquerda
            sys.stdout.write('> ' + ''.join(buffer_digitacao))
            sys.stdout.flush()
        except:
            break

def iniciar_cliente():
    global buffer_digitacao
    buffer_digitacao = []
    
    print("--- CLIENTE IRC ACADÊMICO (LINUX CONSOLE) ---")
    ip = input("IP do Servidor: ") or "127.0.0.1"
    porta = int(input("Porta do Servidor: "))
    nick = input("Nick: ")

    # Configuração da Conexão
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, porta))
    sock.send(nick.encode())

    # Salva as configurações originais do terminal para restaurar ao sair
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        # Coloca o terminal em modo RAW (captura tecla a tecla)
        tty.setraw(sys.stdin.fileno())
        
        threading.Thread(target=receber_mensagens, args=(sock, fd, old_settings), daemon=True).start()

        sys.stdout.write('> ')
        sys.stdout.flush()

        while True:
            # select.select verifica se há dados para ler no teclado sem bloquear a thread
            if select.select([sys.stdin], [], [], 0.1)[0]:
                char = sys.stdin.read(1)
                
                # Se for ENTER (\r no modo raw)
                if char == '\r':
                    linha = ''.join(buffer_digitacao)
                    if linha.lower() == "/quit": break
                    
                    sock.send(linha.encode())
                    buffer_digitacao = []
                    sys.stdout.write('\r\n> ')
                    sys.stdout.flush()
                
                # Se for BACKSPACE (caractere 127 no Linux)
                elif char == '\x7f':
                    if len(buffer_digitacao) > 0:
                        buffer_digitacao.pop()
                        # \b volta um, espaço apaga, \b volta de novo
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                
                # Se for CTRL+C (caractere \x03)
                elif char == '\x03':
                    break
                
                # Caractere normal
                else:
                    buffer_digitacao.append(char)
                    sys.stdout.write(char)
                    sys.stdout.flush()

    finally:
        # IMPORTANTE: Restaura o terminal ao modo normal ("cooked")
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sock.close()
        print("\nConexão encerrada.")

if __name__ == "__main__":
    iniciar_cliente()