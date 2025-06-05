import discord
from discord import app_commands
import aiohttp
from datetime import datetime
import os

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CANAL_PERMITIDO_ID = 1380015764030881903

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

DATA_URLS = [
    "https://firebasestorage.googleapis.com/v0/b/pegacoment.appspot.com/o/reniec_lote_1.json?alt=media&token=3362066a-1752-4727-b82b-8b388de29ffc",
    "https://firebasestorage.googleapis.com/v0/b/pegacoment.appspot.com/o/reniec_lote_2.json?alt=media&token=f4b5956f-4d6a-4322-a81e-b1acc254e2ea",
    "https://firebasestorage.googleapis.com/v0/b/pegacoment.appspot.com/o/reniec_lote_3.json?alt=media&token=e78ea24f-52bd-4a39-b93a-384d8de9ad5a",
]

async def buscar_en_url(session, url, nombres=None, ap_pat=None, ap_mat=None, dni=None, max_resultados=50):
    resultados = []
    async with session.get(url) as resp:
        if resp.status != 200:
            return resultados
        datos = await resp.json()
        for p in datos:
            if dni and p.get("DNI") != dni:
                continue
            if nombres and nombres not in p.get("NOMBRES", ""):
                continue
            if ap_pat and ap_pat not in p.get("AP_PAT", ""):
                continue
            if ap_mat and ap_mat not in p.get("AP_MAT", ""):
                continue
            resultados.append(p)
            if len(resultados) >= max_resultados:
                break
    return resultados

async def buscar_personas_varios_lotes(nombres=None, ap_pat=None, ap_mat=None, dni=None, max_resultados=50):
    resultados_totales = []
    async with aiohttp.ClientSession() as session:
        for url in DATA_URLS:
            resultados_lote = await buscar_en_url(session, url, nombres, ap_pat, ap_mat, dni, max_resultados - len(resultados_totales))
            resultados_totales.extend(resultados_lote)
            if len(resultados_totales) >= max_resultados:
                break
    return resultados_totales

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

    resultados = await buscar_personas_varios_lotes(nombres, ap_pat, ap_mat, dni)
    if not resultados:
        await interaction.followup.send("❌ No se encontraron resultados.")
        return

    for persona in resultados:
        embed_data = generar_payload_embed(persona)
        embed = discord.Embed.from_dict(embed_data)
        await interaction.followup.send(embed=embed)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"🤖 Bot listo como {bot.user}")
    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Game(name="Esperando comandos...")
    )

bot.run(DISCORD_TOKEN)
