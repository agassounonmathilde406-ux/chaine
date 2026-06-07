import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
import re
import time
import json
import os
import sys
import threading
from types import SimpleNamespace
import random
import requests
from flask import Flask  # Ajouté uniquement pour Render

# =============================================================================
# CONFIGURATION SERVEUR WEB FLASK POUR RENDER 🌐
# =============================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Nono Bot Anime Chain est en ligne et opérationnel ! 🥷🔥"

def run_flask():
    # Render donne automatiquement un PORT, sinon on prend 5000 par défaut
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# =============================================================================
# CONFIGURATION DU BOT ET CHEMINS 🔐
# =============================================================================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# METS TON TOKEN GAMEPLAY DIRECTEMENT ICI 🔐
TOKEN = "8931412327:AAHjvksW8S4aD6ZpG1GlttyxUeT0GUDuRmU"

bot = telebot.TeleBot(TOKEN)

# CHANGEMENT ICI : On utilise le dossier racine du projet GitHub sur Render
DOSSIER_STOCKAGE = "."
FICHIER_STATS = os.path.join(DOSSIER_STOCKAGE, "stats_chain.json")
ALPHABET = [chr(i) for i in range(ord('a'), ord('z') + 1)]

# CONFIGURATION DU CANAL OBLIGATOIRE (ID DE TON CANAL NA.PY)
CANAL_CIBLE = -1003757046872 

# ID UNIQUE DU SEUL GROUPE AUTORISÉ (CDO)
GROUPE_AUTORISE_ID = -1002643863313

# ID DU CRÉATEUR DU BOT AUTORISÉ À JOUER EN PV
ID_CREATEUR = 8659372528

# CONFIGURATION DE MOTARENA
MOTARENA_ID = -999
motArena_user = SimpleNamespace(id=MOTARENA_ID, username="motArena", first_name="MotArena")

VANNES_MOTARENA = [
    "T’as pas perdu, t’as juste montré au monde à quel point t’es nul.",
    "Même un mur aurait mieux joué que toi… au moins lui il bloque.",
    "Tu joues ou tu testes le bouton 'honte' en boucle ?",
    "T'as le QI d’un caillou, sans la solidité.",
    "J’ai pas gagné… c’est toi qui t’es écrasé tout seul.",
    "Ton cerveau c’est du Wi-Fi public : lent, instable, et tout le monde l’utilise.",
    "À ce niveau de nullité, c’est plus une défaite, c’est une œuvre d’art."
]

# =============================================================================
# STRUCTURE DES COMMANDES
# =============================================================================
COMMANDES_DM_AUTORISÉES = ["/start", "/aide"] 
COMMANDES_GROUPE_AUTORISÉES = []

COMMANDES_PASSE_PARTOUT = [
    "/game", "/kill", 
    "/ranking", "/classement", "/fkill", 
    "/bilan"
]

# ========================================================
# GESTION DES STATISTIQUES ET CLASSEMENT 📊
# ========================================================
def charger_stats():
    if os.path.exists(FICHIER_STATS):
        try:
            with open(FICHIER_STATS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def sauvegarder_stats(stats):
    try:
        if not os.path.exists(DOSSIER_STOCKAGE):
            os.makedirs(DOSSIER_STOCKAGE, exist_ok=True)
        with open(FICHIER_STATS, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Erreur sauvegarde stats: {e}")

def enregistrer_fin_partie(joueurs, gagnant_id, noms_joueurs):
    stats = charger_stats()
    for uid in joueurs:
        uid_str = str(uid)
        if uid_str not in stats:
            stats[uid_str] = {"nom": noms_joueurs.get(uid, f"Joueur {uid}"), "parties": 0, "victoires": 0, "eliminations": 0, "bot_demarre": True, "communaute_rejointe": True}
        
        stats[uid_str]["parties"] += 1
        stats[uid_str]["nom"] = noms_joueurs.get(uid, stats[uid_str]["nom"])
        
        if uid == gagnant_id:
            stats[uid_str]["victoires"] += 1
        else:
            stats[uid_str]["eliminations"] += 1
            
    sauvegarder_stats(stats)


# =============================================================================
# VÉRIFICATION ET DÉBLOCAGE AUTOMATIQUE LIVE VIA TELEGRAM 🔐
# =============================================================================
def verifier_adhesion_canal(user_id, user_first_name, chat_id, message_id_to_reply=None):
    stats = charger_stats()
    user_id_str = str(user_id)
    
    if user_id_str not in stats:
        stats[user_id_str] = {"nom": user_first_name, "parties": 0, "victoires": 0, "eliminations": 0, "bot_demarre": True, "communaute_rejointe": False}

    stats[user_id_str]["bot_demarre"] = True

    try:
        statut_canal = bot.get_chat_member(CANAL_CIBLE, user_id).status
        if statut_canal in ["member", "administrator", "creator"]:
            stats[user_id_str]["communaute_rejointe"] = True
            sauvegarder_stats(stats)
            return True
    except Exception as e:
        logging.error(f"Erreur get_chat_member pour {user_id}: {e}")

    stats[user_id_str]["communaute_rejointe"] = False
    sauvegarder_stats(stats)

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📢 Rejoindre le Canal Officiel", url="https://t.me/+i3Bk-Ml6aNwyYWRk"))
    
    texte_blocage = (
        f"⚠️ <b>Accès refusé, {user_first_name} !</b>\n\n"
        "Tu dois obligatoirement être membre de notre canal officiel pour participer à l'Anime Chain.\n\n"
        "👉 Rejoins le canal via le bouton ci-dessous puis relance ton action !"
    )

    if message_id_to_reply:
        bot.send_message(chat_id, texte_blocage, parse_mode="HTML", reply_markup=markup, reply_to_message_id=message_id_to_reply)
    else:
        bot.send_message(chat_id, texte_blocage, parse_mode="HTML", reply_markup=markup)
        
    return False


# ========================================================
# STRUCTURE DU JEU
# ========================================================
class AnimeChainGame:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.statut = "inscription"
        self.joueurs = []
        self.noms_joueurs = {}
        self.points = {}                 
        self.eliminated = set()
        self.index_tour = 0
        self.lettre_actuelle = ""
        self.animes_deja_cites = set()
        self.chrono_timer = None         
        self.lock = threading.Lock()     
        self.en_verification = False
        self.limite_temps_tour = 0.0     

    def cancel_chrono(self):
        if self.chrono_timer:
            self.chrono_timer.cancel()
            self.chrono_timer = None

    def mention_joueur(self, user_id):
        if user_id == MOTARENA_ID:
            return "🤖 <b>motArena</b>"
        nom = self.noms_joueurs.get(user_id, f"Joueur {user_id}")
        return f'<a href="tg://user?id={user_id}">{nom}</a>'

games = {}

def verifier_anime_global(chat_id, proposition):
    proposition_clean = proposition.strip().lower()
    lettre_fichier = proposition_clean[0] if proposition_clean else "a"
    if lettre_fichier not in ALPHABET:
        lettre_fichier = "a"

    chemin_fichier = os.path.join(DOSSIER_STOCKAGE, f"{lettre_fichier}.json")
    if os.path.exists(chemin_fichier):
        try:
            with open(chemin_fichier, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if proposition_clean in cache:
                titre_officiel = cache[proposition_clean]
                return {"statut": "trouve" if titre_officiel else "introuvable", "titre": titre_officiel}
        except Exception:
            pass

    try:
        bot.send_chat_action(chat_id, action="typing")
    except Exception:
        pass

    try:
        url = f"https://api.jikan.moe/v4/anime?q={proposition_clean}&limit=5"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", [])
            
            for anime_data in results:
                titre_officiel = anime_data.get("title_english") or anime_data.get("title")
                titre_mal = anime_data.get("title")
                
                alt_titles = [t.get("title", "").lower() for t in anime_data.get("titles", [])]
                if titre_mal:
                    alt_titles.append(titre_mal.lower())
                
                if titre_officiel and (titre_officiel.lower() == proposition_clean or proposition_clean in alt_titles):
                    try:
                        cache_actuel = {}
                        if os.path.exists(chemin_fichier):
                            with open(chemin_fichier, "r", encoding="utf-8") as f:
                                cache_actuel = json.load(f)
                        
                        cache_actuel[proposition_clean] = titre_officiel
                        cache_actuel[titre_officiel.lower()] = titre_officiel
                        if titre_mal:
                            cache_actuel[titre_mal.lower()] = titre_officiel
                        
                        with open(chemin_fichier, "w", encoding="utf-8") as f:
                            json.dump(cache_actuel, f, ensure_ascii=False, indent=4)
                    except Exception as err:
                        logging.error(f"Erreur écriture enrishissement JSON : {err}")
                        
                    return {"statut": "trouve", "titre": titre_officiel}
    except Exception as e:
        logging.error(f"Erreur lors de la requête de secours Jikan : {e}")

    return {"statut": "inconnu", "titre": None}

def extraire_lettre_fin(titre):
    lettres = re.sub(r'[^a-zA-Z]', '', titre)
    return lettres[-1].lower() if lettres else ""

def generer_texte_salon(game):
    texte = (
        "🌀🈳 <b>『 SALON ANIME CHAIN 』</b> 🈳🌀\n\n"
        "Chaque participant débute avec <b>3 points de vie</b> ❤️\n"
        "⏱ Le bot compte <b>20s</b>.\n\n"
        "📋 <b>Joueurs inscrits :</b>\n"
    )
    if not game.joueurs:
        texte += "<i>Aucun joueur pour le moment...</i>"
    else:
        for i, uid in enumerate(game.joueurs, start=1):
            texte += f"{i}- {game.mention_joueur(uid)}\n"
    return texte

def generer_clavier_salon(game):
    nb_joueurs = len(game.joueurs)
    markup = InlineKeyboardMarkup(row_width=2)
    b_rejoindre = InlineKeyboardButton(f"🎮 Rejoindre ({nb_joueurs})", callback_data="join_game")
    b_motarena = InlineKeyboardButton("🤖 Inviter motArena", callback_data="join_motarena")
    b_lancer = InlineKeyboardButton("🚀 Lancer", callback_data="play_game")
    b_terminer = InlineKeyboardButton("💥 Terminer", callback_data="kill_game")
    markup.add(b_rejoindre, b_motarena)
    markup.add(b_lancer, b_terminer)
    return markup

def verifier_vainqueur(game):
    joueurs_en_vie = [uid for uid in game.joueurs if uid not in game.eliminated]
    
    if len(joueurs_en_vie) == 1:
        game.statut = "ferme"
        gagnant_id = joueurs_en_vie[0]
        gagnant_mention = game.mention_joueur(gagnant_id)
        bot.send_message(game.chat_id, f"🏆 <b>Partie terminée ! Le vainqueur suprême est {gagnant_mention} !</b> 🎉", parse_mode="HTML")
        
        enregistrer_fin_partie(game.joueurs, gagnant_id, game.noms_joueurs)
        
        if gagnant_id == MOTARENA_ID:
            bot.send_message(game.chat_id, f"💬 motArena : « {random.choice(VANNES_MOTARENA)} »")
        if game.chat_id in games: del games[game.chat_id]
        return True
    elif len(joueurs_en_vie) == 0:
        game.statut = "ferme"
        bot.send_message(game.chat_id, "🏁 <b>Fin du jeu ! Tout le monde a été éliminé. Aucun vainqueur !</b>", parse_mode="HTML")
        enregistrer_fin_partie(game.joueurs, None, game.noms_joueurs)
        if game.chat_id in games: del games[game.chat_id]
        return True
    return False

def declencher_timeout_secret(game, joueur_id_au_moment_du_tour):
    with game.lock:
        if game.statut != "en_cours" or game.joueurs[game.index_tour] != joueur_id_au_moment_du_tour or game.en_verification:
            return
        try:
            bot.send_message(game.chat_id, "⏰ <b>0 seconde ! Le temps est écoulé !</b>", parse_mode="HTML")
            appliquer_sanction_sans_lock(game, raison="timeout")
        except Exception as e:
            print(f"Erreur envoi timeout: {e}")

def passer_au_joueur_suivant(game):
    game.cancel_chrono()
    if verifier_vainqueur(game):
        return

    if game.index_tour >= len(game.joueurs): 
        game.index_tour = 0
        
    while game.joueurs[game.index_tour] in game.eliminated:
        game.index_tour = (game.index_tour + 1) % len(game.joueurs)

    joueur_actuel_id = game.joueurs[game.index_tour]
    mention_actuel = game.mention_joueur(joueur_actuel_id)
    
    texte_tour = f"👤 À ton tour : {mention_actuel} (Vies: {game.points[joueur_actuel_id]}/3)\n"
    if game.lettre_actuelle:
        texte_tour += f"👉 Lettre imposée : 👑 <b>{game.lettre_actuelle.upper()}</b> 👑\n"
    else:
        texte_tour += "👉 Commence la chaîne avec l'anime de ton choix.\n"
    texte_tour += "⏳ <i>Tu as 20 secondes !</i>"

    bot.send_message(game.chat_id, text=texte_tour, parse_mode="HTML")
    game.limite_temps_tour = time.time() + 20.0

    if joueur_actuel_id == MOTARENA_ID:
        try:
            bot.send_chat_action(game.chat_id, action="typing")
        except Exception:
            pass
        threading.Thread(target=ia_reflexion_motarena, args=(game, game.lettre_actuelle)).start()
    else:
        game.chrono_timer = threading.Timer(20.0, declencher_timeout_secret, args=(game, joueur_actuel_id))
        game.chrono_timer.start()

def ia_reflexion_motarena(game, lettre_requise):
    # Ralentissement d'1.5 seconde pour éviter l'erreur 429
    time.sleep(1.5)

    lettre_fichier = lettre_requise.lower() if lettre_requise else random.choice(ALPHABET)
    proposition_trouvee = None
    
    chemin_fichier = os.path.join(DOSSIER_STOCKAGE, f"{lettre_fichier}.json")
    if os.path.exists(chemin_fichier):
        try:
            with open(chemin_fichier, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if isinstance(cache, dict) and cache:
                choix = [v for k, v in cache.items() if v.lower() not in game.animes_deja_cites and k.startswith(lettre_fichier)]
                if choix:
                    proposition_trouvee = random.choice(choix)
        except Exception:
            pass

    # MODIFICATION ICI : Si motArena ne trouve rien dans le fichier local, 
    # il tente sa chance sur l'API Jikan avec un mot aléatoire au lieu d'abandonner directement.
    if not proposition_trouvee:
        try:
            # On cherche un mot commun commençant par la lettre pour interroger Jikan
            url = f"https://api.jikan.moe/v4/anime?letter={lettre_fichier}&limit=10"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                results = response.json().get("data", [])
                choix_api = []
                for a in results:
                    titre = a.get("title_english") or a.get("title")
                    if titre and titre.lower() not in game.animes_deja_cites and titre.lower().startswith(lettre_fichier):
                        choix_api.append(titre)
                if choix_api:
                    proposition_trouvee = random.choice(choix_api)
        except Exception:
            pass

    if proposition_trouvee:
        bot.send_message(game.chat_id, proposition_trouvee)
        simuler_validation_motarena(game, proposition_trouvee)
    else:
        with game.lock:
            appliquer_sanction_sans_lock(game, raison="introuvable")

def simuler_validation_motarena(game, titre_officiel):
    with game.lock:
        game.en_verification = True
        
    game.animes_deja_cites.add(titre_officiel.lower())
    lettre_suivante = extraire_lettre_fin(titre_officiel)
    game.lettre_actuelle = lettre_suivante
    
    bot.send_message(
        game.chat_id,
        f"✅ <b>{titre_officiel.upper()}</b> validé !\n"
        f"👉 Prochaine lettre : 🔥 <b>{lettre_suivante.upper()}</b> 🔥",
        parse_mode="HTML"
    )

    with game.lock:
        game.index_tour = (game.index_tour + 1) % len(game.joueurs)
        game.en_verification = False
        passer_au_joueur_suivant(game)

def aplicar_sanction_sans_lock(game, raison):
    # (Correction faute de frappe interne pour correspondre aux appels du code)
    appliquer_sanction_sans_lock(game, raison)

def appliquer_sanction_sans_lock(game, raison):
    game.cancel_chrono()
    joueur_id = game.joueurs[game.index_tour]
    mention_sanctionne = game.mention_joueur(joueur_id)
    
    game.points[joueur_id] -= 1
    points_restants = game.points[joueur_id]

    if raison == "timeout":
        texte = f"💥 {mention_sanctionne} <b>a été trop lent ! Temps écoulé !</b> <b>-1 point</b>"
    elif raison == "doublon":
        texte = f"❌ Déjà cité ! <b>-1 point</b> pour {mention_sanctionne}"
    else:
        texte = f"❌ Anime introuvable ! <b>-1 point</b> pour {mention_sanctionne}"

    texte += f" (Reste : {points_restants}/3 pts)."

    if points_restants <= 0:
        texte += f"\n💀 {mention_sanctionne} <b>est ÉLIMINÉ de la partie !</b>"
        game.eliminated.add(joueur_id)

    bot.send_message(game.chat_id, text=texte, parse_mode="HTML")
    game.index_tour = (game.index_tour + 1) % len(game.joueurs)
    passer_au_joueur_suivant(game)

def verifier_si_admin(message):
    if message.chat.type == "private":
        return True
    try:
        statut = bot.get_chat_member(message.chat.id, message.from_user.id).status
        return statut in ['creator', 'administrator']
    except Exception:
        return False

def send_admin_alert(text):
    logging.warning(text)


# =============================================================================
# ANTIVOL : SÉCURITÉ ET EXPULSION SANS PITIÉ DES AUTRES GROUPES 🚷
# =============================================================================

@bot.my_chat_member_handler()
def securite_anti_ajout_groupe(update):
    if update.new_chat_member.status in ["member", "administrator"]:
        chat_id = update.chat.id
        
        if chat_id == GROUPE_AUTORISE_ID or update.chat.type == "private":
            return
            
        inviteur = update.from_user
        username_inviteur = f"@{inviteur.username}" if inviteur.username else inviteur.first_name
        sticker_id = "CAACAgQAAxkBAAEEaxZqJYhwkYVQ_OUTRvVDPyrYc7KlfgACIRkAApR_8VJw0rs8kSuByzsE"
        
        try:
            bot.send_message(chat_id, f"🚨 Qui t'a permis de m'ajouter ici {username_inviteur} ? C'est hors de question.")
            bot.send_sticker(chat_id, sticker_id)
            time.sleep(1.5)
            bot.leave_chat(chat_id)
            print(f"[-] Expulsion réussie du groupe non-autorisé {chat_id} (Ajouté par {username_inviteur})")
        except Exception as e:
            logging.error(f"Erreur lors de l'auto-expulsion : {e}")


# =============================================================================
# CENTRALISATION ET DISPATCH DES COMMANDES ⚙️
# =============================================================================

def traiter_commande(message):
    command = message.text.split()[0].lower()

    # --- Commande /start ---
    if command.startswith("/start"):
        user_id = str(message.from_user.id)
        stats = charger_stats()
        display_name = message.from_user.username or message.from_user.first_name
        
        if user_id not in stats:
            stats[user_id] = {"nom": display_name, "parties": 0, "victoires": 0, "eliminations": 0, "bot_demarre": True, "communaute_rejointe": False}
        stats[user_id]["bot_demarre"] = True
        sauvegarder_stats(stats)

        accueil_text = (
            "🌀🈳 <b>『 𝐀𝐍𝐈𝐌𝐄 𝐂𝐇𝐀𝐈𝐍 – Le
