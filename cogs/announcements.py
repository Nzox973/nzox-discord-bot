import discord
from discord.ext import commands, tasks
import aiohttp
import config
from utils.database import get_last_announcement, update_last_announcement


class Announcements(commands.Cog):
    """Annonces automatiques YouTube (nouvelles vidéos) et Twitch (live)."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._twitch_token: str | None = None
        self.check_feeds.start()

    def cog_unload(self) -> None:
        self.check_feeds.cancel()

    # ─── Boucle principale ────────────────────────────────────────────────────

    @tasks.loop(minutes=5)
    async def check_feeds(self) -> None:
        """Vérifie toutes les 5 minutes les nouvelles publications."""
        for guild in self.bot.guilds:
            channel = guild.get_channel(config.ANNOUNCEMENT_CHANNEL_ID)
            if not channel:
                continue
            if config.YOUTUBE_API_KEY and config.YOUTUBE_CHANNEL_ID:
                await self._check_youtube(guild, channel)
            if config.TWITCH_CLIENT_ID and config.TWITCH_CHANNEL_NAME:
                await self._check_twitch(guild, channel)

    @check_feeds.before_loop
    async def _before_check(self) -> None:
        await self.bot.wait_until_ready()

    # ─── YouTube ──────────────────────────────────────────────────────────────

    async def _check_youtube(self, guild: discord.Guild, channel: discord.TextChannel) -> None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "channelId": config.YOUTUBE_CHANNEL_ID,
                        "maxResults": 1,
                        "order": "date",
                        "type": "video",
                        "key": config.YOUTUBE_API_KEY,
                    },
                ) as resp:
                    if resp.status != 200:
                        return
                    data = await resp.json()

            items = data.get("items", [])
            if not items:
                return

            latest = items[0]
            video_id = latest["id"]["videoId"]
            last_id = await get_last_announcement(guild.id, "youtube")

            if video_id == last_id:
                return

            await update_last_announcement(guild.id, "youtube", video_id)

            # Au premier lancement on mémorise sans annoncer
            if last_id is None:
                return

            snippet = latest["snippet"]
            embed = discord.Embed(
                title="Nouvelle vidéo YouTube !",
                description=f"**{snippet['title']}**\n\n{snippet['description'][:200]}…",
                url=f"https://www.youtube.com/watch?v={video_id}",
                color=discord.Color.red(),
            )
            embed.set_image(url=snippet["thumbnails"]["high"]["url"])
            embed.set_footer(text=snippet["channelTitle"])

            await channel.send("@everyone 🎬 Nouvelle vidéo disponible !", embed=embed)

        except Exception as e:
            print(f"[YouTube] Erreur : {e}")

    # ─── Twitch ───────────────────────────────────────────────────────────────

    async def _get_twitch_token(self) -> str | None:
        if self._twitch_token:
            return self._twitch_token
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://id.twitch.tv/oauth2/token",
                    params={
                        "client_id": config.TWITCH_CLIENT_ID,
                        "client_secret": config.TWITCH_CLIENT_SECRET,
                        "grant_type": "client_credentials",
                    },
                ) as resp:
                    if resp.status == 200:
                        self._twitch_token = (await resp.json()).get("access_token")
                        return self._twitch_token
        except Exception as e:
            print(f"[Twitch] Erreur token : {e}")
        return None

    async def _check_twitch(self, guild: discord.Guild, channel: discord.TextChannel) -> None:
        try:
            token = await self._get_twitch_token()
            if not token:
                return

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.twitch.tv/helix/streams",
                    params={"user_login": config.TWITCH_CHANNEL_NAME},
                    headers={
                        "Client-ID": config.TWITCH_CLIENT_ID,
                        "Authorization": f"Bearer {token}",
                    },
                ) as resp:
                    if resp.status == 401:
                        self._twitch_token = None  # token expiré
                        return
                    if resp.status != 200:
                        return
                    data = await resp.json()

            streams = data.get("data", [])
            last_stream_id = await get_last_announcement(guild.id, "twitch")

            if not streams:
                # Le stream s'est terminé : réinitialiser pour la prochaine session
                if last_stream_id and last_stream_id != "offline":
                    await update_last_announcement(guild.id, "twitch", "offline")
                return

            stream = streams[0]
            stream_id = stream["id"]

            if stream_id == last_stream_id:
                return  # déjà annoncé

            await update_last_announcement(guild.id, "twitch", stream_id)

            if last_stream_id is None:  # premier lancement
                return

            thumbnail = (
                stream["thumbnail_url"]
                .replace("{width}", "1280")
                .replace("{height}", "720")
            )
            embed = discord.Embed(
                title=f"{config.TWITCH_CHANNEL_NAME} est en LIVE !",
                description=f"**{stream['title']}**\n\n🎮 {stream['game_name']}",
                url=f"https://twitch.tv/{config.TWITCH_CHANNEL_NAME}",
                color=discord.Color.purple(),
            )
            embed.set_image(url=thumbnail)
            embed.add_field(name="Viewers", value=str(stream["viewer_count"]), inline=True)
            embed.add_field(name="Jeu", value=stream["game_name"], inline=True)

            await channel.send(
                f"@everyone 🔴 **{config.TWITCH_CHANNEL_NAME}** est en live !",
                embed=embed,
            )

        except Exception as e:
            print(f"[Twitch] Erreur : {e}")

    # ─── Commandes manuelles ──────────────────────────────────────────────────

    @commands.command(name="youtube")
    async def youtube_stats(self, ctx: commands.Context) -> None:
        """Affiche les statistiques de la chaîne YouTube."""
        if not (config.YOUTUBE_API_KEY and config.YOUTUBE_CHANNEL_ID):
            return await ctx.send("❌ Configuration YouTube manquante dans `.env`.")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://www.googleapis.com/youtube/v3/channels",
                    params={
                        "part": "snippet,statistics",
                        "id": config.YOUTUBE_CHANNEL_ID,
                        "key": config.YOUTUBE_API_KEY,
                    },
                ) as resp:
                    data = await resp.json()

            item = data["items"][0]
            snippet = item["snippet"]
            stats = item["statistics"]

            embed = discord.Embed(
                title=snippet["title"],
                description=(snippet["description"] or "")[:300],
                url=f"https://www.youtube.com/channel/{config.YOUTUBE_CHANNEL_ID}",
                color=discord.Color.red(),
            )
            embed.set_thumbnail(url=snippet["thumbnails"]["default"]["url"])
            embed.add_field(name="Abonnés", value=f"{int(stats['subscriberCount']):,}", inline=True)
            embed.add_field(name="Vidéos", value=stats["videoCount"], inline=True)
            embed.add_field(name="Vues totales", value=f"{int(stats['viewCount']):,}", inline=True)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Erreur YouTube : `{e}`")

    @commands.command(name="twitch")
    async def twitch_status(self, ctx: commands.Context) -> None:
        """Vérifie si la chaîne Twitch est en live."""
        if not (config.TWITCH_CLIENT_ID and config.TWITCH_CHANNEL_NAME):
            return await ctx.send("❌ Configuration Twitch manquante dans `.env`.")
        try:
            token = await self._get_twitch_token()
            if not token:
                return await ctx.send("❌ Impossible d'obtenir le token Twitch.")

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.twitch.tv/helix/streams",
                    params={"user_login": config.TWITCH_CHANNEL_NAME},
                    headers={
                        "Client-ID": config.TWITCH_CLIENT_ID,
                        "Authorization": f"Bearer {token}",
                    },
                ) as resp:
                    data = await resp.json()

            streams = data.get("data", [])
            if not streams:
                return await ctx.send(f"📴 **{config.TWITCH_CHANNEL_NAME}** n'est pas en live.")

            stream = streams[0]
            embed = discord.Embed(
                title=f"{config.TWITCH_CHANNEL_NAME} est en LIVE !",
                description=stream["title"],
                url=f"https://twitch.tv/{config.TWITCH_CHANNEL_NAME}",
                color=discord.Color.purple(),
            )
            embed.add_field(name="Jeu", value=stream["game_name"], inline=True)
            embed.add_field(name="Viewers", value=str(stream["viewer_count"]), inline=True)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Erreur Twitch : `{e}`")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Announcements(bot))
