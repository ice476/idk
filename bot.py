import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
load_dotenv()

print("Lancement du bot...")
bot = commands.Bot(command_prefix=["!", "+"], intents=discord.Intents.all())

@bot.event
async def on_ready():
    print("Bot allumé !")
    # Synchroniser les commandes
    try:
        #sync
        synced = await bot.tree.sync()
        print(f"Commandes slash synchronisées : {len(synced)}")
    except Exception as e:
            print(e)

@bot.event
async def on_message(message: discord.Message):

    # empêcher le bot de se déclencher lui-même
    if message.author.bot:
        return

    if message.content.lower() == "bonjour":
        await message.author.send("Comment tu vas ?")

    if message.content.lower() == "bienvenue":
        welcome_channel = bot.get_channel(1518033190428610771)
        if welcome_channel:
            await welcome_channel.send("Bienvenue sur le discord")

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
async def warnguy(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message("Ban envoyé !")
    await member.ban(reason="fils de pute")
    await member.send("Tu as été banni") 

@bot.tree.command(name="youtube", description="Affiche ma chaine youtube")
async def youtube(interaction: discord.Interaction):
    await interaction.response.send_message("Voici le lien de ma chaine : https://www.youtube.com/@Nawkini")

print("TOKEN =", os.getenv("DISCORD_TOKEN"))

bot.run(os.getenv("DISCORD_TOKEN"))