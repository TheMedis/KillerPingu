import os, select, socket, sys, time
import messages

ADDR = ("127.0.0.1", 2010)
MAXBYTES = 4096


serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def test_print(string):
    print("\n--------------------\n")
    print(string)
    print("\n--------------------\n")

def envoyer_direct(data,socket):
    socket.send(data)

def envoyer_autres(data,socket):
    for s in sockets:
        if s != serversocket and s != socket and s != sys.stdin:
            s.send(data)

def envoyer_publique(data):
    for s in socketlist:
        if s != serversocket and s != sys.stdin:
            s.send(data)


def gerer_message_client(data, socket):
    message = messages.decoder_message(data)    
    if message["type"] == "Connexion":
        #verification que le pseudo != admin et unique
        if message["message"] == "admin" or message["message"] in clients.values():
            #enregistrer le client
            envoi = messages.encoder_message("Refus", "le pseudo est deja pris ou invalide","---")
            envoyer_direct(data,socket)
        else:
            clients[socket] = message["pseudo"]
            message_bienvenue = f"Bienvenue dans le serveur ({clients[socket]})  \nil y a {len(clients)} utilisateurs connectés \ntapez /aide pour voir toutes les commandes"
            envoi = messages.encoder_message("Accept", message_bienvenue, message["pseudo"])
            envoyer_direct(envoi.encode(),socket)

    elif message["type"] == "Message":
        print(f"({clients[socket]}): {message['message']}")
        envoyer_autres(data,socket)

        


def fermer_serveur():
    shutdown_message = messages.encoder_message("Termination", "Le serveur va s'arrêter.", "---").encode()
    for s in sockets:
        if s != serversocket and s != sys.stdin:
            try:
                envoyer_direct(shutdown_message, s)
                s.close()
            except Exception as e:
                print(f"Error fermeture socket: {e}")
    serversocket.close()
    sys.exit(0) 


with serversocket:
    serversocket.bind(ADDR)
    serversocket.listen()
    sockets = [serversocket, sys.stdin, ]
    bannedclients = []
    clients = {}

    print(f"Le serveur est disponible à l'addresse {ADDR[0]}:{ADDR[1]}\n")
    while len(sockets) > 0:
        (readable, _, _) = select.select(sockets, [], [])
        for s in readable:
            if (s == serversocket) & (s not in bannedclients):
                (clientsocket, ADDR) = s.accept()
                sockets.append(clientsocket)
                print("Nouvelle connection de:", ADDR)
            elif s == sys.stdin: #cote serveur

                data = os.read(0,MAXBYTES)

                if len(data) == 0:
                    break
                data = data.decode()
                if data.strip() == "/exit":
                    fermer_serveur()
                else:
                    print(f"jai recu  {data}")
            else: #cote client
                data = s.recv(MAXBYTES)
                
                if len(data) > 0:
                    gerer_message_client(data,s)
                else:
                    print(f"user has disconnected ({clients[s]})")
                    sockets.remove(s)
                    s.close()
                    
                              
serversocket.close()