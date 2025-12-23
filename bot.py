import discord
import asyncio
import feedparser
import os
import requests

# =========================
# VARIABLES DE ENTORNO
# =========================
TOKEN = os.environ["DISCORD_TOKEN"]

CHANNEL_ID_MERCADO = int(os.environ["CHANNEL_ID_MERCADO"])
CHANNEL_ID_BASQUET = int(os.environ["CHANNEL_ID_BASQUET"])
CHANNEL_ID_FUTBOL = int(os.environ["CHANNEL_ID_FUTBOL"])

API_FOOTBALL_KEY = os.environ["API_FOOTBALL_KEY"]

FERRO_TEAM_ID = 457  # Ferro Carril Oeste

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

eventos_enviados = set()
partidos_iniciados = set()
partidos_entretiempo = set()
partidos_segundo_tiempo = set()
partidos_finalizados = set()

# =========================
# FUNCIONES RSS
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
# READY
# =========================
@client.event
async def on_ready():
    print(f"Bot conectado como {client.user}")
    client.loop.create_task(check_rss())
    client.loop.create_task(check_ferro_futbol())

# =========================
# LOOP RSS
# =========================
async def check_rss():
    await client.wait_until_ready()

    canal_mercado = client.get_channel(CHANNEL_ID_MERCADO)
    canal_basquet = client.get_channel(CHANNEL_ID_BASQUET)

    while True:
        try:
            for entry in feedparser.parse(RSS_MDPASES).entries:
                if entry.id not in tweets_enviados:
                    texto = limpiar(entry)
                    if (
                        any(p in texto for p in PALABRAS_PASES)
                        and any(f in texto for f in PALABRAS_FERRO)
                    ):
                        await enviar(canal_mercado, "FERRO | MERCADO DE PASES", "🟢", entry)
                    tweets_enviados.add(entry.id)

            for entry in feedparser.parse(RSS_FERRO_OFICIAL).entries:
                if entry.id not in tweets_enviados:
                    if any(p in limpiar(entry) for p in PALABRAS_JUGADOR):
                        await enviar(canal_mercado, "FERRO | COMUNICADO OFICIAL", "🟢", entry)
                    tweets_enviados.add(entry.id)

            for entry in feedparser.parse(RSS_FERRO_BASQUET).entries:
                if entry.id not in tweets_enviados:
                    if "#ferro" in (entry.title + entry.summary).lower():
                        await enviar(canal_basquet, "FERRO BÁSQUET", "🏀", entry)
                    tweets_enviados.add(entry.id)

            await asyncio.sleep(300)

        except Exception as e:
            print("Error RSS:", e)
            await asyncio.sleep(60)

# =========================
# LOOP FUTBOL FERRO
# =========================
async def check_ferro_futbol():
    await client.wait_until_ready()
    canal = client.get_channel(CHANNEL_ID_FUTBOL)

    headers = {"x-apisports-key": API_FOOTBALL_KEY}

    while True:
        try:
            r = requests.get(
                "https://v3.football.api-sports.io/fixtures?live=all",
                headers=headers
            )
            data = r.json().get("response", [])

            for partido in data:
                home = partido["teams"]["home"]
                away = partido["teams"]["away"]

                if home["id"] != FERRO_TEAM_ID and away["id"] != FERRO_TEAM_ID:
                    continue

                fixture_id = partido["fixture"]["id"]
                status = partido["fixture"]["status"]["short"]

                ferro_local = home["id"] == FERRO_TEAM_ID
                rival = away["name"] if ferro_local else home["name"]

                gf = partido["goals"]["home"] if ferro_local else partido["goals"]["away"]
                gr = partido["goals"]["away"] if ferro_local else partido["goals"]["home"]

                marcador = f"**Ferro {gf} - {gr} {rival}**"

                # INICIO
                if status == "1H" and fixture_id not in partidos_iniciados:
                    await canal.send(f"@everyone\n▶ ARRANCÓ EL PARTIDO\n{marcador}")
                    partidos_iniciados.add(fixture_id)

                # ENTRETIEMPO
                if status == "HT" and fixture_id not in partidos_entretiempo:
                    emoji = "🟢" if gf > gr else "🟡" if gf == gr else "🔴"
                    await canal.send(f"@everyone\n⏸ ENTRETIEMPO {emoji}\n{marcador}")
                    partidos_entretiempo.add(fixture_id)

                # SEGUNDO TIEMPO
                if status == "2H" and fixture_id not in partidos_segundo_tiempo:
                    await canal.send(f"@everyone\n🔄 ARRANCÓ EL SEGUNDO TIEMPO\n{marcador}")
                    partidos_segundo_tiempo.add(fixture_id)

                # FINAL
                if status == "FT" and fixture_id not in partidos_finalizados:
                    emoji = "🟢" if gf > gr else "🟡" if gf == gr else "🔴"
                    await canal.send(f"@everyone\n{emoji} FINAL DEL PARTIDO\n{marcador}")
                    partidos_finalizados.add(fixture_id)

                for e in partido["events"]:
                    eid = f'{fixture_id}-{e["time"]["elapsed"]}-{e["type"]}-{e["detail"]}'
                    if eid in eventos_enviados:
                        continue

                    msg = None
                    jugador = e["player"]["name"]
                    minuto = e["time"]["elapsed"]

                    if e["type"] == "Goal":
                        if e["team"]["id"] == FERRO_TEAM_ID:
                            msg = f"@everyone\n⚽ GOL DE FERRO\n👤 {jugador}\n⏱ {minuto}'\n{marcador}"
                        else:
                            msg = f"⚽ Gol del rival ({rival})\n{marcador}"

                    elif e["type"] == "Card":
                        emoji = "🟨" if e["detail"] == "Yellow Card" else "🟥"
                        msg = f"{emoji} {e['detail']}\n👤 {jugador}\n⏱ {minuto}'"

                    if msg:
                        await canal.send(msg)
                        eventos_enviados.add(eid)

            await asyncio.sleep(30)

        except Exception as e:
            print("Error fútbol:", e)
            await asyncio.sleep(30)

# =========================
# RUN
# =========================
client.run(TOKEN)