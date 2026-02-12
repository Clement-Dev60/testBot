import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
load_dotenv()

print('Lancement du bot...')

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print("Bot allumé !")
    # Synchroniser les commandes
    try:
        # sync
        synced = await bot.tree.sync()
        print(f"Commandes slash synchronisées : {len(synced)}")
    except Exception as e:
        print(e)

@bot.event
async def on_message(message= discord.Message):
    # Empêcher le bot d'interpréter ses messages
    if message.author.bot:
        return
    if message.content.lower() == 'bonjour':
        channel = message.channel
        author = message.author
        await author.send("Comment tu vas ?")
    if message.content.lower()== "bienvenue" :
        test_channel = bot.get_channel(1471532131602792612)
        await test_channel.send("Bienvenue")
        
@bot.tree.command(name="test", description="Tester les embeds")
async def test(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Test Title",
        description="Description de l'embed",
        color=discord.Color.blue()
    )        
    embed.add_field(name="Python", value="Apprendre ke python en s'amusant", inline=False)
    embed.add_field(name="Web", value="Apprendre le web en s'amusant")
    embed.set_footer(text="Pied de page")
    embed.set_image(url="https://www.shutterstock.com/shutterstock/photos/2547981135/display_1500/stock-photo-batman-front-position-realistic-style-in-challenging-attitude-with-dramatic-lighting-2547981135.jpg")
    
    await interaction.response.send_message(embed=embed)
   
@bot.tree.command(name="warnguy", description="Alerter une personne")
async def warnguy(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message("Alerte envoyée !")
    await member.send("Tu as reçu une alerte")
        
@bot.tree.command(name="github", description="Affiche mon github")
async def github(interaction: discord.Interaction):
    await interaction.response.send_message("Voici le lien de mon github : https://github.com/Clement-Dev60")   

bot.run(os.getenv('DISCORD_TOKEN'))