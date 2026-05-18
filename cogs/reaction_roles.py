import discord
from discord.ext import commands
from utils.database import add_reaction_role, get_reaction_role, get_all_reaction_roles, remove_reaction_role


class ReactionRoles(commands.Cog):
    """Attribution de rôles par réaction sur un message dédié."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ─── Listeners ────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Attribue le rôle associé à l'emoji cliqué."""
        if payload.user_id == self.bot.user.id:
            return

        rr = await get_reaction_role(payload.message_id, str(payload.emoji))
        if not rr:
            return

        guild = self.bot.get_guild(rr["guild_id"])
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        role = guild.get_role(rr["role_id"])

        if member and role:
            try:
                await member.add_roles(role, reason="Reaction role")
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        """Retire le rôle quand l'utilisateur enlève sa réaction."""
        if payload.user_id == self.bot.user.id:
            return

        rr = await get_reaction_role(payload.message_id, str(payload.emoji))
        if not rr:
            return

        guild = self.bot.get_guild(rr["guild_id"])
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        role = guild.get_role(rr["role_id"])

        if member and role:
            try:
                await member.remove_roles(role, reason="Reaction role retiré")
            except discord.Forbidden:
                pass

    # ─── Commandes ────────────────────────────────────────────────────────────

    @commands.command(name="rr_create")
    @commands.has_permissions(administrator=True)
    async def rr_create(self, ctx: commands.Context) -> None:
        """[Admin] Crée un message de sélection de rôles par réaction."""
        embed = discord.Embed(
            title="Sélection de rôles",
            description=(
                "Réagis à ce message pour obtenir tes rôles !\n\n"
                "*Les rôles disponibles seront listés ici après configuration.*"
            ),
            color=discord.Color.blurple(),
        )
        msg = await ctx.send(embed=embed)
        await ctx.send(
            f"✅ Message créé (ID : `{msg.id}`).\n"
            f"Utilise `!rr_add {msg.id} <emoji> <@rôle>` pour lier des rôles.",
            delete_after=30,
        )

    @commands.command(name="rr_add")
    @commands.has_permissions(administrator=True)
    async def rr_add(
        self,
        ctx: commands.Context,
        message_id: int,
        emoji: str,
        role: discord.Role,
    ) -> None:
        """[Admin] Associe un emoji à un rôle sur un message existant."""
        try:
            msg = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.send("❌ Message introuvable dans ce salon.")

        await add_reaction_role(ctx.guild.id, ctx.channel.id, message_id, emoji, role.id)

        try:
            await msg.add_reaction(emoji)
        except discord.HTTPException:
            return await ctx.send(f"❌ Emoji invalide : `{emoji}`")

        # Mettre à jour l'embed du message avec la nouvelle entrée
        rows = await get_all_reaction_roles(ctx.guild.id)
        lignes = []
        for ch_id, msg_id, e, role_id in rows:
            if msg_id == message_id:
                r = ctx.guild.get_role(role_id)
                if r:
                    lignes.append(f"{e} → **{r.name}**")

        if msg.embeds:
            embed = msg.embeds[0]
            embed.description = (
                "Réagis à ce message pour obtenir tes rôles !\n\n"
                + "\n".join(lignes)
            )
            await msg.edit(embed=embed)

        await ctx.send(f"✅ {emoji} → **{role.name}** ajouté.", delete_after=15)

    @commands.command(name="rr_remove")
    @commands.has_permissions(administrator=True)
    async def rr_remove(
        self, ctx: commands.Context, message_id: int, emoji: str
    ) -> None:
        """[Admin] Supprime une association emoji-rôle."""
        await remove_reaction_role(message_id, emoji)
        await ctx.send(f"✅ Association `{emoji}` supprimée du message `{message_id}`.")

    @commands.command(name="rr_list")
    @commands.has_permissions(administrator=True)
    async def rr_list(self, ctx: commands.Context) -> None:
        """[Admin] Liste toutes les associations rôle-réaction du serveur."""
        rows = await get_all_reaction_roles(ctx.guild.id)
        if not rows:
            return await ctx.send("Aucun rôle-réaction configuré.")

        embed = discord.Embed(title="Rôles par réaction", color=discord.Color.blurple())
        for channel_id, message_id, emoji, role_id in rows:
            ch = ctx.guild.get_channel(channel_id)
            role = ctx.guild.get_role(role_id)
            embed.add_field(
                name=f"{emoji} → {role.name if role else 'Rôle supprimé'}",
                value=f"Salon : {ch.mention if ch else '?'}\nMessage : `{message_id}`",
                inline=True,
            )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReactionRoles(bot))
