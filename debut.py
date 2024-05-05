import os, select, socket, sys ,signal , atexit
import messages

if len(sys.argv) != 3:
    print('Usage:', sys.argv[0])
    sys.exit(1)

MAXBYTES = 4096
try:
    pid = os.getpid()
except Exception as erreur:
    print(f"erreur survenur pendant la creation de FIFO et LOG: {erreur}")
LOG_PATH=f"/var/tmp/killer{pid}.log"
PIPE_PATH=f"/var/tmp/killer{pid}.fifo"

COMMANDE_PIPE=["xterm","-e" ,f"cat > {PIPE_PATH}"]
COMMANDE_LOG=["xterm" ,"-e" ,f"tail -f {LOG_PATH}"]

HOST = sys.argv[1]
PORT = int(sys.argv[2])

OLDTERM = sys.stdout.fileno()


PSEUDO_TROUVE = False

pids_enfants = {}

sockaddr = (HOST, PORT)

def test_print(string):
    print("\n--------------------\n")
    print(string)
    print("\n--------------------\n")

def creation_pipe(pipe_path):
    try:
        os.mkfifo(pipe_path)
    except FileExistsError:
        affichage_standard()
        print("ERREUR: Le Fifo existe deja ")
    except Exception as erreur:
        affichage_standard()
        print(f"probleme pendant la creation de FIFO: {erreur}")

def creation_log_fichier(log_path):
    global OLDTERM
    try:
        log = os.open(log_path, os.O_CREAT | os.O_WRONLY | os.O_APPEND)
        OLDTERM = os.dup(sys.stdout.fileno())  # Save the current stdout
        os.dup2(log, sys.stdout.fileno())  # Redirect stdout to log file
    except Exception as erreur: 
        affichage_standard()
        print(f"probleme survenu durant la creation du log: {erreur}")

def ouverture_fifo(pipe_path):
    fd = os.open(pipe_path, os.O_RDONLY | os.O_NONBLOCK)
    return fd


def ouverture_terminaux(commande_log, commande_pipe):
    global pids_enfants
    try:
        pid_pipe = os.fork()
        if pid_pipe == 0:
            os.execvp("xterm", commande_pipe)
        else:
            pids_enfants["pipe"] = pid_pipe
            pid_log = os.fork()
            if pid_log == 0:
                os.execvp("xterm", commande_log)
            else:
                pids_enfants["log"] = pid_log
    except Exception as erreur:
        affichage_standard()
        print(f"Erreur survenu durant l'ouverture des terminaux: {erreur}")
        


def Ecrire_to_LOG(data):
    global PSEUDO
    try:
        print(f"({PSEUDO}): {data.decode()}")
    except:
        affichage_standard()
        print("erreur durant l'ecriture LOG")


def gerer_signal(signum,frame):
    nettoyage()
    sys.exit(0)

def affichage_standard():
    global fifo
    os.dup2(OLDTERM,sys.stdout.fileno())

def nettoyage():
    try:
        if os.path.exists(PIPE_PATH):
            os.unlink(PIPE_PATH)
        if os.path.exists(LOG_PATH):
            os.remove(LOG_PATH)
        for key, pid in pids_enfants.items():
            if pid is not None:
                try:
                    os.kill(pid, signal.SIGTERM)
                    pids_enfants[key] = None
                    os.waitpid(pid, 0)
                except OSError as erreur:
                    affichage_standard()
                    print(f" erreur pendant la fermeture des processus {pid}: {erreur}")

    except Exception as erreur:
        affichage_standard()
        print(f"Erreur pendant le nettoyage: {erreur}")

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


def gerer_message(data):
    global PSEUDO_TROUVE
    global PSEUDO
    message = messages.decoder_message(data)
    if message["type"] == "Refus":
        afficher = "pseudo invalide entrez un nouveau"
        print(afficher)
    elif message["type"] == "Accept":
        PSEUDO_TROUVE = True
        PSEUDO = message["pseudo"]
        print(message["message"])
    elif message["type"] == "Message":
        print(f"({message['pseudo']}): {message['message']}")
    elif message["type"] == "Message serveur":
        print(f"{message['message']}")
    elif message["type"] == "Message prive":
        print(f"Mp de {message['pseudo']}: {message['message']}")
 

def gerer_commande(data,socket):
    message = data.split(" ")
    if message[0] == "!list":
        envoi = messages.encoder_message("List"," ",PSEUDO)
        socket.send(envoi.encode())
    elif message[0] == "!exit":
        envoi = messages.encoder_message("Fin"," ", PSEUDO)
        socket.send(envoi.encode())
    elif message[0] == "!aide":
        print(f"les commandes sont: @nom message, !list, !exit, !aide")

if __name__ =="__main__":
    

    signal.signal(signal.SIGINT, gerer_signal)
    signal.signal(signal.SIGTERM, gerer_signal)
    atexit.register(nettoyage)

    creation_log_fichier(LOG_PATH)
    creation_pipe(PIPE_PATH)
    ouverture_terminaux(COMMANDE_LOG,COMMANDE_PIPE)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    fifo = ouverture_fifo(PIPE_PATH)

    
    PSEUDO = ""

    with s:
        try:
            s.connect(sockaddr)
        except:
            affichage_standard()
            print("erreur durant la connexion: connexion refusé")
            nettoyage()
            sys.exit(1)
        print("veuillez entrer votre pseudo")
        while True:
            try:
                listened_descriptors, _, _ = select.select([fifo, s], [], [])
                
                if fifo in listened_descriptors:
                    data = os.read(fifo, MAXBYTES)
                     #if os.fstat(fifo).st_nlink == 0:
                    if len(data) == 0:
                        affichage_standard()
                        print("le fifo est fermé, deconnexion.")
                        os.close(fifo)
                        break  # No longer read from a closed FIFO
                    data = data[:-1]
                    if not PSEUDO_TROUVE:
                        message = messages.encoder_message("Connexion",data.decode(),data.decode())
                        s.send(message.encode())
                    else:
                        if (data.decode()).startswith("@"):
                            message = messages.encoder_message("Message prive",data.decode(),PSEUDO)
                            cibles,texte = recuperer_pseudos(data.decode())
                            for cible in cibles:
                                afficher = f"mp vers ({cible}): {texte}"
                                Ecrire_to_LOG(afficher.encode())
                            s.send(message.encode())
                        
                        elif (data.decode()).startswith("!"):
                            gerer_commande(data.decode(),s)
                        
                        else:
                            message = messages.encoder_message("Message",data.decode(),PSEUDO)
                            Ecrire_to_LOG(data)
                            s.send(message.encode())
                
                elif s in listened_descriptors:
                    data = s.recv(MAXBYTES)
                    
                    if len(data) == 0:
                        print("le serveur a fermé la connexion.")
                        s.close()
                        break
                    gerer_message(data)
            except Exception as erreur:
                affichage_standard()
                print(f"erreur durant envoy de messages: {erreur}")
                nettoyage()
                sys.exit(1)
                
