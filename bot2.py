import discord
from discord import app_commands
import aiohttp
import asyncio
from datetime import datetime
import os
import webserver

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN') 
# TOKEN = 'MTAyNjYwNjYzMjkwMzM4NTE1OA.G7iKXP.00es2C5D78D6kyLFMnmE_I8d6fNAq0nF6lNEUU'  # ! Reemplaza con tu token real
CANAL_PERMITIDO_ID = 1380015764030881903  # ✅ Reemplaza con tu canal real

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# * URLs de los archivos JSON online
DATA_URLS = [
    "https://firebasestorage.googleapis.com/v0/b/pegacoment.appspot.com/o/renien.json?alt=media&token=7353d0a7-dfac-4408-8cd0-4361bc41d008",

]

# * Cache global para datos
data_cache = []

# * Carga todos los JSON remotos al iniciar
async def cargar_datos():
    global data_cache
    data_cache.clear()
    async with aiohttp.ClientSession() as session:
        for url in DATA_URLS:
            async with session.get(url) as resp:
                if resp.status == 200:
                    json_data = await resp.json()
                    data_cache.extend(json_data)
    print(f"✅ {len(data_cache)} registros cargados en memoria")

# * Buscar por DNI o nombres
def buscar_personas(nombres=None, ap_pat=None, ap_mat=None, dni=None):
    resultados = []
    for p in data_cache:
        if dni and p.get("DNI") != dni:
            continue
        if nombres and nombres not in p.get("NOMBRES", ""):
            continue
        if ap_pat and ap_pat not in p.get("AP_PAT", ""):
            continue
        if ap_mat and ap_mat not in p.get("AP_MAT", ""):
            continue
        resultados.append(p)
        if len(resultados) >= 50:
            break
    return resultados

def calcular_edad(fecha_nac_str):
    try:
        d, m, y = fecha_nac_str.split('/')
        f_nac = datetime(int(y), int(m), int(d))
        hoy = datetime.now()
        return hoy.year - f_nac.year - ((hoy.month, hoy.day) < (f_nac.month, f_nac.day))
    except:
        return "Desconocida"

def generar_payload_embed(persona):
    hora_actual = datetime.now().strftime("%H:%M:%S")
    nombre_completo = f"{persona.get('NOMBRES')} {persona.get('AP_PAT')} {persona.get('AP_MAT')}"
    edad = calcular_edad(persona.get('FECHA_NAC', ''))

    embed = {
        "title": "📄 DATOS DE PERSONA",
        "description": f"""
👤 **Nombre completo:** ```diff\n+ {nombre_completo}\n```
🆔 **DNI:** ```diff\n+ {persona.get('DNI', 'Desconocido')}\n```
📍 **Dirección:** ```diff\n+ {persona.get('DIRECCION', 'No disponible')}\n```
👥 **Sexo:** ```diff\n+ {"Masculino" if persona.get("SEXO") == "1" else "Femenino"}\n```
🎂 **Fecha de Nacimiento:** ```diff\n+ {persona.get('FECHA_NAC', 'No disponible')}\n```
🎈 **Edad:** ```diff\n+ {edad}\n```
🕒 **Hora de búsqueda:** ```diff\n+ {hora_actual}\n```
👨 **Padre:** ```diff\n+ {persona.get("PADRE", "No disponible")} {persona.get('AP_PAT', '')}\n```
👩 **Madre:** ```diff\n+ {persona.get("MADRE", "No disponible")} {persona.get('AP_MAT', '')}\n```
""",
        "color": 0x18A558,
        "footer": {"text": "Datos extraídos por ❣ℜ𝔲𝔟𝔦❣"},
        "image": {"url": "https://assets.isthereanydeal.com/018d937f-15d1-7105-b09a-6ce4199e5ad8/banner400.jpg?t=1731711306"}
    }

    return embed

@tree.command(name="buscar", description="Buscar persona")
@app_commands.describe(nombres="Nombres", ap_pat="Apellido paterno", ap_mat="Apellido materno", dni="DNI")
async def buscar(interaction: discord.Interaction, nombres: str = None, ap_pat: str = None, ap_mat: str = None, dni: str = None):
    if interaction.channel_id != CANAL_PERMITIDO_ID:
        await interaction.response.send_message("❌ Comando no permitido aquí.", ephemeral=True)
        return

    if nombres: nombres = nombres.upper()
    if ap_pat: ap_pat = ap_pat.upper()
    if ap_mat: ap_mat = ap_mat.upper()
    if dni: dni = dni.upper()

    await interaction.response.defer()

    resultados = buscar_personas(nombres=nombres, ap_pat=ap_pat, ap_mat=ap_mat, dni=dni)

    if not resultados:
        await interaction.followup.send("❌ No se encontraron resultados.")
        return

    for persona in resultados:
        embed_data = generar_payload_embed(persona)
        embed = discord.Embed.from_dict(embed_data)
        await interaction.followup.send(embed=embed)

@bot.event
async def on_ready():
    await cargar_datos()
    await tree.sync()
    print(f"🤖 Bot listo como {bot.user}")

webserver.keep_alive()  # Iniciar el servidor web para mantener el bot activo
bot.run(DISCORD_TOKEN)
