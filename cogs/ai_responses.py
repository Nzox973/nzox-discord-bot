import discord
from discord.ext import commands
from groq import AsyncGroq
import config

_SYSTEM_PROMPT = (
    "Tu es l'assistant IA officiel du serveur Discord NzoxYt. "
    "Tu es sympa, utile et réponds en français par défaut (ou dans la langue du membre). "
    "Tu peux parler de gaming, streaming YouTube/Twitch, et de sujets généraux. "
    "Garde tes réponses concises et adaptées au format Discord. "
    "Ne génère jamais de contenu illégal, haineux ou offensant."
)


class AIResponses(commands.Cog):
    """Réponses IA via Groq (llama-3.3-70b-versatile)."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.client = AsyncGroq(api_key=config.GROQ_API_KEY)
        # Historique de conversation par salon — limité à max_history allers-retours
        self.histories: dict[int, list[dict]] = {}
        self.max_history = 10

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Répond dans le salon IA désigné ou quand le bot est mentionné."""
        if message.author.bot:
            return

        is_ai_channel = bool(config.AI_CHANNEL_ID) and message.channel.id == config.AI_CHANNEL_ID
        is_mentioned = self.bot.user in message.mentions

        if not (is_ai_channel or is_mentioned):
            return

        # Nettoyer la mention du bot si présente
        content = message.content.replace(f"<@{self.bot.user.id}>", "").strip()
        if not content:
            content = "Bonjour !"

        async with message.channel.typing():
            try:
                channel_id = message.channel.id
                history = self.histories.setdefault(channel_id, [])

                history.append({
                    "role": "user",
                    "content": f"{message.author.display_name}: {content}",
                })

                # Fenêtre glissante : garder les N derniers échanges
                if len(history) > self.max_history * 2:
                    self.histories[channel_id] = history[-(self.max_history * 2):]
                    history = self.histories[channel_id]

                response = await self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    max_tokens=1024,
                    messages=[{"role": "system", "content": _SYSTEM_PROMPT}, *history],
                )

                reply = response.choices[0].message.content
                history.append({"role": "assistant", "content": reply})

                # Discord accepte 2 000 caractères max par message
                if len(reply) > 1900:
                    for chunk in [reply[i:i + 1900] for i in range(0, len(reply), 1900)]:
                        await message.reply(chunk)
                else:
                    await message.reply(reply)

            except Exception as e:
                await message.reply(f"❌ Erreur API Groq : `{str(e)[:120]}`")

    @commands.command(name="clearai", aliases=["clear_ai"])
    @commands.has_permissions(manage_messages=True)
    async def clear_ai_history(self, ctx: commands.Context) -> None:
        """[Modo] Efface l'historique de conversation IA de ce salon."""
        self.histories.pop(ctx.channel.id, None)
        await ctx.send("✅ Historique IA effacé pour ce salon.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AIResponses(bot))
