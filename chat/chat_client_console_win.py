import socket
import threading
import sys
import msvcrt # Biblioteca nativa do Windows para captura de teclas

def receber_mensagens(sock):
    while True:
        try:
            data = sock.recv(1024)
            if not data: break
            
            mensagem = data.decode()
            
            # 1. Apaga a linha atual onde o usuário está digitando
            # \r volta ao início, ' '*79 limpa a linha, \r volta de novo
            sys.stdout.write('\r' + ' ' * 79 + '\r')
            
            # 2. Imprime a mensagem recebida
            sys.stdout.write(mensagem + '\n')
            
            # 3. Reescreve o prompt e o que o usuário já tinha digitado
            sys.stdout.write('> ' + ''.join(buffer_digitacao))
            sys.stdout.flush()
        except:
            break

def iniciar_cliente():
    global buffer_digitacao
    buffer_digitacao = []
    
    ip = input("IP do Servidor: ") or "127.0.0.1"
    porta = int(input("Porta do Servidor: "))
    nick = input("Nick: ")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, porta))
    sock.send(nick.encode())

    threading.Thread(target=receber_mensagens, args=(sock,), daemon=True).start()

    sys.stdout.write('> ')
    sys.stdout.flush()

    while True:
        if msvcrt.kbhit(): # Se uma tecla foi pressionada
            char = msvcrt.getch() # Lê a tecla
            
            # Se for ENTER (caractere \r ou \n)
            if char in [b'\r', b'\n']:
                linha = ''.join(buffer_digitacao)
                if linha.lower() == "/quit": break
                
                sock.send(linha.encode())
                
                buffer_digitacao = []
                sys.stdout.write('\n> ')
                sys.stdout.flush()
            
            # Se for BACKSPACE
            elif char == b'\x08':
                if len(buffer_digitacao) > 0:
                    buffer_digitacao.pop()
                    # Apaga o caractere visualmente no console
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            
            # Caractere normal
            else:
                try:
                    letra = char.decode('utf-8')
                    buffer_digitacao.append(letra)
                    sys.stdout.write(letra)
                    sys.stdout.flush()
                except: pass

    sock.close()

if __name__ == "__main__":
    iniciar_cliente()