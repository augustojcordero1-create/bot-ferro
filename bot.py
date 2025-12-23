import discord
import asyncio
import feedparser
import os
import requests
from datetime import datetime, timedelta

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
# ESCUDOS DE RIVALES ACTUALIZADOS
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
partidos_previas = set()
eventos_partido = {}  # Para resumen final

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
                    if any(p in texto for p in PALABRAS_PASES) and any(f in texto for f in PALABRAS_FERRO):
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
# FUNCIONES ESTILO CANCHA
# =========================
def formatear_previa(partido, alineacion=True):
    home = partido["teams"]["home"]
    away = partido["teams"]["away"]
    ferro_local = home["id"] == FERRO_TEAM_ID
    rival = away["name"] if ferro_local else home["name"]
    escudo_rival = ESCUDOS_RIVALES.get(rival, "")
    hora = partido["fixture"]["date"]
    estadio = partido["fixture"]["venue"]["name"]
    msg = (
        f"📣 1 HORA ANTES\n\n"
        f"⏰ HOY JUEGA FERRO 💚\n"
        f"🆚 {rival} {escudo_rival}\n"
        f"🕘 {datetime.fromisoformat(hora[:-1]).strftime('%H:%M')}\n"
        f"🏟️ {estadio}"
    )
    # Alineaciones y suplentes
    if alineacion and "lineups" in partido:
        for team in partido["lineups"]:
            equipo = "💚 FERRO" if team["team"]["id"] == FERRO_TEAM_ID else f"🆚 {rival}"
            titulares = "\n".join([p["player"]["name"] for p in team["startXI"]])
            suplentes = ", ".join([p["player"]["name"] for p in team["substitutes"]])
            msg += f"\n\n{equipo} | TITULARES\n{titulares}\nSuplentes: {suplentes}"
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
        return f"@everyone\n⚠️ PENAL PARA {'FERRO 💚' if equipo_id==FERRO_TEAM_ID else rival + ' ' + ESCUDOS_RIVALES.get(rival,'')}\n{marcador}\n🕒 {minuto}'"
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
        return f"@everyone\n⚽ GOOOOOL DE FERROOOOOO 💚\n🟢 {marcador}\n🕒 {minuto}'\n¡DALE VERDOLAGA!"
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

def formatear_suspendido(partido, rival):
    fecha_nueva = partido["fixture"].get("date")
    msg = f"🚨 PARTIDO SUSPENDIDO\nEl partido contra {rival} ha sido suspendido."
    if fecha_nueva:
        msg += f"\n📅 Nueva fecha: {fecha_nueva}"
    return msg

def formatear_estadisticas(partido, rival):
    stats_msg = f"📊 ESTADÍSTICAS FINALES\n💚 Ferro – {rival}\n"
    for s in partido.get("statistics", []):
        equipo = "Ferro" if s["team"]["id"] == FERRO_TEAM_ID else rival
        for stat in s["statistics"]:
            stats_msg += f"{stat['type']}: {stat['value']}\n"
    return stats_msg

def generar_resumen_final(fixture_id, rival, gf, gr):
    resumen = f"🏆 RESUMEN DEL PARTIDO 🏟️\n{formatear_marcador(gf, gr, rival)}\n\n"
    goles, penales, amarillas, rojas = [], [], [], []
    for eid, e in eventos_partido.get(fixture_id, {}).items():
        tipo = e["type"].lower()
        minuto = e["time"]["elapsed"]
        jugador = e["player"]["name"]
        equipo_id = e["team"]["id"]
        if tipo == "goal":
            goles.append(f"- {'Ferro' if equipo_id==FERRO_TEAM_ID else 'Rival'}: {jugador} {minuto}’")
        elif tipo == "penalty":
            detalle = e["detail"].lower()
            if detalle == "penalty scored":
                penales.append(f"- {'Ferro' if equipo_id==FERRO_TEAM_ID else 'Rival'} {minuto}’ convertido")
            elif detalle == "penalty missed":
                penales.append(f"- {'Ferro' if equipo_id==FERRO_TEAM_ID else 'Rival'} {minuto}’ errado")
            elif detalle == "penalty saved":
                penales.append(f"- {'Ferro' if equipo_id==FERRO_TEAM_ID else 'Rival'} {minuto}’ atajado")
        elif tipo == "card":
            color = e["detail"].lower()
            if "yellow" in color:
                amarillas.append(f"- {'Ferro' if equipo_id==FERRO_TEAM_ID else 'Rival'}: {jugador} {minuto}’")
            else:
                rojas.append(f"- {'Ferro' if equipo_id==FERRO_TEAM_ID else 'Rival'}: {jugador} {minuto}’")
    if goles: resumen += "⚽ Goles:\n" + "\n".join(goles) + "\n\n"
    if penales: resumen += "⚠️ Penales:\n" + "\n".join(penales) + "\n\n"
    if amarillas: resumen += "🟨 Tarjetas amarillas:\n" + "\n".join(amarillas) + "\n\n"
    if rojas: resumen += "🟥 Tarjetas rojas:\n" + "\n".join(rojas) + "\n\n"
    resumen += "¡GRACIAS POR SEGUIRNOS! 💚"
    return resumen

# =========================
# LOOP FUTBOL FERRO
# =========================
async def check_ferro_futbol():
    await client.wait_until_ready()
    canal = client.get_channel(CHANNEL_ID_FUTBOL)
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    while True:
        try:
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
                if fixture_id not in eventos_partido:
                    eventos_partido[fixture_id] = {}

                # Suspensión / postergación
                if status in ["SUSP", "PST", "CANC"]:
                    msg = formatear_suspendido(partido, rival)
                    await canal.send(msg)
                    continue

                # Previa 1 hora
                if 0 <= (fixture_time - now).total_seconds() <= 3600 and fixture_id not in partidos_previas:
                    msg_previa = formatear_previa(partido)
                    await canal.send(msg_previa)
                    partidos_previas.add(fixture_id)

                # Inicio
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
                    resumen = generar_resumen_final(fixture_id, rival, gf, gr)
                    await canal.send(resumen)
                    # Estadísticas finales
                    stats_msg = formatear_estadisticas(partido, rival)
                    await canal.send(stats_msg)
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
                        eventos_partido[fixture_id][eid] = e
            await asyncio.sleep(30)
        except Exception as e:
            print("Error fútbol:", e)
            await asyncio.sleep(30)

# =========================
# RUN
# =========================
client.run(TOKEN)
