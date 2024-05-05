import os, select, socket, sys, time , atexit , signal
import messages

ADDR = ("127.0.0.1", 2005)
MAXBYTES = 4096

fermeture_serveur = False

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

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
    for s in sockets:
        if s != serversocket and s != sys.stdin:
            s.send(data)


def recuperer_pseudos(data):
    mots = data.split(" ")
    pseudos = []
    texte = []
    for mot in mots:
        if mot.startswith('@'):
            pseudos.append(mot[1:])
        else:
            texte.append(mot)
    return (pseudos,str.join(' ',texte))


def gerer_message_client(data, socket):
    message = messages.decoder_message(data)    
    if message["type"] == "Connexion":
        #verification que le pseudo != admin et unique
        if message["message"] == "admin" or message["message"] in clients.values():
            #refuser le client
            envoi = messages.encoder_message("Refus", "le pseudo est deja pris ou invalide","---")
            envoyer_direct(envoi.encode(),socket)
        else:
            clients[socket] = message["pseudo"]
            message_bienvenue = f"Bienvenue dans le serveur ({clients[socket]})  \nil y a {len(clients)} utilisateurs connectés \ntapez !aide pour voir toutes les commandes"
            envoi = messages.encoder_message("Accept", message_bienvenue, message["pseudo"])
            envoyer_direct(envoi.encode(),socket)
            envoi2 = messages.encoder_message("Message serveur",f"nouveau joueur: {message['pseudo']} connecté ","Serveur")
            envoyer_autres(envoi2.encode(),socket)

    elif message["type"] == "Message":
        print(f"({clients[socket]}): {message['message']}")
        envoyer_autres(data,socket)

    elif message["type"] == "Message prive":
        
        decoupage = message["message"].split(" ")
        if len(decoupage) < 2:
            envoi = messages.encoder_message("Message serveur","utilisation de la commande: @nom message","Serveur")
            envoyer_direct(envoi.encode(),socket)
        else:
            pseudo_origine = message["pseudo"]
            
            cibles,message = recuperer_pseudos(message["message"])
            for cible in cibles:
                if cible == "Admin":
                    cibles.remove(cible)
                    print(f"mp de ({pseudo_origine}): {message}")
            envoi = messages.encoder_message("Message prive",message,pseudo_origine)
            for cible in cibles:
                trouve = False
                for (socket_cible,pseudo_cible) in clients.items():
                    temp=""
                    temp = cible
                    if cible == pseudo_cible:
                        envoyer_direct(envoi.encode(), socket_cible)
                        trouve = True
                    elif cible == pseudo_origine:
                        envoi = messages.encoder_message("Message serveur",f"pourquoi s'envoyer des message","Serveur")
                        envoyer_direct(envoi.encode(),socket)
                if not trouve:
                    
                    envoi = messages.encoder_message("Message serveur",f"utilisateur {cible} introuvable","Serveur")
                    envoyer_direct(envoi.encode(), socket)

    elif message["type"] == "List":
        envoi = messages.encoder_message("Message serveur", "Utilisateurs connectés: " + str.join(', ',clients.values()), "Serveur")
        envoyer_direct(envoi.encode(), socket)
    elif message["type"] == "Fin":
        #client se deconnecte
        if socket in clients:
            print(f"l'utilisateur deconnecté ({clients[socket]})")
            envoi = messages.encoder_message("Message serveur",f"l'utilisateur deconnecté ({clients[socket]})", "Serveur" )
            envoyer_autres(envoi.encode(),socket)
        else:
            #si l'utilisateur na pas mis de de pseudo
            print(f"Utilisateur ({socket.getsockname()[0]}) deconnecté")
            envoi = messages.encoder_message("Message serveur",f"Utilisateur ({socket.getsockname()[0]}) deconnecté", "Serveur" )
            envoyer_autres(envoi.encode(),socket)
        sockets.remove(socket)
        clients.pop(socket,None)
        socket.close()



def fermer_serveur():
    global fermeture_serveur
    if fermeture_serveur:
        return
    fermeture_serveur = True
    message_fermeture = messages.encoder_message("Message serveur", "Le serveur va s'arrêter.", "---").encode()
    print("\nle serveur va s'arreter\n")
    
    all_sockets = list(sockets)

    for s in all_sockets:
        if s != serversocket and s != sys.stdin:
            try:
                envoyer_direct(message_fermeture, s)
            except Exception as e:
                print(f"Erreur lors de l'envoi du message de fermeture à {s}: {e}")
            finally:
                try:
                    s.close()
                except Exception as e:
                    print(f"Erreur lors de la fermeture de la socket {s}: {e}")
                if s in sockets:
                    sockets.remove(s)

    # fermer la socket serveur
    try:
        serversocket.close()
    except Exception as e:
        print(f"Erreur lors de la fermeture du serveur: {e}")

def gerer_signal_fermeture(signum,frame):
    fermer_serveur()
    sys.exit(0)


with serversocket:

    signal.signal(signal.SIGINT, gerer_signal_fermeture)
    signal.signal(signal.SIGTERM, gerer_signal_fermeture)
    atexit.register(fermer_serveur)

    serversocket.bind(ADDR)
    serversocket.listen()
    sockets = [serversocket, sys.stdin, ]
    bannedclients = []
    clients = {}

    print(f"Le serveur est disponible à l'addresse {ADDR[0]}:{ADDR[1]}\ntapez !commandes pour les commandes")
    while len(sockets) > 0:
        try:
            sockets_lisible = [s for s in sockets if s.fileno() != -1]
            (readable, _, _) = select.select(sockets_lisible, [], [])
        except Exception as e:
            continue
        for s in readable:
            if (s == serversocket) & (s not in bannedclients):
                #1ere connexion
                (clientsocket, ADDR) = s.accept()
                sockets.append(clientsocket)
                print("Nouvelle connection de:", ADDR)
            elif s == sys.stdin: #cote serveur

                data = os.read(0,MAXBYTES)

                if len(data) == 0:
                    break
                data = data.decode()
                if data.strip() == "!close":
                    fermer_serveur()
                    sys.exit(0)
                elif data.strip() == "!list":
                    print("Utilisateurs connectés: " + str.join(', ',clients.values()))
                elif data.strip() == "!commandes":
                    print("Les commandes accesibles sont !close, !list , !commandes, @everyone , !forgive, !suspend, !ban")
                elif data.startswith("@"):
                    pseudo_origine = "Admin"
                    cibles,message = recuperer_pseudos(data)
                    for cible in cibles:
                        if cible == "everyone":
                            envoi = messages.encoder_message("Message",message,"Admin")
                            envoyer_publique(envoi.encode())
                            cibles.remove(cible)
                    envoi = messages.encoder_message("Message prive",message,pseudo_origine)
                    for cible in cibles:
                        trouve = False
                        for (socket_cible,pseudo_cible) in clients.items():
                            temp=""
                            temp = cible
                            if cible == pseudo_cible:
                                
                                envoyer_direct(envoi.encode(), socket_cible)
                                trouve = True
                            elif cible == pseudo_origine:
                                envoi = messages.encoder_message("Message serveur",f"pourquoi s'envoyer des message","Serveur")
                        if not trouve:
                            print(f"utilisateur {cible} introuvable")
                else:
                    print(f"commande invalide")
            else: #recevoir cote client
                data = s.recv(MAXBYTES)
                
                if len(data) > 0:
                    gerer_message_client(data,s)
                else:
                    #client se deconnecte
                    if s in clients:
                        print(f"l'utilisateur deconnecté ({clients[s]})")
                        envoi = messages.encoder_message("Message serveur",f"l'utilisateur deconnecté ({clients[s]})", "Serveur" )
                        envoyer_autres(envoi.encode(),s)
                    else:
                        #si l'utilisateur na pas mis de de pseudo
                        print(f"Utilisateur ({s.getsockname()[0]}) deconnecté")
                        envoi = messages.encoder_message("Message serveur",f"Utilisateur ({s.getsockname()[0]}) deconnecté", "Serveur" )
                        envoyer_autres(envoi.encode(),s)
                    sockets.remove(s)
                    clients.pop(s,None)
                    s.close()
                    
                              
serversocket.close()