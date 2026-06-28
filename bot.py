import discord
import os
from dotenv import load_dotenv
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

@bot.event
async def on_message(message: discord.Message):


    if message.author.bot:
        return

    if message.content.lower() == "bonjour":
        await message.author.send("Comment tu vas ?")

    if message.content.lower() == "bienvenue":
        welcome_channel = bot.get_channel(1518033190428610771)
        if welcome_channel:
            await welcome_channel.send("Bienvenue sur le discord")

    await bot.process_commands(message)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Créer un ticket 📩", style=discord.ButtonStyle.blurple, custom_id="click_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        channel_name = f"ticket-{user.name}"
        ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

        await ticket_channel.send(f"Bonjour {user.mention} ! Un membre du staff va s'occuper de vous. Expliquez votre problème ici.")
        
        await interaction.response.send_message(f"Votre ticket a été créé ici : {ticket_channel.mention}", ephemeral=True)


@bot.event
async def on_ready():
    bot.add_view(TicketView())
    print(f"Connecté en tant que {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    await ctx.message.delete()
    
    embed = discord.Embed(
        title="Système de Support",
        description="Cliquez sur le bouton ci-dessous pour contacter l'équipe.",
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed, view=TicketView())
    

    print(self.bot.user.name)

@bot.event
async def on_member_join(member):
    ID_DU_SALON = 1518341039499378739  
    
    channel = bot.get_channel(ID_DU_SALON)
    
    if channel:
        await channel.send(f"🎉 Bienvenue {member.mention} sur le serveur ! Installe-toi bien !")



@bot.tree.command(name="staff", description="Demande de staff")
async def staff(interaction: discord.Interaction, member: discord.Member):
    embed = discord.Embed(
        title="Rejoignez l'équipe de T-Shirt",
        description="T-Shirt recrute du personnel. voici les conditions :",
        color=discord.Color.blue()
    )
    embed.add_field(name="Age minimum", value="pour devenir staff minimum 15ans", inline=False)
    embed.add_field(name="Activité", value="5h de vocal ou 500 messages", inline=False)
    embed.add_field(name="Clean", value="Pour finir faut être clean 0 sanction", inline=False)
    embed.add_field(name="", value="Si vous souhaitez devenir Staff, contactez une personne haut gradée.", inline=False)
    embed.set_footer(text="Cordialement")
    embed.set_image(url="https://i.pinimg.com/webp85/1200x/a8/84/a8/a884a8c972360381071e972f1a6b659e.webp")

    await interaction.response.send_message(embed=embed)

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