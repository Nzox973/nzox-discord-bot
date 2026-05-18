import datetime
import asyncio
from collections import defaultdict, deque
import time

import discord
from discord.ext import commands

import config
from utils.database import add_warning, get_warnings, clear_warnings


class Moderation(commands.Cog):
    """Modération automatique anti-spam + commandes manuelles."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Horodatages des messages par utilisateur pour la détection spam
        self._timestamps: dict[int, deque] = defaultdict(lambda: deque(maxlen=30))
        # Membres actuellement en timeout automatique (évite les doubles actions)
        self._en_timeout: set[int] = set()

    # ─── Détection ────────────────────────────────────────────────────────────

    def _est_spam_vitesse(self, user_id: int) -> bool:
        """Trop de messages dans la fenêtre de temps définie."""
        now = time.time()
        ts = self._timestamps[user_id]
        ts.append(now)
        recents = sum(1 for t in ts if now - t <= config.SPAM_FENETRE_SECONDES)
        return recents >= config.SPAM_MAX_MESSAGES

    @staticmethod
    def _est_spam_repetition(content: str) -> bool:
        """Message composé à >70 % du même caractère (zalgo, spam 'aaaa…')."""
        if len(content) < 8:
            return False
        max_rep = max(content.count(c) for c in set(content))
        return max_rep / len(content) > 0.7

    @staticmethod
    def _est_lien_invite(content: str) -> bool:
        """Invitation Discord non sollicitée."""
        return any(s in content.lower() for s in ["discord.gg/", "discordapp.com/invite/"])

    # ─── Listener principal ───────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
        # Les modérateurs sont exemptés
        if message.author.guild_permissions.manage_messages:
            return

        user_id = message.author.id

        # Supprimer les messages des membres déjà en timeout auto
        if user_id in self._en_timeout:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            return

        raisons: list[str] = []
        if self._est_spam_vitesse(user_id):
            raisons.append("messages trop rapides")
        if self._est_spam_repetition(message.content):
            raisons.append("caractères répétés")
        if self._est_lien_invite(message.content):
            raisons.append("invitation Discord non autorisée")

        if raisons:
            await self._traiter_spam(message, raisons)

    async def _traiter_spam(self, message: discord.Message, raisons: list[str]) -> None:
        """Supprime le message, avertit le membre et applique la sanction."""
        member = message.author
        guild = message.guild
        raison_str = ", ".join(raisons)

        try:
            await message.delete()
        except discord.Forbidden:
            pass

        await add_warning(guild.id, member.id, f"Anti-spam : {raison_str}", self.bot.user.id)
        warnings = await get_warnings(guild.id, member.id)
        nb = len(warnings)

        try:
            await message.channel.send(
                f"⚠️ {member.mention} — Spam détecté ({raison_str}). "
                f"Avertissement **{nb}/3**.",
                delete_after=10,
            )
        except discord.Forbidden:
            pass

        if nb >= 3:
            await self._appliquer_timeout(member, guild, config.SPAM_MUTE_DUREE, raison_str)

        await self._log(guild, member, "Spam détecté (auto)", raison_str, nb)

    async def _appliquer_timeout(
        self,
        member: discord.Member,
        guild: discord.Guild,
        durée: int,
        raison: str,
    ) -> None:
        """Applique un timeout natif Discord."""
        try:
            until = discord.utils.utcnow() + datetime.timedelta(seconds=durée)
            await member.timeout(until, reason=f"Anti-spam : {raison}")
            self._en_timeout.add(member.id)
            try:
                await member.send(
                    f"🔇 Tu as été muté sur **{guild.name}** pendant "
                    f"{durée // 60} minutes pour : {raison}."
                )
            except discord.Forbidden:
                pass
            await asyncio.sleep(durée)
            self._en_timeout.discard(member.id)
        except discord.Forbidden:
            pass

    async def _log(
        self,
        guild: discord.Guild,
        member: discord.Member,
        action: str,
        raison: str,
        nb_warnings: int,
    ) -> None:
        """Envoie un log dans le salon dédié."""
        if not config.LOG_CHANNEL_ID:
            return
        channel = guild.get_channel(config.LOG_CHANNEL_ID)
        if not channel:
            return
        embed = discord.Embed(
            title=f"🛡️ {action}",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Membre", value=f"{member.mention} (`{member.id}`)", inline=True)
        embed.add_field(name="Raison", value=raison, inline=True)
        embed.add_field(name="Avertissements", value=str(nb_warnings), inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

    # ─── Commandes manuelles ──────────────────────────────────────────────────

    @commands.command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn(
        self, ctx: commands.Context, member: discord.Member, *, raison: str = "Aucune raison"
    ) -> None:
        """[Modo] Avertit un membre."""
        await add_warning(ctx.guild.id, member.id, raison, ctx.author.id)
        warnings = await get_warnings(ctx.guild.id, member.id)

        embed = discord.Embed(title="Avertissement", color=discord.Color.orange())
        embed.add_field(name="Membre", value=member.mention, inline=True)
        embed.add_field(name="Total", value=str(len(warnings)), inline=True)
        embed.add_field(name="Raison", value=raison, inline=False)
        embed.set_footer(text=f"Par {ctx.author.display_name}")
        await ctx.send(embed=embed)

        try:
            await member.send(
                f"⚠️ Tu as reçu un avertissement sur **{ctx.guild.name}**.\nRaison : {raison}"
            )
        except discord.Forbidden:
            pass

    @commands.command(name="warnings", aliases=["infractions"])
    @commands.has_permissions(manage_messages=True)
    async def warnings_list(self, ctx: commands.Context, member: discord.Member) -> None:
        """[Modo] Liste les avertissements actifs d'un membre."""
        rows = await get_warnings(ctx.guild.id, member.id)
        if not rows:
            return await ctx.send(f"✅ {member.mention} n'a aucun avertissement actif.")

        embed = discord.Embed(
            title=f"Avertissements — {member.display_name}",
            color=discord.Color.orange(),
        )
        for warn_id, raison, mod_id, ts in rows[:10]:
            dt = datetime.datetime.fromtimestamp(ts)
            mod = ctx.guild.get_member(mod_id)
            mod_nom = mod.display_name if mod else f"ID:{mod_id}"
            embed.add_field(
                name=f"#{warn_id} — {dt.strftime('%d/%m/%Y %H:%M')}",
                value=f"**Raison :** {raison}\n**Modérateur :** {mod_nom}",
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(name="clearwarns")
    @commands.has_permissions(administrator=True)
    async def clear_warns(self, ctx: commands.Context, member: discord.Member) -> None:
        """[Admin] Supprime tous les avertissements d'un membre."""
        await clear_warnings(ctx.guild.id, member.id)
        await ctx.send(f"✅ Avertissements effacés pour {member.mention}.")

    @commands.command(name="mute", aliases=["timeout"])
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(
        self,
        ctx: commands.Context,
        member: discord.Member,
        durée: int = 10,
        *,
        raison: str = "Aucune raison",
    ) -> None:
        """[Modo] Mute un membre (durée en minutes, défaut 10)."""
        until = discord.utils.utcnow() + datetime.timedelta(minutes=durée)
        await member.timeout(until, reason=raison)

        embed = discord.Embed(title="Membre muté", color=discord.Color.orange())
        embed.add_field(name="Membre", value=member.mention, inline=True)
        embed.add_field(name="Durée", value=f"{durée} min", inline=True)
        embed.add_field(name="Raison", value=raison, inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member) -> None:
        """[Modo] Retire le mute d'un membre."""
        await member.timeout(None)
        self._en_timeout.discard(member.id)
        await ctx.send(f"✅ {member.mention} n'est plus muté.")

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(
        self, ctx: commands.Context, member: discord.Member, *, raison: str = "Aucune raison"
    ) -> None:
        """[Modo] Expulse un membre."""
        try:
            await member.send(f"👢 Tu as été expulsé de **{ctx.guild.name}**.\nRaison : {raison}")
        except discord.Forbidden:
            pass
        await member.kick(reason=raison)
        embed = discord.Embed(title="Membre expulsé", color=discord.Color.red())
        embed.add_field(name="Membre", value=str(member), inline=True)
        embed.add_field(name="Raison", value=raison, inline=False)
        embed.set_footer(text=f"Par {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(
        self, ctx: commands.Context, member: discord.Member, *, raison: str = "Aucune raison"
    ) -> None:
        """[Modo] Bannit un membre."""
        try:
            await member.send(f"🔨 Tu as été banni de **{ctx.guild.name}**.\nRaison : {raison}")
        except discord.Forbidden:
            pass
        await member.ban(reason=raison, delete_message_days=1)
        embed = discord.Embed(title="Membre banni", color=discord.Color.dark_red())
        embed.add_field(name="Membre", value=str(member), inline=True)
        embed.add_field(name="Raison", value=raison, inline=False)
        embed.set_footer(text=f"Par {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int) -> None:
        """[Modo] Débannit un utilisateur par son ID."""
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"✅ **{user}** a été débanni.")

    @commands.command(name="purge", aliases=["clear"])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, nombre: int = 10) -> None:
        """[Modo] Supprime N messages dans le salon (max 100)."""
        if not 1 <= nombre <= 100:
            return await ctx.send("❌ Nombre entre 1 et 100.")
        supprimés = await ctx.channel.purge(limit=nombre + 1)
        await ctx.send(f"✅ {len(supprimés) - 1} messages supprimés.", delete_after=5)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
