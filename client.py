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
        print("ERREUR: Le Fifo existe deja ")
    except Exception as erreur:
        print(f"probleme pendant la creation de FIFO: {erreur}")

def creation_log_fichier(log_path):
    try:
        f=os.open(log_path,os.O_CREAT|os.O_RDWR)
        os.dup2(f,1)
    except Exception as erreur: 
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
        print(f"Erreur survenu durant l'ouverture des terminaux: {erreur}")
        


def Ecrire_to_LOG(data):
    global PSEUDO
    try:
        print(f"({PSEUDO}): {data.decode()}")
    except:
        print("erreur durant l'ecriture LOG")


def gerer_signal(signum,frame):
    nettoyage()
    sys.exit(0)

def nettoyage():
    try:
        if os.path.exists(PIPE_PATH):
            os.unlink(PIPE_PATH)
        if os.path.exists(LOG_PATH):
            pass
            os.remove(LOG_PATH)
        for key, pid in pids_enfants.items():
            if pid is not None:
                os.kill(pid, signal.SIGTERM)
                os.waitpid(pid, 0)

    except Exception as erreur:
       print(f"Erreur pendant le nettoyage: {erreur}")



def gerer_message(data,socket):
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
        s.connect(sockaddr)
        print("veuillez entrer votre pseudo")
        while True:
            try:
                listened_descriptors, _, _ = select.select([fifo, s], [], [])
                
                if fifo in listened_descriptors:
                    data = os.read(fifo, MAXBYTES)
                    
                    if len(data) == 0:
                        break # gerer fermeture
                    data = data[:-1]
                    if not PSEUDO_TROUVE:
                        message = messages.encoder_message("Connexion",data.decode(),data.decode())
                        s.send(message.encode())
                    else:
                        message = messages.encoder_message("Message",data.decode(),PSEUDO)
                        Ecrire_to_LOG(data)

                        s.send(message.encode())
                
                elif s in listened_descriptors:
                    data = s.recv(MAXBYTES)
                    
                    if len(data) == 0:
                        break #gerer socket deconnexion
                    
                    gerer_message(data,s)
            except Exception as erreur:
                print(f"erreur durant envoy de messages: {erreur}")
                nettoyage()
                sys.exit(1)
                
