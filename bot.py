import discord
import asyncio
import feedparser
import os

# =========================
# VARIABLES DE ENTORNO
# =========================
TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

# =========================
# RSS
# =========================
RSS_MDPASES = "https://rsshub.app/twitter/user/MDPasesPM"
RSS_FERRO_OFICIAL = "https://rsshub.app/twitter/user/FerroOficial"
RSS_FERRO_BASQUET = "https://rsshub.app/twitter/user/ferrobasquetok"

# =========================
# PALABRAS CLAVE
# =========================
PALABRAS_PASES = [
    "refuerzo", "refuerzos", "transferencia", "alta", "baja",
    "llega", "llegó", "se va", "incorpora", "incorporó",
    "firma", "firmó", "nuevo jugador"
]

PALABRAS_FERRO = [
    "ferro", "ferro carril oeste",
    "verdolaga", "verdolagas", "caballito"
]

PALABRAS_JUGADOR = ["jugador"]

# =========================
# DISCORD CLIENT
# =========================
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# =========================
# MEMORIA GLOBAL (ANTI DUPES)
# =========================
tweets_enviados = set()

# =========================
# FUNCIONES UTILITARIAS
# =========================
def limpiar_texto(entry):
    return (
        entry.title + " " + getattr(entry, "summary", "")
    ).lower().replace("#", "")

async def enviar(canal, titulo, emoji, entry):
    mensaje = (
        f"{emoji} **{titulo}**\n\n"
        f"📝 {entry.title}\n"
        f"🔗 {entry.link}"
    )
    await canal.send(mensaje)

# =========================
# DEFINICIÓN DE FEEDS
# =========================
FEEDS = [
    {
        "titulo": "FERRO | MERCADO DE PASES",
        "emoji": "🟢",
        "url": RSS_MDPASES,
        "filtro": lambda t: (
            any(p in t for p in PALABRAS_PASES)
            and
            any(f in t for f in PALABRAS_FERRO)
        )
    },
    {
        "titulo": "FERRO | COMUNICADO OFICIAL",
        "emoji": "🟢",
        "url": RSS_FERRO_OFICIAL,
        "filtro": lambda t: any(p in t for p in PALABRAS_JUGADOR)
    },
    {
        "titulo": "FERRO BÁSQUET",
        "emoji": "🏀",
        "url": RSS_FERRO_BASQUET,
        "filtro": lambda t: "#ferro" in t
    }
]

# =========================
# EVENTO READY
# =========================
@client.event
async def on_ready():
    print(f"Bot conectado como {client.user}")
    client.loop.create_task(check_rss())

# =========================
# LOOP PRINCIPAL RSS
# =========================
async def check_rss():
    await client.wait_until_ready()
    canal = client.get_channel(CHANNEL_ID)

    if canal is None:
        print("ERROR: Canal no encontrado")
        return

    while True:
        try:
            for feed in FEEDS:
                rss = feedparser.parse(feed["url"])

                for entry in rss.entries:
                    if entry.id in tweets_enviados:
                        continue

                    texto = limpiar_texto(entry)

                    if feed["filtro"](texto):
                        await enviar(
                            canal,
                            feed["titulo"],
                            feed["emoji"],
                            entry
                        )

                    tweets_enviados.add(entry.id)

            await asyncio.sleep(300)  # 5 minutos

        except Exception as e:
            print(f"Error RSS: {e}")
            await asyncio.sleep(60)

# =========================
# RUN BOT
# =========================
client.run(TOKEN)
