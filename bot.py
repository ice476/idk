import discord
import os
import time
from dotenv import load_dotenv
from discord.ext import tasks, commands

load_dotenv()

print("Lancement du bot...")
bot = commands.Bot(command_prefix=["!", "+"], intents=discord.Intents.all(), help_command=None)

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
    ID_SALON_STAFF = 1518366776952623357
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
    print(f"Bot connecté sous le nom de : {bot.user.name}")

    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name="T-shirt",  
        
        details="Good Vibes", 
        
        state="Dev bi 9vibe", 
        
        timestamps={
            "end": int(time.time()) + 3600  
        },
        
        party={
            "size": [4, 5] 
        },
        
        assets={
            "large_image": "image_principale",  
            "large_text": "T-shirt Communauté",  
            "small_image": "petit_logo",        
            "small_text": "Vibe"                
        }
    )

    await bot.change_presence(status=discord.Status.online, activity=activity)

@bot.event
async def on_ready():
    print(f"Bot connecté sous le nom de : {bot.user.name}")
    

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
                color=discord.Color.blue()
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


# --- AUTRES ÉVÉNEMENTS (Unifiés aussi pour le join) ---

@bot.event
async def on_member_join(member):

    ID_DU_SALON = 1518341039499378739  
    channel = bot.get_channel(ID_DU_SALON)
    if channel:
        await channel.send(f"Bienvenue {member.mention} sur le serveur ! Viens discuter dans le chat !")
        

    ID_SALON_STAFF = 1518366776952623357
    channel_staff = bot.get_channel(ID_SALON_STAFF)
    if channel_staff:
        await channel_staff.send(f"{member.mention}", delete_after=1)


@bot.event
async def on_member_update(before, after):
    if before.premium_since_current_amount < after.premium_since_current_amount:
        ID_SALON_BOOST = 1519027720367898835
        channel = bot.get_channel(ID_SALON_BOOST)
        
        if channel:
            nb_boosts_membre = after.premium_since_current_amount
            embed = discord.Embed(
                title="Un énorme MERCI !",
                description=f"{after.mention}\n\n"
                            f"Tu as donné **{nb_boosts_membre}** boost(s) à ce serveur. "
                            f"Merci pour ton soutien ! ",
                color=discord.Color.fuchsia()
            )
            embed.set_thumbnail(url=after.display_avatar.url)
            await channel.send(embed=embed)


# --- COMMANDES PREFIX & SLASH ---

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Toutes les commandes", description="⠀", color=discord.Color.blue())
    embed.add_field(name="⠀", value="/youtube", inline=False)
    embed.add_field(name="⠀", value="/warnguy", inline=False)
    embed.add_field(name="⠀", value="+ban", inline=False)
    embed.add_field(name="⠀", value="+clear", inline=False)
    embed.add_field(name="⠀", value="+warn", inline=False)
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
@commands.has_permissions(moderate_members=True)
async def warn(ctx, user_id: int, *, raison="Aucune raison fournie"):
    try:
        user = await bot.fetch_user(user_id)

        await ctx.send(
            f"⚠️ **{user}** (`{user.id}`) a reçu un avertissement.\n"
            f"Raison : {raison}"
        )

    except discord.NotFound:
        await ctx.send("❌ Utilisateur introuvable.")

    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}")


@bot.tree.command(name="youtube", description="Affiche ma chaine youtube")
async def youtube(interaction: discord.Interaction):
    await interaction.response.send_message("Voici le lien de ma chaine : https://www.youtube.com/@Nawkini")


print("TOKEN =", os.getenv("DISCORD_TOKEN"))
bot.run(os.getenv("DISCORD_TOKEN"))