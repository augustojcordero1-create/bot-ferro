import os
import discord
import feedparser
import asyncio

TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
RSS_URI = "https://rsshub.app/twitter/user/MDPasesPM"

PALABRAS_PASES = [
    "refuerzo",
    "transferencia",
    "alta",
    "baja",
    "llega",
    "se va",
    "incorpora",
    "incorporó",
    "firma",
    "firmó"
]

PALABRAS_FERRO = [
    "ferro",
    "ferro carril oeste",
    "verdolaga",
    "verdolagas",
    "caballito"
]

intents = discord.Intents.default()
client = discord.Client(intents=intents)

ultimos_tweets = set()

@client.event
async def on_ready():
    print(f"Bot conectado como {client.user}")
    client.loop.create_task(check_rss())


async def check_rss():
    await client.wait_until_ready()
    canal = client.get_channel(CHANNEL_ID)

    if canal is None:
        print("ERROR: No se encontró el canal")
        return

    while True:
        try:
            feed = feedparser.parse(RSS_URI)

            for entry in feed.entries:
                if entry.id not in ultimos_tweets:
                    texto = (entry.title + " " + entry.summary).lower()

if (
    any(p in texto for p in PALABRAS_PASES)
    and
    any(f in texto for f in PALABRAS_FERRO)
):

                        mensaje = (
                            f"🟢 **FERRO | MERCADO DE PASES**\n\n"
                            f"📝 {entry.title}\n"
                            f"🔗 {entry.link}"
                        )
                        await canal.send(mensaje)

                    ultimos_tweets.add(entry.id)

            await asyncio.sleep(300)  # 5 minutos

        except Exception as e:
            print(f"Error en RSS: {e}")
            await asyncio.sleep(60)

client.run(TOKEN)


