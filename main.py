import asyncio
import discord
from discord.ext import commands
import config
from utils.database import init_db

# Intents nécessaires au fonctionnement complet du bot
intents = discord.Intents.default()
intents.members = True          # accueil, départ, modération
intents.message_content = True  # lecture des messages pour IA, XP, anti-spam
intents.reactions = True        # rôles par réaction

bot = commands.Bot(
    command_prefix=config.COMMAND_PREFIX,
    intents=intents,
    help_command=None,  # commande !help personnalisée ci-dessous
)

COGS = [
    "cogs.welcome",
    "cogs.ai_responses",
    "cogs.announcements",
    "cogs.levels",
    "cogs.reaction_roles",
    "cogs.moderation",
]


# ─── Événements globaux ───────────────────────────────────────────────────────

@bot.event
async def on_ready() -> None:
    print(f"✅  {bot.user} connecté")
    print(f"    ID      : {bot.user.id}")
    print(f"    Serveurs: {len(bot.guilds)}")

    try:
        synced = await bot.tree.sync()
        print(f"    Slash   : {len(synced)} commandes synchronisées")
    except Exception as e:
        print(f"    Slash sync erreur : {e}")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{config.COMMAND_PREFIX}help | NzoxYt",
        )
    )


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    """Gestion centralisée des erreurs de commande."""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu n'as pas les permissions nécessaires.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ Le bot manque de permissions pour exécuter cette action.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Membre introuvable.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Argument manquant : `{error.param.name}`. Utilise `!help` pour l'aide.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Argument invalide. Utilise `!help` pour l'aide.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # ignorer les commandes inconnues silencieusement
    else:
        print(f"[Erreur non gérée] {type(error).__name__}: {error}")


# ─── Commandes intégrées ──────────────────────────────────────────────────────

@bot.command(name="help", aliases=["aide"])
async def help_command(ctx: commands.Context) -> None:
    """Affiche toutes les commandes disponibles."""
    p = config.COMMAND_PREFIX
    embed = discord.Embed(
        title="Aide — NzoxYt Bot",
        description=f"Préfixe : `{p}` | Mentionne le bot pour parler à l'IA",
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="🤖 Intelligence Artificielle",
        value=(
            f"`{p}clearai` — Efface l'historique IA du salon\n"
            "*Écris dans le salon IA ou mentionne le bot*"
        ),
        inline=False,
    )
    embed.add_field(
        name="⭐ Niveaux & XP",
        value=(
            f"`{p}rank [@membre]` — Affiche ton niveau et XP\n"
            f"`{p}leaderboard` — Top 10 XP du serveur\n"
            f"`{p}addxp <@membre> <montant>` — [Admin] Ajoute XP\n"
            f"`{p}resetxp <@membre>` — [Admin] Remet XP à zéro"
        ),
        inline=False,
    )
    embed.add_field(
        name="🎭 Rôles par réaction",
        value=(
            f"`{p}rr_create` — [Admin] Crée un message de rôles\n"
            f"`{p}rr_add <msg_id> <emoji> <@rôle>` — [Admin] Lie un rôle\n"
            f"`{p}rr_remove <msg_id> <emoji>` — [Admin] Retire un lien\n"
            f"`{p}rr_list` — [Admin] Liste les rôles-réactions"
        ),
        inline=False,
    )
    embed.add_field(
        name="🛡️ Modération",
        value=(
            f"`{p}warn <@membre> [raison]` — Avertir un membre\n"
            f"`{p}warnings <@membre>` — Voir les avertissements\n"
            f"`{p}clearwarns <@membre>` — [Admin] Effacer les avertissements\n"
            f"`{p}mute <@membre> [minutes] [raison]` — Muter\n"
            f"`{p}unmute <@membre>` — Démuter\n"
            f"`{p}kick <@membre> [raison]` — Expulser\n"
            f"`{p}ban <@membre> [raison]` — Bannir\n"
            f"`{p}unban <id>` — Débannir par ID\n"
            f"`{p}purge [nombre]` — Supprimer des messages (max 100)"
        ),
        inline=False,
    )
    embed.add_field(
        name="📺 Médias & Info",
        value=(
            f"`{p}youtube` — Stats de la chaîne YouTube\n"
            f"`{p}twitch` — Statut du live Twitch\n"
            f"`{p}ping` — Latence du bot\n"
            f"`{p}info` — Infos du serveur"
        ),
        inline=False,
    )
    embed.set_footer(text="NzoxYt Bot • Les commandes [Admin] nécessitent le rang Administrateur")
    await ctx.send(embed=embed)


@bot.command(name="ping")
async def ping(ctx: commands.Context) -> None:
    """Affiche la latence du bot."""
    await ctx.send(f"🏓 Pong ! **{round(bot.latency * 1000)} ms**")


@bot.command(name="info")
async def server_info(ctx: commands.Context) -> None:
    """Affiche les informations générales du serveur."""
    g = ctx.guild
    embed = discord.Embed(
        title=g.name,
        description=g.description or "Serveur NzoxYt",
        color=discord.Color.blurple(),
    )
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="Membres", value=str(g.member_count), inline=True)
    embed.add_field(name="Salons", value=str(len(g.channels)), inline=True)
    embed.add_field(name="Rôles", value=str(len(g.roles)), inline=True)
    embed.add_field(name="Créé le", value=g.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(
        name="Propriétaire",
        value=g.owner.mention if g.owner else "Inconnu",
        inline=True,
    )
    await ctx.send(embed=embed)


# ─── Démarrage ────────────────────────────────────────────────────────────────

async def main() -> None:
    await init_db()
    print("✅  Base de données initialisée")

    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f"✅  Cog chargé : {cog}")
            except Exception as e:
                print(f"❌  Erreur chargement {cog} : {e}")

        if not config.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN manquant dans .env")

        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
