import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
load_dotenv()

print("Lancement du bot...")
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

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

@bot.tree.command(name="test", description="Tester les embeds")
async def test(interaction: discord.Interaction, member: discord.Member):
    embed = discord.Embed(
        title="Test Title",
        description="Description de l'embed",
        color=discord.Color.blue()
    )
    embed.add_field(name="Python", value="embed add field python value", inline=False)
    embed.add_field(name="Wev", value="embed add field wev value", inline=False)
    embed.set_footer(text="Pied de page")
    embed.set_image(url="https://i.pinimg.com/236x/3a/80/77/3a80778feac905d3772bc16e23b34f8a.jpg")

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

bot.run(os.getenv('DISCORD_TOKEN'))