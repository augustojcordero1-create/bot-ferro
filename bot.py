# =========================
# BOT COMPLETO DE FERRO
# =========================

import discord
import asyncio
import feedparser
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import unicodedata
from aiohttp import web  

# =========================
# CARGAR VARIABLES DE ENTORNO DESDE .ENV
# =========================
load_dotenv()  

TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID_MERCADO = int(os.environ["CHANNEL_ID_MERCADO"])
CHANNEL_ID_BASQUET = int(os.environ["CHANNEL_ID_BASQUET"])
CHANNEL_ID_FUTBOL = int(os.environ["CHANNEL_ID_FUTBOL"])
API_FOOTBALL_KEY = os.environ["API_FOOTBALL_KEY"]

FERRO_TEAM_ID = 457	  # Confirmar ID oficial 2026 en API

# =========================
# ESCUDOS DE RIVALES
# =========================
ESCUDOS_RIVALES = {
    "SAN TELMO": "🔵⚪",
    "SAN MIGUEL": "🟩⚪",
    "COLON": "🔴⚫",
    "DEPORTIVO MORON": "⚪🔴",
    "GODOY CRUZ": "🔵⚪",
    "LOS ANDES": "🔴⚪",
    "ATLANTA": "🟨🔵",
    "ALL BOYS": "⚪⬛",
    "ESTUDIANTES DE CASEROS": "⚪⬛",
    "MITRE": "🟨⬛",
    "ALMIRANTE BROWN": "🟨⬛",
    "CIUDAD BOLIVAR": "🔵",
    "DEFENSORES DE BELGRANO": "🔴⬛",
    "DEPORTIVO MADRYN": "⬛🟨",
    "CENTRAL NORTE": "⚪⬛",
    "RACING DE CORDOBA": "🔵⚪",
    "CHACO FOR EVER": "⚪⬛",
    "ACASSUSO": "🔵⚪"
}

# =========================
# RSS (Nitter)
# =========================
RSS_MDPASES = "https://nitter.auct.eu/MDPasesPM/rss"
RSS_FERRO_OFICIAL = "https://nitter.auct.eu/FerroOficial/rss"
RSS_FERRO_BASQUET = "https://nitter.auct.eu/ferrobasquetok/rss"

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

PALABRAS_JUGADOR = ["jugador", "vinculo"]

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
partidos_previas = set()
eventos_partido = {}  # Para resumen final
previa_mensajes = {}  # fixture_id -> message_id para borrar previa anterior

# =========================
# FUNCIONES RSS
# =========================
def limpiar(entry):
    texto = (entry.title + " " + getattr(entry, "summary", "")).lower().replace("#", "")
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
    return texto

async def enviar(canal, titulo, emoji, entry):
    await canal.send(f"{emoji} **{titulo}**\n\n📝 {entry.title}\n🔗 {entry.link}")

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
                    if any(p in texto for p in PALABRAS_PASES) and any(f in texto for f in PALABRAS_FERRO):
                        await enviar(canal_mercado, "FERRO | MERCADO DE PASES", "🟢", entry)
                    tweets_enviados.add(entry.id)

            for entry in feedparser.parse(RSS_FERRO_OFICIAL).entries:
                if entry.id not in tweets_enviados:
                    texto = limpiar(entry)
                    if any(p in texto for p in PALABRAS_JUGADOR):
                        await enviar(canal_mercado, "FERRO | COMUNICADO OFICIAL", "🟢", entry)
                    tweets_enviados.add(entry.id)

            for entry in feedparser.parse(RSS_FERRO_BASQUET).entries:
                if entry.id not in tweets_enviados:
                    if "#ferro" in (entry.title + getattr(entry, "summary", "")).lower():
                        await enviar(canal_basquet, "FERRO BÁSQUET", "🏀", entry)
                    tweets_enviados.add(entry.id)

            await asyncio.sleep(300)
        except Exception as e:
            print("Error RSS:", e)
            await asyncio.sleep(60)

# =========================
# FUNCIONES ESTILO CANCHA
# =========================
def formatear_previa(partido):
    home = partido["teams"]["home"]
    away = partido["teams"]["away"]
    ferro_local = home["id"] == FERRO_TEAM_ID
    rival = away["name"] if ferro_local else home["name"]
    escudo_rival = ESCUDOS_RIVALES.get(rival, "")
    hora = partido["fixture"]["date"]
    estadio = partido["fixture"]["venue"]["name"]
    return (
        f"📣 1 HORA ANTES\n\n⏰ HOY JUEGA FERRO 💚\n"
        f"🆚 {rival} {escudo_rival}\n"
        f"🕘 {datetime.fromisoformat(hora[:-1]).strftime('%H:%M')}\n"
        f"🏟️ {estadio}"
    )

def formatear_alineacion(lineups):
    titulares = [p["player"]["name"] for p in lineups["startXI"]]
    suplentes = [p["player"]["name"] for p in lineups["substitutes"]]
    msg = "**Titulares:** " + ", ".join(titulares) + "\n**Suplentes:** " + ", ".join(suplentes)
    return msg

def formatear_marcador(gf, gr, rival):
    escudo_rival = ESCUDOS_RIVALES.get(rival, "")
    return f"💚 Ferro {gf} – {gr} {escudo_rival} {rival}"

def formatear_penal(evento, rival, gf, gr):
    minuto = evento["time"]["elapsed"]
    equipo_id = evento["team"]["id"]
    tipo = evento["detail"]
    marcador = formatear_marcador(gf, gr, rival)
    if tipo.lower() == "penalty scored":
        return f"@everyone ⚠️ PENAL PARA {'FERRO 💚' if equipo_id==FERRO_TEAM_ID else rival + ' ' + ESCUDOS_RIVALES.get(rival,'')}\n{marcador}\n🕒 {minuto}'"
    elif tipo.lower() == "penalty missed":
        return f"❌ PENAL ERRADO\n{marcador}\n🕒 {minuto}'"
    elif tipo.lower() == "penalty saved":
        return f"🧤 PENAL ATAJADO POR EL ARQUERO\n{marcador}\n🕒 {minuto}'\n¡DALE FERRO!"
    return None

def formatear_gol(evento, rival, gf, gr):
    minuto = evento["time"]["elapsed"]
    jugador = evento["player"]["name"]
    equipo_id = evento["team"]["id"]
    marcador = formatear_marcador(gf, gr, rival)
    if equipo_id == FERRO_TEAM_ID:
        return f"@everyone ⚽ GOOOOOL DE FERROOOOOO 💚\n🟢 {marcador}\n🕒 {minuto}'\n¡DALE VERDOLAGA!"
    else:
        return f"😡 GOL DEL RIVAL\n🔴 {marcador}\n🕒 {minuto}'"

def formatear_tarjeta(evento, rival):
    minuto = evento["time"]["elapsed"]
    jugador = evento["player"]["name"]
    equipo_id = evento["team"]["id"]
    color = evento["detail"].lower()
    if "yellow" in color:
        return f"🟨 TARJETA AMARILLA\n🧑‍🦱 {jugador} ({'Ferro' if equipo_id==FERRO_TEAM_ID else rival})\n🕒 {minuto}'"
    else:
        return f"🟥 EXPULSADO\n🧑‍🦱 {jugador} ({'Ferro' if equipo_id==FERRO_TEAM_ID else rival})\n🕒 {minuto}'"

def formatear_final(gf, gr, rival):
    marcador = formatear_marcador(gf, gr, rival)
    if gf > gr:
        return f"🏁 FINAL DEL PARTIDO 🟢\n💚 GANÓ FERRO\n{marcador}\n¡Vamos Verdolaga!"
    elif gf == gr:
        return f"🏁 FINAL 🟡\n{marcador}"
    else:
        return f"🏁 FINAL 🔴\n{marcador}"

def formatear_entretiempo(gf, gr, rival):
    marcador = formatear_marcador(gf, gr, rival)
    return f"⏱️ ENTRETIEMPO EN CABALLITO\n🟢 {marcador}"

# =========================
# LOOP FUTBOL FERRO
# =========================
async def check_ferro_futbol():
    await client.wait_until_ready()
    canal = client.get_channel(CHANNEL_ID_FUTBOL)
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    while True:
        try:
            # Obtener fixtures en vivo y próximos
            r = requests.get("https://v3.football.api-sports.io/fixtures?live=all", headers=headers)
            data = r.json().get("response", [])
            now = datetime.utcnow()
            for partido in data:
                home = partido["teams"]["home"]
                away = partido["teams"]["away"]
                if home["id"] != FERRO_TEAM_ID and away["id"] != FERRO_TEAM_ID:
                    continue
                fixture_id = partido["fixture"]["id"]
                status = partido["fixture"]["status"]["short"]
                fixture_time = datetime.fromisoformat(partido["fixture"]["date"][:-1])
                ferro_local = home["id"] == FERRO_TEAM_ID
                rival = away["name"] if ferro_local else home["name"]
                gf = partido["goals"]["home"] if ferro_local else partido["goals"]["away"]
                gr = partido["goals"]["away"] if ferro_local else partido["goals"]["home"]

                # =========================
                # Previa a las 00:00
                # =========================
                now_arg = datetime.utcnow() + timedelta(hours=-3)  # Ajuste hora argentina
                if now_arg.hour == 0 and fixture_id not in partidos_previas:
                    # Borrar previa anterior solo si es del mismo partido
                    if fixture_id in previa_mensajes:
                        try:
                            old_msg = await canal.fetch_message(previa_mensajes[fixture_id])
                            await old_msg.delete()
                        except:
                            pass
                    msg_previa = formatear_previa(partido)
                    msg = await canal.send(f"@everyone\n{msg_previa}")
                    previa_mensajes[fixture_id] = msg.id
                    partidos_previas.add(fixture_id)

                # =========================
                # Alineación
                # =========================
                lineups = partido.get("lineups")
                if lineups:
                    msg_alineacion = formatear_alineacion(lineups)
                    await canal.send(f"📝 Alineación de {rival} vs Ferro:\n{msg_alineacion}")

                # =========================
                # Inicio
                # =========================
                if status == "1H" and fixture_id not in partidos_iniciados:
                    await canal.send(f"@everyone\n▶ ARRANCÓ EL PARTIDO\n🟢 {formatear_marcador(gf, gr, rival)}")
                    partidos_iniciados.add(fixture_id)

                # Entretiempo
                if status == "HT" and fixture_id not in partidos_entretiempo:
                    msg = formatear_entretiempo(gf, gr, rival)
                    await canal.send(msg)
                    partidos_entretiempo.add(fixture_id)

                # Segundo tiempo
                if status == "2H" and fixture_id not in partidos_segundo_tiempo:
                    await canal.send(f"@everyone\n🔄 ARRANCÓ EL SEGUNDO TIEMPO\n🟢 {formatear_marcador(gf, gr, rival)}")
                    partidos_segundo_tiempo.add(fixture_id)

                # Final
                if status == "FT" and fixture_id not in partidos_finalizados:
                    msg = formatear_final(gf, gr, rival)
                    await canal.send(msg)
                    partidos_finalizados.add(fixture_id)

                # Eventos en vivo
                for e in partido.get("events", []):
                    eid = f'{fixture_id}-{e["time"]["elapsed"]}-{e["type"]}-{e["detail"]}'
                    if eid in eventos_enviados:
                        continue
                    msg = None
                    tipo_evento = e["type"].lower()
                    if tipo_evento == "goal":
                        msg = formatear_gol(e, rival, gf, gr)
                    elif tipo_evento == "card":
                        msg = formatear_tarjeta(e, rival)
                    elif tipo_evento == "penalty":
                        msg = formatear_penal(e, rival, gf, gr)
                    if msg:
                        await canal.send(msg)
                        eventos_enviados.add(eid)
                        eventos_partido.setdefault(fixture_id, {})[eid] = e

            await asyncio.sleep(30)
        except Exception as e:
            print("Error fútbol:", e)
            await asyncio.sleep(30)

# =========================
# SERVIDOR HTTP PARA KOYEB
# =========================
async def handle(request):
    return web.Response(text="Bot de Ferro corriendo ✅")

app = web.Application()
app.router.add_get("/", handle)

# =========================
# RUN
# =========================
# Iniciar HTTP server y bot de Discord juntos
async def main():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=int(os.environ.get("PORT", 8080)))
    await site.start()
    print("HTTP server activo en el puerto", os.environ.get("PORT", 8080))
    await client.start(TOKEN)

asyncio.run(main())
