import discord
import asyncio
import feedparser
import os

# =========================
# VARIABLES DE ENTORNO
# =========================
TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

# RSS
RSS_MDPASES = "https://rsshub.app/twitter/user/MDPasesPM"
RSS_FERRO_OFICIAL = "https://rsshub.app/twitter/user/FerroOficial"

# =========================
# PALABRAS CLAVE
# =========================

# Mercado de pases
PALABRAS_PASES = [
    "refuerzo",
    "refuerzos",
    "transferencia",
    "alta",
    "baja",
    "llega",
    "llegó",
    "se va",
    "incorpora",
    "incorporó",
    "firma",
    "firmó",
    "nuevo jugador"
]

# Identificadores de Ferro
PALABRAS_FERRO = [
    "ferro",
    "#ferro",
    "ferro carril oeste",
    "verdolaga",
    "verdolagas",
    "caballito"
]

# Ferro Oficial
PALABRAS_JUGADOR = [
    "jugador"
]

# =========================
# DISCORD CLIENT
# =========================
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Memoria de tweets
ultimos_tweets_mdpases = set()
ultimos_tweets_ferro_oficial = set()

# =========================
# EVENTO READY
# =========================
@client.event
async def on_ready():
    print(f"Bot conectado como {client.user}")
    client.loop.create_task(check_rss())

# =========================
# CHECK RSS
# =========================
async def check_rss():
    await client.wait_until_ready()
    canal = client.get_channel(CHANNEL_ID)

    if canal is None:
        print("ERROR: No se encontró el canal")
        return

    while True:
        try:
            # ==================================================
            # RSS MDPASES (MERCADO DE PASES – SOLO FERRO)
            # ==================================================
            feed_mdpases = feedparser.parse(RSS_MDPASES)

            for entry in feed_mdpases.entries:
                if entry.id not in ultimos_tweets_mdpases:
                    texto = (
                        entry.title +
                        " " +
                        getattr(entry, "summary", "")
                    ).lower()

                    texto = texto.replace("#", "")

                    if (
                        any(p in texto for p in PALABRAS_PASES)
                        and
                        any(f.replace("#", "") in texto for f in PALABRAS_FERRO)
                    ):
                        mensaje = (
                            "🟢 **FERRO | MERCADO DE PASES**\n\n"
                            f"📝 {entry.title}\n"
                            f"🔗 {entry.link}"
                        )
                        await canal.send(mensaje)

                    ultimos_tweets_mdpases.add(entry.id)

            # ==================================================
            # RSS FERRO OFICIAL (SOLO “JUGADOR”)
            # ==================================================
            feed_ferro = feedparser.parse(RSS_FERRO_OFICIAL)

            for entry in feed_ferro.entries:
                if entry.id not in ultimos_tweets_ferro_oficial:
                    texto = (
                        entry.title +
                        " " +
                        getattr(entry, "summary", "")
                    ).lower()

                    texto = texto.replace("#", "")

                    if any(p in texto for p in PALABRAS_JUGADOR):
                        mensaje = (
                            "🟢 **FERRO | COMUNICADO OFICIAL**\n\n"
                            f"📝 {entry.title}\n"
                            f"🔗 {entry.link}"
                        )
                        await canal.send(mensaje)

                    ultimos_tweets_ferro_oficial.add(entry.id)

            await asyncio.sleep(300)  # 5 minutos

        except Exception as e:
            print(f"Error en RSS: {e}")
            await asyncio.sleep(60)

# =========================
# RUN BOT
# =========================
client.run(TOKEN)
