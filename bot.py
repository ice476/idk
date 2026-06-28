import discord
import os
from dotenv import load_dotenv
from discord.ext import tasks
from discord.ext import commands
load_dotenv()

print("Lancement du bot...")
bot = commands.Bot(command_prefix=["!", "+"], intents=discord.Intents.all(), help_command=None)

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="Toutes les commands",
        description="⠀",
        color=discord.Color.blue())

    embed.add_field(name="⠀", value="/youtube", inline=False)
    embed.add_field(name="⠀", value="/warnguy", inline=False)
    embed.add_field(name="⠀", value="/banguy", inline=False)
    embed.add_field(name="⠀", value="/staff", inline=False)

    await ctx.send(embed=embed)


@bot.event
async def on_ready():
    print("Bot allumé !")
    
    try:
        #sync
        synced = await bot.tree.sync()
        print(f"Commandes slash synchronisées : {len(synced)}")
    except Exception as e:
            print(e)

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # timeout=None pour que le bouton reste actif indéfiniment

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Supprime le salon du ticket
        await interaction.response.send_message("Fermeture du ticket...", ephemeral=True)
        await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Créer un ticket", style=discord.ButtonStyle.green, custom_id="create_ticket")
    async def ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user

        # Configuration des permissions pour le salon privé
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False), # Personne ne voit
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True), # Sauf le membre
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True) # Et le bot
        }

        # Création du salon textuel personnalisé
        channel = await guild.create_text_channel(
            name=f"ticket-{member.name}", 
            overwrites=overwrites,
            reason=f"Ticket ouvert par {member.name}"
        )

        # Message de confirmation éphémère (que seul le membre voit)
        await interaction.response.send_message(f"Votre ticket a été créé ici : {channel.mention}", ephemeral=True)

        # Message d'accueil à l'intérieur du ticket avec le bouton de fermeture
        embed = discord.Embed(
            title="Ticket Ouvert",
            description=f"Bonjour {member.mention},\nUn membre de l'équipe va s'occuper de vous. Cliquez sur le bouton ci-dessous pour fermer ce ticket si votre problème est résolu.",
            color=discord.Color.green()
        )
        await channel.send(embed=embed, view=TicketCloseView())


# --- COMMANDE POUR ENVOYER LE SYSTÈME DE TICKET ---
@bot.tree.command(name="setup_ticket", description="Installe le système de ticket dans ce salon")
@commands.has_permissions(administrator=True)
async def setup_ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Besoin d'aide ?",
        description="Cliquez sur le bouton ci-dessous pour ouvrir un ticket de support privé.",
        color=discord.Color.blue()
    )
    # Envoie l'embed avec le bouton de création
    await interaction.response.send_message(embed=embed, view=TicketView())

@bot.event
async def on_member_join(member):
    ID_DU_SALON = 1518341039499378739  
    
    channel = bot.get_channel(ID_DU_SALON)
    
    if channel:
        await channel.send(f"Bienvenue {member.mention} sur le serveur ! Viens discuter dans le chat !")



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

@bot.event
async def on_ready():
    if not message_recrutement_mensuel.is_running():
        message_recrutement_mensuel.start()
    print(f"Connecté en tant que {bot.user}")


@bot.event
async def on_member_join(member):
    ID_SALON_STAFF = 1518366776952623357
    channel = bot.get_channel(ID_SALON_STAFF)
    
    if channel:
        await channel.send(
            f"{member.mention}",
            delete_after=1
        )


@bot.tree.command(name="warnguy", description="Alert une personne")
async def warnguy(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message("Alerte envoyé !")
    await member.send("Tu as reçu une alerte")

@bot.tree.command(name="banguy", description="Bannir une personne")
async def banguy(interaction: discord.Interaction, member: discord.Member, reason: str):
    await interaction.response.send_message("Ban envoyé !")
    await member.send(f"Tu as été banni\nRaison : {reason}")
    await member.send("Tu as été banni") 
    await member.ban(reason=reason)

@bot.tree.command(name="youtube", description="Affiche ma chaine youtube")
async def youtube(interaction: discord.Interaction):
    await interaction.response.send_message("Voici le lien de ma chaine : https://www.youtube.com/@Nawkini")

print("TOKEN =", os.getenv("DISCORD_TOKEN"))

bot.run(os.getenv("DISCORD_TOKEN"))