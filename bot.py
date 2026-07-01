import discord
import os
import json
import time
import yt_dlp
import asyncio
import datetime
import wavelink
from dotenv import load_dotenv
from collections import deque
from discord.ext import tasks, commands
 
load_dotenv()
 
print("Lancement du bot...")
 
 
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
 
bot = commands.Bot(command_prefix=["!", "+"], intents=intents, help_command=None)
 
# =========================================================
#                  CONFIG ANTI-RAID
# =========================================================
 
CONFIG_PATH = "antiraid_config.json"
 
DEFAULT_CONFIG = {
    "enabled": True,
    "join_threshold": 5,          # nombre de joins...
    "join_window": 10,            # ...en X secondes -> déclenche l'alerte
    "min_account_age_hours": 24,  # comptes plus jeunes que ça = suspects
    "action": "kick",             # "kick", "ban", ou "quarantine"
    "auto_lockdown": True,        # verrouille le serveur si raid détecté
    "log_channel_id": None,       # salon de logs anti-raid
    "quarantine_role_id": None,   # rôle utilisé si action = "quarantine"
    "whitelist_role_ids": [],     # rôles jamais concernés
}
 
 
def load_all_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}
 
 
def save_all_config(data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
 
 
async def custom_setup_hook():
    node = wavelink.Node(
        uri="https://lavalink-production-f694.up.railway.app:443",
        password="password"
    )
    await wavelink.Pool.connect(nodes=[node], client=bot)
    print("Nœud Lavalink configuré dans le pool.")
 
bot.setup_hook = custom_setup_hook
 
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'username': 'oauth2',
    'password': '',
}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}
cookies_content = os.environ.get('YOUTUBE_COOKIES')
if cookies_content:
    with open('cookies.txt', 'w') as f:
        f.write(cookies_content)
    YTDL_OPTIONS['cookiefile'] = 'cookies.txt'
    print(f"Cookies écrits : {len(cookies_content)} caractères, fichier présent : {os.path.exists('cookies.txt')}", flush=True)
else:
    print("⚠️ Aucune variable YOUTUBE_COOKIES trouvée !", flush=True)
 
 
def load_warns():
    try:
        with open('warns.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
 
 
def save_warns(data):
    with open('warns.json', 'w') as f:
        json.dump(data, f, indent=4)
 
 
# =========================================================
#                  VUES POUR LES TICKETS
# =========================================================
 
class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
 
    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Fermeture du ticket...", ephemeral=True)
        await interaction.channel.delete()
 
 
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
 
    @discord.ui.button(label="Créer un ticket", style=discord.ButtonStyle.green, custom_id="create_ticket_btn")
    async def ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
 
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
 
        channel = await guild.create_text_channel(
            name=f"ticket-{member.name}",
            overwrites=overwrites
        )
 
        await interaction.response.send_message(f"Votre ticket a été créé ici : {channel.mention}", ephemeral=True)
 
        embed = discord.Embed(
            title="Ticket Ouvert",
            description=f"Bonjour {member.mention},\nUn membre de l'équipe va s'occuper de vous. Cliquez sur le bouton ci-dessous pour fermer ce ticket.",
            color=discord.Color.green()
        )
        await channel.send(embed=embed, view=TicketCloseView())
 
 
# =========================================================
#                  EFFETS ET LOOP
# =========================================================
 
@tasks.loop(hours=720)
async def message_recrutement_mensuel():
    ID_SALON_STAFF = 1521077673663660165
    channel = bot.get_channel(ID_SALON_STAFF)
 
    if channel:
        embed = discord.Embed(
            title="Rejoignez l'équipe de T-Shirt",
            description="T-Shirt recrute du personnel. Voici les conditions :",
            color=discord.Color.blue()
        )
        embed.add_field(name="Age minimum", value="Pour devenir staff minimum 15 ans", inline=False)
        embed.add_field(name="Activité", value="5h de vocal ou 500 messages", inline=False)
        embed.add_field(name="Clean", value="Pour finir faut être clean 0 sanction", inline=False)
        embed.add_field(name="Candidature", value="Si vous souhaitez devenir Staff, contactez une personne haut gradée.", inline=False)
        embed.set_footer(text="Cordialement")
        embed.set_image(url="https://i.pinimg.com/webp85/1200x/a8/84/a8/a884a8c972360381071e972f1a6b659e.webp")
 
        await channel.send(content="@everyone", embed=embed)
 
 
# =========================================================
#                  COG ANTI-RAID
# =========================================================
 
class AntiRaid(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.all_config = load_all_config()
        # historique des joins par serveur : {guild_id: deque[timestamps]}
        self.join_times: dict[int, deque] = {}
        # serveurs actuellement en raid détecté (pour éviter le spam d'alertes)
        self.raid_active: set[int] = set()
 
    # ---------- Config helpers ----------
 
    def get_config(self, guild_id: int) -> dict:
        gid = str(guild_id)
        if gid not in self.all_config:
            self.all_config[gid] = DEFAULT_CONFIG.copy()
            save_all_config(self.all_config)
        return self.all_config[gid]
 
    def set_config(self, guild_id: int, key: str, value):
        gid = str(guild_id)
        cfg = self.get_config(guild_id)
        cfg[key] = value
        self.all_config[gid] = cfg
        save_all_config(self.all_config)
 
    async def log(self, guild: discord.Guild, message: str, color=discord.Color.orange()):
        cfg = self.get_config(guild.id)
        channel_id = cfg.get("log_channel_id")
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if channel:
            embed = discord.Embed(
                description=message,
                color=color,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            embed.set_author(name="🛡️ Anti-Raid")
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass
 
    # ---------- Listener principal ----------
 
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        cfg = self.get_config(guild.id)
 
        if not cfg["enabled"]:
            return
 
        now = time.time()
 
        # --- 1. Vérif compte trop récent ---
        account_age_hours = (now - member.created_at.timestamp()) / 3600
        if account_age_hours < cfg["min_account_age_hours"]:
            await self.handle_suspect(member, f"Compte créé il y a {account_age_hours:.1f}h (< {cfg['min_account_age_hours']}h)")
 
        # --- 2. Vérif afflux de joins (raid) ---
        dq = self.join_times.setdefault(guild.id, deque())
        dq.append(now)
 
        while dq and now - dq[0] > cfg["join_window"]:
            dq.popleft()
 
        if len(dq) >= cfg["join_threshold"] and guild.id not in self.raid_active:
            self.raid_active.add(guild.id)
            await self.trigger_raid_alert(guild, len(dq))
 
    async def handle_suspect(self, member: discord.Member, reason: str):
        guild = member.guild
        cfg = self.get_config(guild.id)
 
        if any(r.id in cfg["whitelist_role_ids"] for r in getattr(member, "roles", [])):
            return
 
        action = cfg["action"]
        try:
            if action == "kick":
                await member.kick(reason=f"Anti-raid: {reason}")
                await self.log(guild, f"👢 **{member}** kické — {reason}", discord.Color.red())
            elif action == "ban":
                await member.ban(reason=f"Anti-raid: {reason}")
                await self.log(guild, f"🔨 **{member}** banni — {reason}", discord.Color.dark_red())
            elif action == "quarantine":
                role_id = cfg.get("quarantine_role_id")
                role = guild.get_role(role_id) if role_id else None
                if role:
                    await member.add_roles(role, reason="Anti-raid: quarantaine")
                    await self.log(guild, f"⚠️ **{member}** mis en quarantaine — {reason}", discord.Color.gold())
                else:
                    await self.log(guild, f"❌ Rôle de quarantaine introuvable pour **{member}**", discord.Color.red())
        except discord.Forbidden:
            await self.log(guild, f"❌ Permissions insuffisantes pour agir sur **{member}**", discord.Color.red())
 
    async def trigger_raid_alert(self, guild: discord.Guild, count: int):
        cfg = self.get_config(guild.id)
        await self.log(
            guild,
            f"🚨 **RAID DÉTECTÉ** — {count} arrivées en moins de {cfg['join_window']}s.",
            discord.Color.dark_red(),
        )
 
        if cfg["auto_lockdown"]:
            await self.do_lockdown(guild)
            await self.log(guild, "🔒 Lockdown automatique activé sur tout le serveur.", discord.Color.dark_red())
 
    # ---------- Lockdown global ----------
 
    async def do_lockdown(self, guild: discord.Guild):
        for channel in guild.text_channels:
            try:
                overwrite = channel.overwrites_for(guild.default_role)
                overwrite.send_messages = False
                await channel.set_permissions(guild.default_role, overwrite=overwrite)
            except discord.Forbidden:
                continue
 
    async def undo_lockdown(self, guild: discord.Guild):
        for channel in guild.text_channels:
            try:
                overwrite = channel.overwrites_for(guild.default_role)
                overwrite.send_messages = None
                await channel.set_permissions(guild.default_role, overwrite=overwrite)
            except discord.Forbidden:
                continue
 
    # ---------- Commandes ----------
 
    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lockdown(self, ctx: commands.Context):
        """Verrouille manuellement TOUS les salons textuels du serveur."""
        await self.do_lockdown(ctx.guild)
        await ctx.send("🔒 Lockdown activé sur tout le serveur.")
 
    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unlockdown(self, ctx: commands.Context):
        """Retire le lockdown manuel sur tous les salons textuels."""
        self.raid_active.discard(ctx.guild.id)
        await self.undo_lockdown(ctx.guild)
        await ctx.send("🔓 Lockdown levé sur tout le serveur.")
 
    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def antiraid(self, ctx: commands.Context):
        """Affiche la config actuelle de l'anti-raid."""
        cfg = self.get_config(ctx.guild.id)
        embed = discord.Embed(title="🛡️ Configuration Anti-Raid", color=discord.Color.blue())
        embed.add_field(name="Activé", value=str(cfg["enabled"]), inline=True)
        embed.add_field(name="Seuil de joins", value=f"{cfg['join_threshold']} en {cfg['join_window']}s", inline=True)
        embed.add_field(name="Âge min. compte", value=f"{cfg['min_account_age_hours']}h", inline=True)
        embed.add_field(name="Action", value=cfg["action"], inline=True)
        embed.add_field(name="Auto-lockdown", value=str(cfg["auto_lockdown"]), inline=True)
        log_chan = ctx.guild.get_channel(cfg["log_channel_id"]) if cfg["log_channel_id"] else None
        embed.add_field(name="Salon de logs", value=log_chan.mention if log_chan else "Aucun", inline=True)
        await ctx.send(embed=embed)
 
    @antiraid.command(name="toggle")
    @commands.has_permissions(administrator=True)
    async def antiraid_toggle(self, ctx: commands.Context):
        cfg = self.get_config(ctx.guild.id)
        self.set_config(ctx.guild.id, "enabled", not cfg["enabled"])
        await ctx.send(f"🛡️ Anti-raid : {'activé ✅' if not cfg['enabled'] else 'désactivé ❌'}")
 
    @antiraid.command(name="seuil")
    @commands.has_permissions(administrator=True)
    async def antiraid_seuil(self, ctx: commands.Context, joins: int, secondes: int):
        """Ex: +antiraid seuil 5 10  -> alerte si 5 joins en 10s"""
        self.set_config(ctx.guild.id, "join_threshold", joins)
        self.set_config(ctx.guild.id, "join_window", secondes)
        await ctx.send(f"✅ Seuil mis à jour : {joins} joins en {secondes}s.")
 
    @antiraid.command(name="age")
    @commands.has_permissions(administrator=True)
    async def antiraid_age(self, ctx: commands.Context, heures: int):
        """Ex: +antiraid age 24 -> comptes de moins de 24h = suspects"""
        self.set_config(ctx.guild.id, "min_account_age_hours", heures)
        await ctx.send(f"✅ Âge minimum du compte mis à jour : {heures}h.")
 
    @antiraid.command(name="action")
    @commands.has_permissions(administrator=True)
    async def antiraid_action(self, ctx: commands.Context, action: str):
        """Ex: +antiraid action kick | ban | quarantine"""
        if action not in ("kick", "ban", "quarantine"):
            await ctx.send("❌ Action invalide. Choisis parmi : kick, ban, quarantine.")
            return
        self.set_config(ctx.guild.id, "action", action)
        await ctx.send(f"✅ Action anti-raid réglée sur : `{action}`.")
 
    @antiraid.command(name="quarantinerole")
    @commands.has_permissions(administrator=True)
    async def antiraid_quarantine_role(self, ctx: commands.Context, role: discord.Role):
        """Définit le rôle utilisé pour la quarantaine."""
        self.set_config(ctx.guild.id, "quarantine_role_id", role.id)
        await ctx.send(f"✅ Rôle de quarantaine réglé sur {role.mention}.")
 
    @antiraid.command(name="logs")
    @commands.has_permissions(administrator=True)
    async def antiraid_logs(self, ctx: commands.Context, channel: discord.TextChannel):
        """Définit le salon de logs anti-raid."""
        self.set_config(ctx.guild.id, "log_channel_id", channel.id)
        await ctx.send(f"✅ Salon de logs réglé sur {channel.mention}.")
 
    @antiraid.command(name="autolockdown")
    @commands.has_permissions(administrator=True)
    async def antiraid_autolockdown(self, ctx: commands.Context):
        """Active/désactive le lockdown automatique en cas de raid détecté."""
        cfg = self.get_config(ctx.guild.id)
        self.set_config(ctx.guild.id, "auto_lockdown", not cfg["auto_lockdown"])
        await ctx.send(f"✅ Auto-lockdown : {'activé' if not cfg['auto_lockdown'] else 'désactivé'}")
 
    @antiraid.command(name="whitelist")
    @commands.has_permissions(administrator=True)
    async def antiraid_whitelist(self, ctx: commands.Context, role: discord.Role):
        """Ajoute/retire un rôle de la whitelist anti-raid."""
        cfg = self.get_config(ctx.guild.id)
        ids = cfg["whitelist_role_ids"]
        if role.id in ids:
            ids.remove(role.id)
            msg = f"➖ {role.mention} retiré de la whitelist."
        else:
            ids.append(role.id)
            msg = f"➕ {role.mention} ajouté à la whitelist."
        self.set_config(ctx.guild.id, "whitelist_role_ids", ids)
        await ctx.send(msg)
 
    @commands.command(name="reset_raidflag")
    @commands.has_permissions(administrator=True)
    async def reset_raidflag(self, ctx: commands.Context):
        """Réinitialise le drapeau 'raid en cours' si besoin (debug)."""
        self.raid_active.discard(ctx.guild.id)
        await ctx.send("♻️ État de raid réinitialisé.")
 
 
# =========================================================
#                  UNIFICATION DU ON_READY
# =========================================================
 
@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    print(f"Le nœud Lavalink {payload.node.identifier} est connecté avec succès !")
 
 
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user.name}")
 
    if not bot.get_cog("MusicBot"):
        await bot.add_cog(MusicBot(bot))
    if not bot.get_cog("AntiRaid"):
        await bot.add_cog(AntiRaid(bot))
 
    nom_activite = "T-shirt | Dev by 9vibe (1 sur 5) | 0 restante"
    await bot.change_presence(activity=discord.Game(name=nom_activite))
 
    try:
        synced = await bot.tree.sync()
        print(f"Commandes slash synchronisées : {len(synced)}")
    except Exception as e:
        print(f"Erreur sync : {e}")
 
    if not message_recrutement_mensuel.is_running():
        message_recrutement_mensuel.start()
 
    bot.add_view(TicketView())
    bot.add_view(TicketCloseView())
 
    ID_SALON_TICKET = 1518340932813062215
    channel_ticket = bot.get_channel(ID_SALON_TICKET)
    if channel_ticket:
        messages = [msg async for msg in channel_ticket.history(limit=1)]
        if not messages:
            embed = discord.Embed(
                title="Besoin d'aide ?",
                description="Cliquez sur le bouton ci-dessous pour ouvrir un ticket de support privé.",
                color=discord.Color.blue(),
            )
            await channel_ticket.send(embed=embed, view=TicketView())
            print("Panneau de ticket automatique envoyé avec succès !")
 
    ID_SALON_PUB = 1518709316818043001
    channel_pub = bot.get_channel(ID_SALON_PUB)
    if channel_pub:
        messages_pub = [msg async for msg in channel_pub.history(limit=1)]
        if not messages_pub:
            texte_pub = """Tu cherches un endroit cool pour discuter, rencontrer du monde et jouer ensemble ?
Rejoins T shirt, une communauté conviviale où bonne humeur et gaming sont au rendez-vous !
 
Discussions libres et respectueuses
Sessions de jeux entre membres
Délires, memes et ambiance détendue
Une communauté active et accueillante
 
Que tu sois casual ou tryhard, tu as ta place ici ! Rejoins-nous et fais partie de l'aventure T shirt dès maintenant Au 5 invites au rôles !! 
 
https://discord.gg/PM6Zsca8xe
 
Si vous aimez le serveur T shirt , n'hésitez pas à en parler autour de vous ou à inviter vos amis
Plus on est nombreux, plus l'ambiance sera folle @everyone"""
 
            await channel_pub.send(content=texte_pub)
            print("Message de pub envoyé avec succès !")
 
 
# =========================================================
#                  AUTRES ÉVÉNEMENTS
# =========================================================
 
@bot.event
async def on_member_join(member):
    ID_DU_SALON = 1518341039499378739
    channel = bot.get_channel(ID_DU_SALON)
    if channel:
        await channel.send(
            f"Bienvenue {member.mention} sur le serveur ! Viens discuter dans le chat !"
        )
 
    ID_SALON_STAFF = 1521077673663660165
    channel_staff = bot.get_channel(ID_SALON_STAFF)
    if channel_staff:
        await channel_staff.send(f"{member.mention}", delete_after=1)
 
 
@bot.event
async def on_member_update(before, after):
    if before.guild.premium_subscription_count < after.guild.premium_subscription_count:
        ID_SALON_BOOST = 1519027720367898835
        channel = bot.get_channel(ID_SALON_BOOST)
 
        if channel:
            embed = discord.Embed(
                title="Un énorme MERCI !",
                description=f"{after.mention}\n\nMerci d'avoir boosté le serveur ! Votre soutien est précieux. 💖",
                color=discord.Color.fuchsia(),
            )
            embed.set_thumbnail(url=after.display_avatar.url)
            await channel.send(embed=embed)
 
 
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)
 
 
# =========================================================
#                  COG MUSIQUE
# =========================================================
 
class MusicBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
 
    @commands.command(name='play')
    async def play(self, ctx, *, search: str):
        if not ctx.author.voice:
            return await ctx.send("Tu dois être dans un salon vocal pour faire ça !")
 
        voice_channel = ctx.author.voice.channel
 
        if not ctx.voice_client:
            vc: wavelink.Player = await voice_channel.connect(cls=wavelink.Player)
        else:
            vc: wavelink.Player = ctx.voice_client
 
        await ctx.send(f"🔍 Recherche de `{search}`...")
 
        try:
            tracks = await wavelink.Playable.search(search)
            if not tracks:
                return await ctx.send("Impossible de trouver ou de lire cette musique.")
            track = tracks[0]
        except Exception as e:
            print(f"Erreur wavelink: {e}")
            import traceback
            traceback.print_exc()
            return await ctx.send("Impossible de trouver ou de lire cette musique.")
 
        await vc.queue.put_wait(track)
        await ctx.send(f"🎵 Ajouté à la file : **{track.title}**")
 
        print(f"DEBUG état player -> connected: {vc.connected}, playing: {vc.playing}, paused: {vc.paused}")
 
        if not vc.playing and not vc.paused:
            try:
                await vc.play(vc.queue.get())
            except Exception as e:
                print(f"Erreur lors du play(): {e}")
                import traceback
                traceback.print_exc()
                await ctx.send(f"❌ Erreur lors du lancement de la lecture : `{e}`")
 
    @commands.command(name='pause')
    async def pause(self, ctx):
        vc: wavelink.Player = ctx.voice_client
        if vc and vc.playing and not vc.paused:
            await vc.pause(True)
            await ctx.send("⏸️ Musique mise en pause.")
        else:
            await ctx.send("Aucune musique n'est en cours de lecture.")
 
    @commands.command(name='resume')
    async def resume(self, ctx):
        vc: wavelink.Player = ctx.voice_client
        if vc and vc.paused:
            await vc.pause(False)
            await ctx.send("▶️ Musique reprise.")
        else:
            await ctx.send("La musique n'est pas en pause.")
 
    @commands.command(name='volume')
    async def volume(self, ctx, volume: int):
        vc: wavelink.Player = ctx.voice_client
        if not vc:
            return await ctx.send("Je ne suis pas connecté à un salon vocal.")
        if not 0 <= volume <= 100:
            return await ctx.send("❌ Le volume doit être entre 0 et 100.")
        await vc.set_volume(volume)
        await ctx.send(f"🔊 Volume réglé à **{volume}%**.")
 
    @commands.command(name='skip')
    async def skip(self, ctx):
        vc: wavelink.Player = ctx.voice_client
        if vc and vc.playing:
            await vc.skip(force=True)
            await ctx.send("⏭️ Musique passée !")
        else:
            await ctx.send("Aucune musique n'est en cours de lecture.")
 
    @commands.command(name='stop')
    async def stop(self, ctx):
        vc: wavelink.Player = ctx.voice_client
        if vc:
            vc.queue.clear()
            await vc.disconnect()
            await ctx.send("🛑 Musique arrêtée et déconnexion.")
        else:
            await ctx.send("Je ne suis pas connecté à un salon vocal.")
 
    @commands.command(name='queue')
    async def queue_list(self, ctx):
        vc: wavelink.Player = ctx.voice_client
        if not vc or vc.queue.is_empty:
            return await ctx.send("La file d'attente est vide.")
        embed = discord.Embed(title="📋 File d'attente", color=discord.Color.blue())
        description = ""
        for i, track in enumerate(vc.queue, start=1):
            description += f"{i}. **{track.title}**\n"
        embed.description = description
        await ctx.send(embed=embed)
 
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player:
            return
        if not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)
 
    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        player = payload.player
        if not player or not player.guild:
            return
        channel = player.guild.system_channel
        message = getattr(payload.exception, "message", str(payload.exception))
        print(f"Erreur Lavalink (track exception) : {message}")
        if channel:
            await channel.send(f"❌ Impossible de lire ce morceau (erreur Lavalink) : `{message}`")
 
 
@bot.command()
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, message: str):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass
    await ctx.send(message)
 
 
@say.error
async def say_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "❌ Tu n'as pas la permission d'utiliser cette commande.",
            delete_after=5,
        )
 
 
# =========================================================
#                  MENU +help AVEC BOUTONS
# =========================================================
 
def build_main_help_embed():
    embed = discord.Embed(
        title="📖 Menu d'aide",
        description="Choisis une catégorie ci-dessous en cliquant sur un bouton.",
        color=discord.Color.blue(),
    )
    embed.add_field(name="🛡️ Modération", value="Commandes de gestion des membres et des salons", inline=False)
    embed.add_field(name="🚨 Anti-Raid", value="Protection automatique du serveur", inline=False)
    embed.add_field(name="🎵 Musique", value="Commandes pour écouter de la musique", inline=False)
    embed.set_footer(text="Clique sur un bouton pour voir les commandes de la catégorie")
    return embed
 
 
def build_moderation_embed():
    embed = discord.Embed(title="🛡️ Commandes de Modération", color=discord.Color.blurple())
    embed.add_field(name="Membres", value="`+userinfo`, `+ban`, `+unban`, `+kick`, `+mute`, `+unmute`", inline=False)
    embed.add_field(name="Avertissements", value="`+warn`, `+history`", inline=False)
    embed.add_field(name="Salons", value="`+lock`, `+unlock`, `+clear`, `+say`", inline=False)
    return embed
 
 
def build_antiraid_embed():
    embed = discord.Embed(title="🚨 Commandes Anti-Raid", color=discord.Color.red())
    embed.add_field(name="Lockdown global", value="`+lockdown`, `+unlockdown`", inline=False)
    embed.add_field(name="Configuration", value=(
        "`+antiraid` (voir la config)\n"
        "`+antiraid toggle`\n"
        "`+antiraid seuil <joins> <secondes>`\n"
        "`+antiraid age <heures>`\n"
        "`+antiraid action <kick|ban|quarantine>`\n"
        "`+antiraid quarantinerole @role`\n"
        "`+antiraid logs #salon`\n"
        "`+antiraid autolockdown`\n"
        "`+antiraid whitelist @role`"
    ), inline=False)
    embed.add_field(name="Debug", value="`+reset_raidflag`", inline=False)
    return embed
 
 
def build_musique_embed():
    embed = discord.Embed(title="🎵 Commandes Musique", color=discord.Color.green())
    embed.add_field(name="Lecture", value="`+play`, `+pause`, `+resume`, `+skip`, `+stop`", inline=False)
    embed.add_field(name="Autres", value="`+queue`, `+volume`", inline=False)
    return embed
 
 
class HelpCategoryView(discord.ui.View):
    def __init__(self, author: discord.abc.User):
        super().__init__(timeout=120)
        self.author = author
 
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Ce menu n'est pas pour toi.", ephemeral=True)
            return False
        return True
 
    @discord.ui.button(label="⬅️ Retour", style=discord.ButtonStyle.gray)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_main_help_embed()
        await interaction.response.edit_message(embed=embed, view=HelpMainView(self.author))
 
 
class HelpMainView(discord.ui.View):
    def __init__(self, author: discord.abc.User):
        super().__init__(timeout=120)
        self.author = author
 
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Ce menu n'est pas pour toi.", ephemeral=True)
            return False
        return True
 
    @discord.ui.button(label="🛡️ Modération", style=discord.ButtonStyle.blurple)
    async def moderation_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_moderation_embed()
        await interaction.response.edit_message(embed=embed, view=HelpCategoryView(self.author))
 
    @discord.ui.button(label="🚨 Anti-Raid", style=discord.ButtonStyle.red)
    async def antiraid_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_antiraid_embed()
        await interaction.response.edit_message(embed=embed, view=HelpCategoryView(self.author))
 
    @discord.ui.button(label="🎵 Musique", style=discord.ButtonStyle.green)
    async def musique_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_musique_embed()
        await interaction.response.edit_message(embed=embed, view=HelpCategoryView(self.author))
 
 
@bot.command(name="help")
async def help_command(ctx):
    embed = build_main_help_embed()
    view = HelpMainView(ctx.author)
    await ctx.send(embed=embed, view=view)
 
 
# =========================================================
#                  MODÉRATION - SALONS
# =========================================================
 
@bot.command()
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def lock(ctx):
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send("🔒 Salon verrouillé.")
    except discord.Forbidden:
        await ctx.send("❌ Je n'ai pas la permission de verrouiller ce salon.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : `{e}`")
 
 
@bot.command()
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def unlock(ctx):
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
        await ctx.send("🔓 Salon déverrouillé.")
    except discord.Forbidden:
        await ctx.send("❌ Je n'ai pas la permission de déverrouiller ce salon.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : `{e}`")
 
 
@bot.command()
@commands.has_permissions(manage_channels=True)
async def clear(ctx):
    channel = ctx.channel
    category = channel.category
    position = channel.position
 
    new_channel = await channel.clone(reason=f"Salon vidé par {ctx.author}")
    await new_channel.edit(position=position, category=category)
    await channel.delete(reason=f"Salon vidé par {ctx.author}")
 
 
# =========================================================
#                  MODÉRATION - MEMBRES
# =========================================================
 
@bot.command()
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def mute(ctx, user_id: int, minutes: int, *, raison="Aucune raison fournie"):
    try:
        member = await ctx.guild.fetch_member(user_id)
        duree = datetime.timedelta(minutes=minutes)
        await member.timeout(duree, reason=raison)
        await ctx.send(f"🤫 **{member.name}** (`{member.id}`) a été rendu muet pour **{minutes}** minute(s).\nRaison : {raison}")
    except discord.NotFound:
        await ctx.send("❌ Cet utilisateur n'est pas sur le serveur.")
    except discord.Forbidden:
        await ctx.send("❌ Je ne peux pas rendre muet ce membre (rôle supérieur au mien).")
    except Exception as e:
        await ctx.send(f"❌ Erreur : `{e}`")
 
 
@bot.command()
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def unmute(ctx, user_id: int, *, raison="Action du staff"):
    try:
        member = await ctx.guild.fetch_member(user_id)
        await member.timeout(None, reason=raison)
        await ctx.send(f"🔊 **{member.name}** (`{member.id}`) peut de nouveau parler !")
    except discord.NotFound:
        await ctx.send("❌ Cet utilisateur n'est pas sur le serveur.")
    except discord.Forbidden:
        await ctx.send("❌ Je n'ai pas la permission de retirer le timeout de ce membre.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : `{e}`")
 
 
@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban(ctx, user_id: int, *, raison="Aucune raison fournie"):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.ban(user, reason=raison)
        await ctx.send(f"✅ **{user}** (`{user.id}`) a été banni.\nRaison : {raison}")
    except discord.NotFound:
        await ctx.send("❌ Utilisateur introuvable.")
    except discord.Forbidden:
        await ctx.send("❌ Je n'ai pas la permission de bannir cet utilisateur.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : `{e}`")
 
 
@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def unban(ctx, user_id: int, *, raison="Aucune raison fournie"):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=raison)
        await ctx.send(f"✅ **{user}** (`{user.id}`) a été débanni.\nRaison : {raison}")
    except discord.NotFound:
        await ctx.send("❌ Utilisateur introuvable ou pas banni.")
    except discord.Forbidden:
        await ctx.send("❌ Je n'ai pas la permission de débannir cet utilisateur.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : `{e}`")
 
 
@bot.command()
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
async def kick(ctx, user_id: int, *, raison="Aucune raison fournie"):
    try:
        member = await ctx.guild.fetch_member(user_id)
        await member.kick(reason=raison)
        await ctx.send(f"👢 **{member.name}** (`{member.id}`) a été exclu.\nRaison : {raison}")
    except discord.NotFound:
        await ctx.send("❌ Cet utilisateur n'est pas sur le serveur ou l'ID est incorrect.")
    except discord.Forbidden:
        await ctx.send("❌ Je n'ai pas les permissions nécessaires pour exclure ce membre.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : `{e}`")
 
 
@kick.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu n'as pas la permission d'exclure des membres.", delete_after=5)
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ Je n'ai pas la permission `Exclure des membres`.", delete_after=5)
 
 
@bot.command()
@commands.has_permissions(moderate_members=True)
async def warn(ctx, user_id: int, *, raison="Aucune raison fournie"):
    try:
        user = await bot.fetch_user(user_id)
        warns = load_warns()
 
        if str(user_id) not in warns:
            warns[str(user_id)] = []
 
        warns[str(user_id)].append({
            'raison': raison,
            'date': datetime.datetime.now().strftime("%d/%m/%Y à %H:%M"),
            'moderateur': str(ctx.author)
        })
        save_warns(warns)
 
        await ctx.send(f"⚠️ **{user}** (`{user.id}`) a reçu un avertissement.\nRaison : {raison}")
    except discord.NotFound:
        await ctx.send("❌ Utilisateur introuvable.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}")
 
 
@bot.command()
@commands.has_permissions(moderate_members=True)
async def history(ctx, user_id: int):
    try:
        user = await bot.fetch_user(user_id)
        warns = load_warns()
        user_warns = warns.get(str(user_id), [])
 
        if not user_warns:
            return await ctx.send(f"✅ **{user}** n'a aucun avertissement.")
 
        embed = discord.Embed(
            title=f"⚠️ Historique de {user}",
            color=discord.Color.orange()
        )
        for i, w in enumerate(user_warns, start=1):
            embed.add_field(
                name=f"Warn #{i} — {w['date']}",
                value=f"Raison : {w['raison']}\nPar : {w['moderateur']}",
                inline=False
            )
        await ctx.send(embed=embed)
    except discord.NotFound:
        await ctx.send("❌ Utilisateur introuvable.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : `{e}`")
 
 
@bot.command()
async def userinfo(ctx, user_id: int = None):
    try:
        if user_id is None:
            member = ctx.author
        else:
            member = await ctx.guild.fetch_member(user_id)
 
        roles = [role.mention for role in member.roles if role != ctx.guild.default_role]
        roles_texte = ", ".join(roles) if roles else "Aucun rôle"
 
        embed = discord.Embed(title=f"📋 Informations sur {member.name}", color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 Pseudo", value=member.name, inline=True)
        embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
 
        creation_date = member.created_at.strftime("%d/%m/%Y à %H:%M")
        join_date = member.joined_at.strftime("%d/%m/%Y à %H:%M")
 
        embed.add_field(name="📅 Compte créé le", value=creation_date, inline=False)
        embed.add_field(name="📥 A rejoint le serveur le", value=join_date, inline=False)
        embed.add_field(name="🎭 Rôles", value=roles_texte, inline=False)
 
        await ctx.send(embed=embed)
 
    except discord.NotFound:
        await ctx.send("❌ Utilisateur introuvable sur ce serveur. Vérifie l'ID !")
    except Exception as e:
        await ctx.send(f"❌ Erreur : `{e}`")
 
 
@bot.tree.command(name="youtube", description="Affiche ma chaine youtube")
async def youtube(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Voici le lien de ma chaine : https://www.youtube.com/@Nawkini"
    )
 
 
bot.run(os.getenv("DISCORD_TOKEN"))
 
