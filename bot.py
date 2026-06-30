import discord
import os
import time
import yt_dlp
import asyncio
import datetime
from dotenv import load_dotenv
from discord.ext import tasks, commands

load_dotenv()

print("Lancement du bot...")


intents = discord.Intents.default()
intents.message_content = True  
intents.voice_states = True    
intents.members = True  

bot = commands.Bot(command_prefix=["!", "+"], intents=intents, help_command=None)

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

cookies_content = os.environ.get('YOUTUBE_COOKIES')
if cookies_content:
    with open('cookies.txt', 'w') as f:
        f.write(cookies_content)

# --- VUES POUR LES TICKETS ---

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


# --- EFFETS ET LOOP ---

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


# --- UNIFICATION DU ON_READY ---

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user.name}")
    await bot.add_cog(MusicBot(bot))

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

Que tu sois casual ou tryhard, tu as ta place ici ! Rejoins-nous et fais partie de l’aventure T shirt dès maintenant Au 5 invites au rôles !! 

https://discord.gg/PM6Zsca8xe

Si vous aimez le serveur T shirt , n’hésitez pas à en parler autour de vous ou à inviter vos amis
Plus on est nombreux, plus l’ambiance sera folle @everyone"""

            await channel_pub.send(content=texte_pub)
            print("Message de pub envoyé avec succès !")


# --- AUTRES ÉVÉNEMENTS ---

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



class MusicBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []  

    @commands.command(name='play')
    async def play(self, ctx, *, search: str):
        if not ctx.author.voice:
            return await ctx.send("Tu dois être dans un salon vocal pour faire ça !")

        voice_channel = ctx.author.voice.channel

        if not ctx.voice_client:
            await voice_channel.connect()
        
        await ctx.send(f"🔍 Recherche de `{search}`...")

        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ytdl:
            try:
                info = ytdl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
                url = info['url']
                title = info['title']
            except Exception as e:
                print(f"Erreur yt-dlp: {e}")
                import traceback
                traceback.print_exc()
                return await ctx.send("Impossible de trouver ou de lire cette musique.")

        self.queue.append({'url': url, 'title': title})
        await ctx.send(f"🎵 Ajouté à la file : **{title}**")

        if not ctx.voice_client.is_playing():
            self.play_next(ctx)

    def play_next(self, ctx):
        if len(self.queue) > 0:
            song = self.queue.pop(0)
            url = song['url']
            title = song['title']

            source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
            ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.check_queue(ctx), self.bot.loop))
            
            self.bot.loop.create_task(ctx.send(f"🎶 En train de jouer : **{title}**"))

    async def check_queue(self, ctx):
        self.play_next(ctx)

    @commands.command(name='skip')
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()  
            await ctx.send("⏭️ Musique passée !")
        else:
            await ctx.send("Aucune musique n'est en cours de lecture.")

    @commands.command(name='stop')
    async def stop(self, ctx):
        self.queue.clear()
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("🛑 Musique arrêtée et déconnexion.")
        else:
            await ctx.send("Je ne suis pas connecté à un salon vocal.")

    @commands.command(name='queue')
    async def queue_list(self, ctx):
        if len(self.queue) == 0:
            return await ctx.send("La file d'attente est vide.")

        embed = discord.Embed(title="📋 File d'attente", color=discord.Color.blue())
        description = ""
        for i, song in enumerate(self.queue, start=1):
            description += f"{i}. **{song['title']}**\n"
        
        embed.description = description
        await ctx.send(embed=embed)

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

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="Toutes les commandes", description="⠀", color=discord.Color.blue()
    )
    embed.add_field(name="Modération", value="`+ban`, `+kick`, `+mute`, `+unmute`, `+warn`, `+clear`, `+say`", inline=False)
    embed.add_field(name="Musique", value="`+play`, `+skip`, `+stop`, `+queue`", inline=False)
    embed.add_field(name="Slash Commands", value="`/youtube`", inline=False)
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(manage_channels=True)
async def clear(ctx):
    channel = ctx.channel
    category = channel.category
    position = channel.position

    new_channel = await channel.clone(reason=f"Salon vidé par {ctx.author}")
    await new_channel.edit(position=position, category=category)
    await channel.delete(reason=f"Salon vidé par {ctx.author}")

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
        await ctx.send(f"⚠️ **{user}** (`{user.id}`) a reçu un avertissement.\nRaison : {raison}")
    except discord.NotFound:
        await ctx.send("❌ Utilisateur introuvable.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}")

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


print("TOKEN =", os.getenv("DISCORD_TOKEN"))
bot.run(os.getenv("DISCORD_TOKEN"))