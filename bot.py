import os
import discord
import feedparser
import asyncio

TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = 1452451999067934942
RSS_URL = "https://nitter.net/MDePasesPN/rss"

PALABRAS_CLAVE = [
    "refuerzo",
    "transferencia",
    "alta",
    "baja",
    "llega",
    "se va",
    "ferro"
]

intents = discord.Intents.default()
client = discord.Client(intents=intents)

ultimos_tweets = set()

@client.event
async def on_ready():
    print(f"Bot conectado como {client.user}")
    canal = client.get_channel(CHANNEL_ID)

    while True:
        feed = feedparser.parse(RSS_URL)

        for entry in feed.entries:
            if entry.id not in ultimos_tweets:
                texto = entry.title.lower()

                if any(palabra in texto for palabra in PALABRAS_CLAVE):
                    mensaje = f"🟢 **FERRO | MERCADO DE PASES**\n{entry.title}\n{entry.link}"
                    await canal.send(mensaje)

                ultimos_tweets.add(entry.id)

        await asyncio.sleep(300)

client.run(TOKEN)


