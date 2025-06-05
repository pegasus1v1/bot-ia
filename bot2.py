import discord
from discord import app_commands
import requests
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
import os

# * Carga variables de entorno para mayor seguridad
TOKEN = os.getenv("DISCORD_TOKEN")  # Token del bot Discord
FIREBASE_CRED_JSON = os.getenv("FIREBASE_CREDENTIALS")  # JSON completo en variable de entorno
FIREBASE_DB_URL = "https://fotos-b8a54-default-rtdb.firebaseio.com"
CANAL_PERMITIDO_ID = 1380015764030881903

# ! Validar que variables importantes estén definidas
if not TOKEN or not FIREBASE_CRED_JSON or not FIREBASE_DB_URL:
    raise Exception("Faltan variables de entorno necesarias: DISCORD_TOKEN, FIREBASE_CRED_JSON, FIREBASE_DB_URL")

# * Inicializar Firebase Admin
import json
cred_dict = json.loads(FIREBASE_CRED_JSON)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred, {
    'databaseURL': FIREBASE_DB_URL
})

def obtener_base_url():
    ref = db.reference("/config/api_url")
    url = ref.get()
    if not url:
        raise Exception("No hay URL de API configurada en Firebase.")
    return url

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# * Cálculo de edad
def calcular_edad(fecha_nac_str):
    try:
        dia, mes, año = fecha_nac_str.split('/')
        fecha_nac = datetime(int(año), int(mes), int(dia))
        hoy = datetime.now()
        edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
        return edad
    except Exception:
        return "Desconocida"

# * Consulta a API con URL dinámica desde Firebase
def buscar_personas(nombres=None, ap_pat=None, ap_mat=None, dni=None, offset=0, limit=5):
    try:
        base_url = obtener_base_url()
        url = f"{base_url}/buscar"
    except Exception as e:
        print(f"Error obteniendo URL base de Firebase: {e}")
        return []

    params = {}
    if dni:
        params['dni'] = dni
    else:
        if nombres: params['nombres'] = nombres
        if ap_pat: params['ap_pat'] = ap_pat
        if ap_mat: params['ap_mat'] = ap_mat
        params['offset'] = offset
        params['limit'] = limit

    try:
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            return resp.json().get("resultados", [])
        else:
            print(f"Error en respuesta API: Código {resp.status_code}")
            return []
    except Exception as e:
        print(f"Error de conexión a API: {e}")
        return []

# * Construcción del embed para Discord
def generar_payload_embed(persona):
    hora_actual = datetime.now().strftime("%H:%M:%S")
    nombre_completo = f"{persona.get('NOMBRES', '')} {persona.get('AP_PAT', '')} {persona.get('AP_MAT', '')}".strip()
    dni = persona.get("DNI", "Desconocido")
    direccion = persona.get("DIRECCION", "No disponible")
    sexo = "Masculino" if persona.get("SEXO") == "1" else "Femenino"
    fecha_nac = persona.get("FECHA_NAC", "No disponible")
    edad = calcular_edad(fecha_nac)
    padre = persona.get("PADRE", "").strip() or "No disponible"
    madre = persona.get("MADRE", "").strip() or "No disponible"

    embed = discord.Embed(
        title="📄 DATOS DE PERSONA",
        description=(
            f"**👤 Nombre completo:**\n```diff\n+ {nombre_completo}```\n"
            f"**🆔 DNI:**\n```diff\n+ {dni}```\n"
            f"**📍 Dirección:**\n```diff\n+ {direccion}```\n"
            f"**👥 Sexo:**\n```diff\n+ {sexo}```\n"
            f"**🎂 Fecha de Nacimiento:**\n```diff\n+ {fecha_nac}```\n"
            f"**🎈 Edad:**\n```diff\n+ {edad}```\n"
            f"**🕒 Hora de búsqueda:**\n```diff\n+ {hora_actual}```\n"
            f"**👨 Padre:**\n```diff\n+ {padre}```\n"
            f"**👩 Madre:**\n```diff\n+ {madre}```"
        ),
        color=0x18A558
    )
    embed.set_image(url="https://assets.isthereanydeal.com/018d937f-15d1-7105-b09a-6ce4199e5ad8/banner400.jpg")
    embed.set_footer(text="Datos extraídos por ❣ℜ𝔲𝔟𝔦❣")
    return embed

# * View con botón para paginar resultados
class ResultadoView(discord.ui.View):
    def __init__(self, nombres, ap_pat, ap_mat, offset):
        super().__init__(timeout=None)
        self.nombres = nombres
        self.ap_pat = ap_pat
        self.ap_mat = ap_mat
        self.offset = offset

    @discord.ui.button(label="▶ Ver más", style=discord.ButtonStyle.primary)
    async def ver_mas_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        nuevos = buscar_personas(
            nombres=self.nombres,
            ap_pat=self.ap_pat,
            ap_mat=self.ap_mat,
            offset=self.offset,
            limit=5
        )
        if not nuevos:
            await interaction.followup.send("❌ No hay más resultados.")
            return

        for persona in nuevos:
            embed = generar_payload_embed(persona)
            await interaction.followup.send(embed=embed)

        nueva_view = ResultadoView(self.nombres, self.ap_pat, self.ap_mat, self.offset + 5)
        await interaction.followup.send("Resultados adicionales:", view=nueva_view)

# * Comando /buscar
@tree.command(name="buscar", description="Buscar persona")
@app_commands.describe(nombres="Nombres", ap_pat="Apellido paterno", ap_mat="Apellido materno", dni="DNI")
async def buscar(interaction: discord.Interaction, nombres: str = None, ap_pat: str = None, ap_mat: str = None, dni: str = None):
    if interaction.channel_id != CANAL_PERMITIDO_ID:
        await interaction.response.send_message("❌ Este comando solo puede usarse en el canal autorizado.", ephemeral=True)
        return

    if nombres: nombres = nombres.upper()
    if ap_pat: ap_pat = ap_pat.upper()
    if ap_mat: ap_mat = ap_mat.upper()
    if dni: dni = dni.upper()

    await interaction.response.defer()

    resultados = buscar_personas(nombres=nombres, ap_pat=ap_pat, ap_mat=ap_mat, dni=dni, offset=0, limit=5)
    if not resultados:
        await interaction.followup.send("❌ No se encontraron resultados con los datos proporcionados.")
        return

    for persona in resultados:
        embed = generar_payload_embed(persona)
        await interaction.followup.send(embed=embed)

    if len(resultados) == 5:
        view = ResultadoView(nombres, ap_pat, ap_mat, offset=5)
        await interaction.followup.send("¿Quieres ver más resultados?", view=view)

# * Evento on_ready
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot conectado como {bot.user}")

bot.run(TOKEN)
