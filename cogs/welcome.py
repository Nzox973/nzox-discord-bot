import discord
from discord.ext import commands
import config


class Welcome(commands.Cog):
    """Accueil automatique des nouveaux membres."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Message de bienvenue personnalisé à l'arrivée d'un membre."""
        channel = member.guild.get_channel(config.WELCOME_CHANNEL_ID)
        if not channel:
            return

        embed = discord.Embed(
            title="Bienvenue sur NzoxYt !",
            description=(
                f"Hey {member.mention} ! Bienvenue sur le serveur **NzoxYt** !\n\n"
                f"Tu es le **{member.guild.member_count}ème** membre à nous rejoindre.\n\n"
                "📋 Lis les règles du serveur\n"
                "🎭 Choisis tes rôles dans le salon dédié\n"
                "💬 N'hésite pas à te présenter !"
            ),
            color=discord.Color.green(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"NzoxYt Bot • {member.guild.name}")

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Annonce le départ d'un membre."""
        channel = member.guild.get_channel(config.WELCOME_CHANNEL_ID)
        if not channel:
            return

        embed = discord.Embed(
            title="Un membre est parti",
            description=(
                f"**{member.name}** a quitté le serveur. 👋\n"
                f"Il reste maintenant **{member.guild.member_count}** membres."
            ),
            color=discord.Color.red(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))
