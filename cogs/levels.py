import discord
from discord.ext import commands
import random
import time
import config
from utils.database import get_user_xp, update_user_xp, get_leaderboard


def xp_pour_niveau(niveau: int) -> int:
    """XP cumulé requis pour atteindre ce niveau."""
    return 100 * (niveau ** 2) + 50 * niveau


def niveau_depuis_xp(xp: int) -> int:
    """Calcule le niveau correspondant à un total d'XP."""
    niveau = 0
    while xp_pour_niveau(niveau + 1) <= xp:
        niveau += 1
    return niveau


class Levels(commands.Cog):
    """Système de niveaux et d'XP basé sur l'activité des membres."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Attribue de l'XP pour chaque message (avec cooldown anti-farm)."""
        if message.author.bot or not message.guild:
            return
        if message.content.startswith(config.COMMAND_PREFIX):
            return

        guild_id = message.guild.id
        user_id = message.author.id
        now = time.time()

        data = await get_user_xp(guild_id, user_id)

        # Respecter le cooldown
        if now - data["last_xp_time"] < config.XP_COOLDOWN_SECONDES:
            return

        xp_gagné = random.randint(config.XP_MIN_PAR_MESSAGE, config.XP_MAX_PAR_MESSAGE)
        nouvel_xp = data["xp"] + xp_gagné
        nouveau_niveau = niveau_depuis_xp(nouvel_xp)
        ancien_niveau = data["level"]

        await update_user_xp(
            guild_id, user_id, nouvel_xp, nouveau_niveau,
            now, data["messages_count"] + 1,
        )

        if nouveau_niveau > ancien_niveau:
            await self._annoncer_niveau(message, nouveau_niveau)

    async def _annoncer_niveau(self, message: discord.Message, nouveau_niveau: int) -> None:
        """Envoie le message de montée de niveau dans le salon dédié."""
        channel = (
            message.guild.get_channel(config.LEVEL_UP_CHANNEL_ID)
            if config.LEVEL_UP_CHANNEL_ID
            else message.channel
        )
        if not channel:
            channel = message.channel

        embed = discord.Embed(
            title="Niveau supérieur !",
            description=(
                f"Félicitations {message.author.mention} ! "
                f"Tu as atteint le **niveau {nouveau_niveau}** !"
            ),
            color=discord.Color.gold(),
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.add_field(
            name="Prochain niveau",
            value=f"{xp_pour_niveau(nouveau_niveau + 1):,} XP requis",
            inline=False,
        )
        await channel.send(embed=embed)

    # ─── Commandes ────────────────────────────────────────────────────────────

    @commands.command(name="rank", aliases=["niveau", "level", "xp"])
    async def rank(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """Affiche le niveau et l'XP d'un membre (ou toi-même)."""
        member = member or ctx.author
        data = await get_user_xp(ctx.guild.id, member.id)

        xp = data["xp"]
        niveau = data["level"]
        xp_actuel = xp_pour_niveau(niveau)
        xp_prochain = xp_pour_niveau(niveau + 1)
        progression = xp - xp_actuel
        requis = xp_prochain - xp_actuel

        # Barre de progression ASCII
        longueur = 20
        rempli = int(longueur * progression / requis) if requis > 0 else longueur
        barre = "█" * rempli + "░" * (longueur - rempli)

        embed = discord.Embed(
            title=f"Rang de {member.display_name}",
            color=member.color if member.color != discord.Color.default() else discord.Color.blue(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Niveau", value=str(niveau), inline=True)
        embed.add_field(name="XP Total", value=f"{xp:,}", inline=True)
        embed.add_field(name="Messages", value=f"{data['messages_count']:,}", inline=True)
        embed.add_field(
            name=f"Vers le niveau {niveau + 1}",
            value=f"`{barre}` {progression:,} / {requis:,} XP",
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard", aliases=["top", "classement", "lb"])
    async def leaderboard(self, ctx: commands.Context) -> None:
        """Affiche le top 10 XP du serveur."""
        rows = await get_leaderboard(ctx.guild.id, limit=10)
        if not rows:
            return await ctx.send("Aucun classement disponible pour l'instant.")

        médailles = ["🥇", "🥈", "🥉"]
        lignes = []
        for i, (user_id, xp, niveau) in enumerate(rows):
            member = ctx.guild.get_member(user_id)
            nom = member.display_name if member else f"Membre {user_id}"
            icone = médailles[i] if i < 3 else f"`#{i + 1}`"
            lignes.append(f"{icone} **{nom}** — Niv. {niveau} ({xp:,} XP)")

        embed = discord.Embed(
            title=f"Classement XP — {ctx.guild.name}",
            description="\n".join(lignes),
            color=discord.Color.gold(),
        )
        await ctx.send(embed=embed)

    @commands.command(name="addxp")
    @commands.has_permissions(administrator=True)
    async def add_xp(self, ctx: commands.Context, member: discord.Member, montant: int) -> None:
        """[Admin] Ajoute de l'XP à un membre."""
        data = await get_user_xp(ctx.guild.id, member.id)
        nouvel_xp = data["xp"] + montant
        nouveau_niveau = niveau_depuis_xp(nouvel_xp)
        await update_user_xp(
            ctx.guild.id, member.id, nouvel_xp, nouveau_niveau,
            data["last_xp_time"], data["messages_count"],
        )
        await ctx.send(
            f"✅ **+{montant} XP** attribués à {member.mention}. "
            f"(Total : {nouvel_xp:,} XP — Niveau {nouveau_niveau})"
        )

    @commands.command(name="resetxp")
    @commands.has_permissions(administrator=True)
    async def reset_xp(self, ctx: commands.Context, member: discord.Member) -> None:
        """[Admin] Remet à zéro l'XP d'un membre."""
        await update_user_xp(ctx.guild.id, member.id, 0, 0, 0.0, 0)
        await ctx.send(f"✅ XP réinitialisé pour {member.mention}.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Levels(bot))
