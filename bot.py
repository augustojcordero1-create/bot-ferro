import discord
import asyncio
import feedparser
import os

# =========================
# VARIABLES DE ENTORNO
# =========================
TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID_MERCADO = int(os.environ["CHANNEL_ID_MERCADO"])
CHANNEL_ID_BASQUET = int(os.environ["CHANNEL_ID_BASQUET"])

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
# MEMORIA GLOBAL
# =========================
tweets_enviados = set()

# =========================
# FUNCIONES
# =========================
def limpiar(entry):
    return (
        entry.title + " " + getattr(entry, "summary", "")
    ).lower().replace("#", "")

async def enviar(canal, titulo, emoji, entry):
    await canal.send(
        f"{emoji} **{titulo}**\n\n"
        f"📝 {entry.title}\n"
        f"🔗 {entry.link}"
    )

# =========================
# EVENTO READY
# =========================
@client.event
async def on_ready():
    print(f"Bot conectado como {client.user}")
    client.loop.create_task(check_rss())

# =========================
# LOOP RSS
# =========================
async def check_rss():
    await client.wait_until_ready()

    canal_mercado = client.get_channel(CHANNEL_ID_MERCADO)
    canal_basquet = client.get_channel(CHANNEL_ID_BASQUET)

    if not canal_mercado or not canal_basquet:
        print("ERROR: uno de los canales no existe")
        return

    while True:
        try:
            # ================= MERCADO DE PASES =================
            for entry in feedparser.parse(RSS_MDPASES).entries:
                if entry.id not in tweets_enviados:
                    texto = limpiar(entry)
                    if (
                        any(p in texto for p in PALABRAS_PASES)
                        and any(f in texto for f in PALABRAS_FERRO)
                    ):
                        await enviar(
                            canal_mercado,
                            "FERRO | MERCADO DE PASES",
                            "🟢",
                            entry
                        )
                    tweets_enviados.add(entry.id)

            # ================= FERRO OFICIAL =================
            for entry in feedparser.parse(RSS_FERRO_OFICIAL).entries:
                if entry.id not in tweets_enviados:
                    texto = limpiar(entry)
                    if any(p in texto for p in PALABRAS_JUGADOR):
                        await enviar(
                            canal_mercado,
                            "FERRO | COMUNICADO OFICIAL",
                            "🟢",
                            entry
                        )
                    tweets_enviados.add(entry.id)

            # ================= FERRO BÁSQUET =================
            for entry in feedparser.parse(RSS_FERRO_BASQUET).entries:
                if entry.id not in tweets_enviados:
                    texto = (entry.title + " " + getattr(entry, "summary", "")).lower()
                    if "#ferro" in texto:
                        await enviar(
                            canal_basquet,
                            "FERRO BÁSQUET",
                            "🏀",
                            entry
                        )
                    tweets_enviados.add(entry.id)

            await asyncio.sleep(300)

        except Exception as e:
            print("Error RSS:", e)
            await asyncio.sleep(60)

# =========================
# RUN
# =========================
client.run(TOKEN)
