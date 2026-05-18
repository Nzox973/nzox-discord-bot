# NzoxYt Discord Bot

Bot Discord complet pour le serveur **NzoxYt** avec IA, annonces automatiques, système de niveaux, rôles par réaction et modération anti-spam.

---

## Fonctionnalités

| Module | Description |
|---|---|
| 🤖 **IA Anthropic** | Répond via Claude dans un salon dédié ou sur mention |
| 👋 **Accueil** | Message de bienvenue/départ personnalisé |
| 📺 **Annonces** | Notification automatique nouvelles vidéos YouTube et live Twitch |
| ⭐ **Niveaux XP** | Gain d'XP par message, cooldown anti-farm, classement |
| 🎭 **Rôles réaction** | Attribution/retrait de rôles par emoji |
| 🛡️ **Modération** | Anti-spam automatique + commandes manuelles (warn/mute/kick/ban) |

---

## Installation

### Prérequis

- Python 3.11+
- Un compte Discord Developer
- (Optionnel) Clés API YouTube, Twitch, Anthropic

### 1. Cloner / télécharger le projet

```bash
git clone <url-du-repo>
cd discord_bot
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Ouvre `.env` et remplis les valeurs (voir section Configuration ci-dessous).

### 5. Lancer le bot

```bash
python main.py
```

---

## Configuration détaillée

### Token Discord (obligatoire)

1. Va sur [discord.com/developers/applications](https://discord.com/developers/applications)
2. Clique **New Application** → donne un nom
3. Onglet **Bot** → **Add Bot**
4. Clique **Reset Token** puis copie le token → `DISCORD_TOKEN`
5. Active les **Privileged Gateway Intents** :
   - ✅ Server Members Intent
   - ✅ Message Content Intent
6. Onglet **OAuth2 > URL Generator** :
   - Scopes : `bot`, `applications.commands`
   - Permissions : `Administrator` (ou permissions précises)
   - Copie l'URL générée et invite le bot sur ton serveur

### ID du serveur

- Discord en mode développeur (Paramètres > Avancé > Mode développeur)
- Clic droit sur le nom du serveur → **Copier l'identifiant** → `GUILD_ID`

### IDs des salons

- Clic droit sur un salon → **Copier l'identifiant**
- Remplis chaque `*_CHANNEL_ID` dans `.env`

### Clé API Anthropic (module IA)

1. Va sur [console.anthropic.com](https://console.anthropic.com)
2. **API Keys** → **Create Key**
3. Copie la clé → `ANTHROPIC_API_KEY`

Le bot utilise le prompt caching pour réduire les coûts sur chaque échange.

### YouTube Data API v3 (annonces)

1. Va sur [console.cloud.google.com](https://console.cloud.google.com)
2. Crée un projet → **API et services** → **Bibliothèque**
3. Cherche **YouTube Data API v3** → Activer
4. **Identifiants** → **Créer des identifiants** → **Clé API** → `YOUTUBE_API_KEY`
5. ID de ta chaîne YouTube :
   - Va sur ta chaîne → URL → copie la partie après `/channel/` → `YOUTUBE_CHANNEL_ID`
   - (ou utilise [commentpicker.com/youtube-channel-id.php](https://commentpicker.com/youtube-channel-id.php))

### Twitch API (annonces live)

1. Va sur [dev.twitch.tv/console](https://dev.twitch.tv/console)
2. **Register Your Application**
   - Category : Chat Bot
   - OAuth Redirect URL : `http://localhost`
3. Copie **Client ID** → `TWITCH_CLIENT_ID`
4. **New Secret** → copie → `TWITCH_CLIENT_SECRET`
5. `TWITCH_CHANNEL_NAME` = le nom de ta chaîne Twitch (sans @)

---

## Commandes

### Générales
| Commande | Description |
|---|---|
| `!help` | Affiche cette aide |
| `!ping` | Latence du bot |
| `!info` | Informations du serveur |

### IA
| Commande | Description |
|---|---|
| `@bot <message>` | Parler à l'IA (n'importe quel salon) |
| *Écrire dans #ia* | Parler à l'IA (salon dédié) |
| `!clearai` | [Modo] Efface l'historique IA du salon |

### Niveaux XP
| Commande | Description |
|---|---|
| `!rank [@membre]` | Affiche le niveau et XP |
| `!leaderboard` | Top 10 XP du serveur |
| `!addxp <@membre> <montant>` | [Admin] Ajouter XP |
| `!resetxp <@membre>` | [Admin] Remettre XP à zéro |

### Rôles par réaction
| Commande | Description |
|---|---|
| `!rr_create` | [Admin] Crée un message de sélection de rôles |
| `!rr_add <msg_id> <emoji> <@rôle>` | [Admin] Associe un emoji à un rôle |
| `!rr_remove <msg_id> <emoji>` | [Admin] Supprime une association |
| `!rr_list` | [Admin] Liste toutes les associations |

### Médias
| Commande | Description |
|---|---|
| `!youtube` | Stats de la chaîne YouTube |
| `!twitch` | Statut du live Twitch |

### Modération
| Commande | Description |
|---|---|
| `!warn <@membre> [raison]` | Avertir un membre |
| `!warnings <@membre>` | Voir les avertissements |
| `!clearwarns <@membre>` | [Admin] Effacer les avertissements |
| `!mute <@membre> [minutes] [raison]` | Muter (timeout natif Discord) |
| `!unmute <@membre>` | Démuter |
| `!kick <@membre> [raison]` | Expulser |
| `!ban <@membre> [raison]` | Bannir |
| `!unban <id>` | Débannir par ID utilisateur |
| `!purge [nombre]` | Supprimer N messages (max 100) |

---

## Système XP

- Chaque message rapporte entre 8 et 15 XP (aléatoire)
- Cooldown de 60 secondes par membre pour éviter le farm
- Formule de niveau : `XP requis = 100 × niveau² + 50 × niveau`
- Montée de niveau annoncée dans `LEVEL_UP_CHANNEL_ID`

## Anti-spam automatique

Le bot détecte trois types de spam :
1. **Vitesse** : 5+ messages en moins de 5 secondes
2. **Répétition** : message composé à >70% du même caractère
3. **Invitations** : lien `discord.gg/` non autorisé

**Sanctions progressives** :
- Avertissement 1 & 2 : suppression du message + notification
- Avertissement 3 : timeout automatique de 5 minutes

---

## Structure du projet

```
discord_bot/
├── main.py                  # Point d'entrée, commandes globales
├── config.py                # Chargement des variables d'environnement
├── requirements.txt
├── .env.example             # Modèle de configuration
├── cogs/
│   ├── welcome.py           # Accueil des membres
│   ├── ai_responses.py      # IA via Anthropic Claude
│   ├── announcements.py     # YouTube & Twitch
│   ├── levels.py            # Système XP/niveaux
│   ├── reaction_roles.py    # Rôles par réaction
│   └── moderation.py        # Anti-spam + commandes modo
├── utils/
│   └── database.py          # Couche SQLite (aiosqlite)
└── data/
    └── bot.db               # Base de données (créée automatiquement)
```

---

## Dépannage

**`DISCORD_TOKEN manquant`** → Vérifie que le fichier `.env` existe et contient `DISCORD_TOKEN=...`

**Le bot ne répond pas à `!help`** → Vérifie que l'intent **Message Content** est activé dans le portail développeur.

**Les annonces YouTube/Twitch ne fonctionnent pas** → Au **premier lancement**, le bot mémorise la dernière publication sans l'annoncer (évite le spam au démarrage). Les annonces commenceront à la prochaine nouvelle publication.

**`discord.errors.Forbidden` dans les logs** → Le bot manque de permissions. Vérifie son rôle dans les paramètres du serveur.
