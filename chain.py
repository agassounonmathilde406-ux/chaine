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
# RESTE DE TON CODE D'ORIGINE STRICTEMENT SANS MODIFICATION 🔐
# =============================================================================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# METS TON TOKEN GAMEPLAY DIRECTEMENT ICI 🔐
TOKEN = "8090418346:AAG0-un8Zbrslc-gECB8j_MWoo1gq6rTmV8"

bot = telebot.TeleBot(TOKEN)

DOSSIER_STOCKAGE = "/storage/emulated/0/Callbreak."
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
    # Rendre motArena lent d'1.5 seconde lorsqu'il rejoint le jeu actif pour éviter l'erreur 429
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
            "🌀🈳 <b>『 𝐀𝐍𝐈𝐌𝐄 𝐂𝐇𝐀𝐈𝐍 – Le jeu de la dernière lettre 』</b> 🈳🌀\n"
            "<i>— Un seul mot d’ordre : enchaîne… ou tu tombes.</i>\n\n"
            "« Otakus du Cabinet,\n"
            "Bienvenue dans un duel verbal à haute tension.\n"
            "❓ <b>Comment jouer ?</b>\n"
            "Pour découvrir toutes les règles complètes, tape ou clique sur : /aide"
        )
        
        try:
            statut = bot.get_chat_member(CANAL_CIBLE, message.from_user.id).status
            if statut in ["member", "administrator", "creator"]:
                stats[user_id]["communaute_rejointe"] = True
                sauvegarder_stats(stats)
        except Exception:
            pass

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("📢 Rejoindre la communauté", url="https://t.me/+i3Bk-Ml6aNwyYWRk"))
        bot.send_message(message.chat.id, accueil_text, parse_mode="HTML", reply_markup=markup)
        
    # --- Commande /aide ---
    elif command.startswith("/aide"):
        vannes_aide = [
            "Je ne suis pas là pour t'expliquer, mais pour te briser la chaîne ! 🦾💀",
            "T'as le QI d’un caillou, prépare-toi à perdre tes points. 🧠🚫",
            "Même un mur aurait plus de mémoire que toi... 😏"
        ]
        replique_choisie = random.choice(vannes_aide)
        
        help_text = (
            f"🤖 <b>Salut, moi c'est motArena !</b>\n\n"
            f"Je parie que t'es là parce que tu as besoin d'aide 😄😆\n"
            f"« <i>{replique_choisie}</i> »\n\n"
            f"👉 <a href='https://cadobot.my.canva.site/caqejtg2b5z3cmkv'>𝖢𝗅𝗂𝗊𝗎𝖾 𝗂𝖼𝗂 𝗉𝗈𝗎𝗋 𝗅𝗂𝗋𝖾 𝗅𝖾𝗌 𝖱𝖤𝖦𝖫𝖤𝖲 𝖣𝖴 𝖩𝖤𝖴 📜</a>"
        )
        
        try:
            with open("madara.jpg", "rb") as photo:
                bot.send_photo(
                    chat_id=message.chat.id,
                    photo=photo,
                    caption=help_text,
                    parse_mode="HTML"
                )
        except FileNotFoundError:
            bot.send_message(message.chat.id, help_text, parse_mode="HTML")
        except Exception:
            bot.send_message(message.chat.id, help_text, parse_mode="HTML")

    # --- Commande /game ---
    elif command.startswith("/game"):
        if message.chat.type == "private" and message.from_user.id != ID_CREATEUR:
            bot.reply_to(message, "❌ <b>Tu ne peux pas lancer de partie en privé !</b>\nCrée ton salon directement dans le groupe officiel CDO.")
            return

        if not verifier_adhesion_canal(message.from_user.id, message.from_user.first_name, message.chat.id, message.message_id):
            return

        chat_id = message.chat.id
        user = message.from_user
        if chat_id in games and games[chat_id].statut != "ferme":
            bot.reply_to(message, "⚠️ Une partie est déjà lancée ici.")
            return
            
        game = AnimeChainGame(chat_id)
        games[chat_id] = game
        game.joueurs.append(user.id)
        game.noms_joueurs[user.id] = user.first_name
        game.points[user.id] = 3
        bot.send_message(chat_id, generer_texte_salon(game), parse_mode="HTML", reply_markup=generer_clavier_salon(game))

    # --- Commande /kill ---
    elif command.startswith("/kill"):
        chat_id = message.chat.id
        if chat_id not in games or games[chat_id].statut == "ferme":
            bot.reply_to(message, "❌ Aucun jeu actif.")
            return
        games[chat_id].cancel_chrono()
        del games[chat_id]
        bot.send_message(chat_id, "💥 <b>La partie a été réinitialisée de force.</b>", parse_mode="HTML")

    # --- Dashboard, Bilans & Classements ---
    elif command.startswith("/ranking") or command.startswith("/classement"):
        stats = charger_stats()
        if not stats:
            bot.reply_to(message, "📊 Aucun historique disponible.")
            return
        
        liste_joueurs = {uid: data for uid, data in stats.items() if uid != str(MOTARENA_ID)}
        
        joueurs_tries = sorted(liste_joueurs.items(), key=lambda item: (item[1].get('victoires', 0), -item[1].get('eliminations', 0)), reverse=True)
        texte = "🏆 <b>『 TABLEAU DES CHAMPIONS ANIME CHAIN 』</b> 🏆\n\n"
        for idx, (uid, data) in enumerate(joueurs_tries[:10], start=1):
            medaille = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "🏅"
            texte += f"{medaille} {idx}. <b>{data.get('nom', 'Inconnu')}</b>\n┗ 👑 {data.get('victoires', 0)} Vict. | 💀 {data.get('eliminations', 0)} Élim.\n\n"
        bot.send_message(message.chat.id, texte, parse_mode="HTML")

    elif command.startswith("/bilan"):
        stats = charger_stats()
        user_id = str(message.from_user.id)
        if user_id not in stats:
            bot.reply_to(message, "⚠️ Vous n'avez pas encore de statistiques enregistrées.")
            return
        s = stats[user_id]
        tag_joueur = f"<a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>"
        text = (
            f"<b>📊 BILAN ANIME CHAIN DE : {tag_joueur}</b>\n\n"
            f"<blockquote>✅ <b>Victoires</b> : {s.get('victoires', 0)}</blockquote>\n"
            f"<blockquote>❌ <b>Éliminations</b> : {s.get('eliminations', 0)}</blockquote>\n"
            f"<blockquote>🎮 <b>Parties jouées</b> : {s.get('parties', 0)}</blockquote>"
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML")

    # --- Commandes d'Administration ---
    elif command.startswith("/fskip"):
        if not verifier_si_admin(message): return
        chat_id = message.chat.id
        if chat_id in games and games[chat_id].statut == "en_cours":
            game = games[chat_id]
            with game.lock:
                bot.send_message(chat_id, "⏭ <b>L'administrateur a forcé le passage !</b>", parse_mode="HTML")
                game.cancel_chrono()
                game.index_tour = (game.index_tour + 1) % len(game.joueurs)
                passer_au_joueur_suivant(game)

    elif command.startswith("/fkill"):
        if not verifier_si_admin(message): return
        chat_id = message.chat.id
        if chat_id in games:
            games[chat_id].cancel_chrono()
            del games[chat_id]
            bot.reply_to(message, "🗑️ <b>Session détruite par l'administrateur.</b>", parse_mode="HTML")

    elif command.startswith("/fheal"):
        if not verifier_si_admin(message): return
        chat_id = message.chat.id
        if chat_id in games and games[chat_id].statut == "en_cours":
            game = games[chat_id]
            joueur_id = game.joueurs[game.index_tour]
            with game.lock:
                if game.points[joueur_id] < 3:
                    game.points[joueur_id] += 1
                    bot.reply_to(message, f"❤️ <b>Vie restaurée à {game.mention_joueur(joueur_id)} ({game.points[joueur_id]}/3)</b>", parse_mode="HTML")


# =============================================================================
# FILTRES DE SÉCURITÉ ET INTERCEPTION DES COMMANDES 🛡️
# =============================================================================

@bot.message_handler(func=lambda message: message.text and message.text.startswith("/"))
def dispatch_global_commandes(message):
    chat_id = message.chat.id
    
    if message.chat.type != "private" and chat_id != GROUPE_AUTORISE_ID:
        coupable = message.from_user
        username_coupable = f"@{coupable.username}" if coupable.username else coupable.first_name
        sticker_id = "CAACAgQAAxkBAAEEaxZqJYhwkYVQ_OUTRvVDPyrYc7KlfgACIRkAApR_8VJw0rs8kSuByzsE"
        try:
            bot.send_message(chat_id, f"🚨 Je n'ai rien à faire ici {username_coupable}. Je me casse.")
            bot.send_sticker(chat_id, sticker_id)
            time.sleep(1.5)
            bot.leave_chat(chat_id)
        except Exception:
            pass
        return

    command = message.text.split()[0].lower()
    if message.chat.type == "private":
        if command in COMMANDES_DM_AUTORISÉES or any(command.startswith(cmd) for cmd in COMMANDES_PASSE_PARTOUT):
            traiter_commande(message)
        elif command in COMMANDES_GROUPE_AUTORISÉES:
            send_admin_alert(f"🚫 Commande de groupe {command} utilisée en privé par {message.from_user.id}")
        else:
            bot.send_message(message.chat.id, "❌ Commande privée inconnue.")
            
    else:
        if command in COMMANDES_GROUPE_AUTORISÉES or any(command.startswith(cmd) for cmd in COMMANDES_PASSE_PARTOUT):
            traiter_commande(message)
        elif command in COMMANDES_DM_AUTORISÉES:
            send_admin_alert(f"🚫 Commande DM exclusive {command} bloquée dans le groupe")


# ========================================================
# CALLBACK QUERIES DE GESTION DU SALON (BOUTONS INTERACTIFS)
# ========================================================

@bot.callback_query_handler(func=lambda call: True)
def gerer_boutons(call):
    chat_id = call.message.chat.id
    user = call.from_user

    if chat_id not in games: 
        bot.answer_callback_query(call.id, "Aucune partie active.")
        return
        
    game = games[chat_id]

    if call.data == "join_game":
        try:
            statut = bot.get_chat_member(CANAL_CIBLE, user.id).status
            if statut not in ["member", "administrator", "creator"]:
                bot.answer_callback_query(call.id, "❌ Tu dois d'abord rejoindre notre communauté ! Fais /start en privé.", show_alert=True)
                return
            else:
                stats = charger_stats()
                if str(user.id) in stats:
                    stats[str(user.id)]["communaute_rejointe"] = True
                    sauvegarder_stats(stats)
        except Exception:
            bot.answer_callback_query(call.id, "❌ Erreur de vérification communauté.", show_alert=True)
            return

        if game.statut != "inscription": return
        if user.id in game.joueurs: return
        game.joueurs.append(user.id)
        game.noms_joueurs[user.id] = user.first_name
        game.points[user.id] = 3
        bot.edit_message_text(generer_texte_salon(game), chat_id, call.message.message_id, parse_mode="HTML", reply_markup=generer_clavier_salon(game))

    elif call.data == "join_motarena":
        if game.statut != "inscription": return
        if MOTARENA_ID in game.joueurs: return
        game.joueurs.append(MOTARENA_ID)
        game.noms_joueurs[MOTARENA_ID] = "motArena"
        game.points[MOTARENA_ID] = 3
        bot.edit_message_text(generer_texte_salon(game), chat_id, call.message.message_id, parse_mode="HTML", reply_markup=generer_clavier_salon(game))

    elif call.data == "play_game":
        if game.statut != "inscription": return
        if len(game.joueurs) < 2:
            bot.send_message(chat_id, "⚠️ Il faut au moins 2 joueurs.")
            return
        game.statut = "en_cours"
        bot.edit_message_text("🚀 <b>La partie commence !</b>", chat_id, call.message.message_id, parse_mode="HTML")
        passer_au_joueur_suivant(game)

    elif call.data == "kill_game":
        game.cancel_chrono()
        del games[chat_id]
        bot.edit_message_text("💥 <b>Salon annulé.</b>", chat_id, call.message.message_id, parse_mode="HTML")


# ========================================================
# PROPOSITIONS ET ENVOIS DE TEXTE (GAMEPLAY)
# ========================================================

def executer_verification_complete_async(game, message, user_id, proposition):
    resultat = verifier_anime_global(game.chat_id, proposition)
    
    if resultat["statut"] == "inconnu" or resultat["statut"] == "introuvable" or not resultat["titre"]:
        with game.lock:
            game.en_verification = False
            appliquer_sanction_sans_lock(game, raison="introuvable")
        return

    titre_officiel = resultat["titre"]

    if titre_officiel in game.animes_deja_cites:
        with game.lock:
            game.en_verification = False
            appliquer_sanction_sans_lock(game, raison="doublon")
        return

    game.animes_deja_cites.add(titre_officiel.lower())
    game.animes_deja_cites.add(proposition.lower())
    
    lettre_suivante = extraire_lettre_fin(titre_officiel)
    game.lettre_actuelle = lettre_suivante
    
    bot.reply_to(message, f"✅ <b>{titre_officiel.upper()}</b> validé !\n👉 Prochaine lettre : 🔥 <b>{lettre_suivante.upper()}</b> 🔥", parse_mode="HTML")

    with game.lock:
        game.index_tour = (game.index_tour + 1) % len(game.joueurs)
        game.en_verification = False
        passer_au_joueur_suivant(game)


@bot.message_handler(func=lambda m: True, content_types=['text'])
def gerer_proposition_jeu(message):
    chat_id = message.chat.id
    if chat_id not in games: return
    game = games[chat_id]
    if game.statut != "en_cours": return

    user_id = message.from_user.id
    if user_id not in game.joueurs or user_id in game.eliminated: return
    if user_id != game.joueurs[game.index_tour]: return
    if message.text.startswith('/'): return

    if time.time() >= game.limite_temps_tour:
        with game.lock:
            if not game.en_verification:
                bot.send_message(game.chat_id, "⏰ <b>0 seconde ! Le temps est écoulé !</b>", parse_mode="HTML")
                appliquer_sanction_sans_lock(game, raison="timeout")
        return
        
    with game.lock:
        if game.en_verification: return
        game.en_verification = True
        game.cancel_chrono()

    proposition = message.text.strip().lower()

    if game.lettre_actuelle and not proposition.startswith(game.lettre_actuelle):
        bot.reply_to(message, f"❌ Mauvaise lettre ! Tu devais commencer par <b>{game.lettre_actuelle.upper()}</b>.", parse_mode="HTML")
        with game.lock:
            game.en_verification = False
            temps_restant = game.limite_temps_tour - time.time()
            if temps_restant > 0:
                game.chrono_timer = threading.Timer(temps_restant, declencher_timeout_secret, args=(game, user_id))
                game.chrono_timer.start()
            else:
                bot.send_message(game.chat_id, "⏰ <b>0 seconde ! Le temps est écoulé !</b>", parse_mode="HTML")
                appliquer_sanction_sans_lock(game, raison="timeout")
        return

    if proposition in game.animes_deja_cites:
        with game.lock:
            game.en_verification = False
            appliquer_sanction_sans_lock(game, raison="doublon")
        return

    threading.Thread(target=executer_verification_complete_async, args=(game, message, user_id, proposition)).start()


# =============================================================================
# EXÉCUTION DU SCRIPT (AVEC LANCEMENT DU THREAD FLASK) 🚀
# =============================================================================
if __name__ == '__main__':
    print("[+] Initialisation du serveur Flask pour Render...")
    # On lance Flask sur un thread en arrière-plan sans bloquer la suite
    threading.Thread(target=run_flask, daemon=True).start()
    print("[+] Serveur Flask actif. Connexion au moteur centralisé Anime Chain...")
    
    # Nettoyage des mises à jour en attente chez Telegram pour éviter tout spam
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print(f"[-] Erreur delete_webhook: {e}")
    
    # Message de redémarrage unique envoyé au groupe CDO
    try:
        bot.send_message(GROUPE_AUTORISE_ID, "🚀 <b>Je suis de retour !</b> Ready pour une nouvelle chaîne ?", parse_mode="HTML")
    except Exception as e:
        print(f"[-] Erreur envoi message retour: {e}")

    bot.infinity_polling(allowed_updates=['message', 'callback_query', 'my_chat_member'])
