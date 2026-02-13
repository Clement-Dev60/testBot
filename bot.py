import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
from datetime import timedelta
import random

load_dotenv()

print("Lancement du bot...")

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

blagues = [
    "Je tiens beaucoup à ma montre, c'est mon grand-père qui me l'a vendue sur son lit de mort.",
    "Consolation de cul-de-jatte : 'Je ne partirai pas les pieds devant.'",
    "Pour vivre heureuse et toujours semblable à elle-même, une jolie femme doit mourir jeune, et une honnête femme mourir âgée.",
    "Il ne faut jamais gifler un sourd. Il perd la moitié du plaisir. Il sent la gifle mais il ne l'entend pas.",
    "Une femme laide, c’est le trésor d’une maison : cela évite bien des préoccupations.",
    "Je veux être incinéré et je veux que 10% soit versé à mon imprésario, comme il est écrit dans mon contrat.",
    "Les catastrophes, ce sont les fêtes des pauvres.",
    "Il vaut mieux être cocu que veuf : il y a moins de formalités !",
    "Il n'y a que les sots et les morts qui ne changent pas d'opinion.",
    "La peur de tomber : voilà ce qui fait grimacer les pendus.",
    "C'est très reposant d'être sourd. On ne vous dit que l'essentiel.",
    "Tout arrive à qui sait attendre. La mort, par exemple.",
    "Apprendre à mourir ! Et pourquoi donc ? On y réussit très bien la première fois !",
    "L'agréable perspective du veuvage soutient le courage de beaucoup d'épouses.",
    "Un incinéré ne peut pas se retourner dans sa tombe.",
    "Je tiens beaucoup à ma montre, c'est mon grand-père qui me l'a vendue sur son lit de mort.",
    "Si c'est les meilleurs qui partent les premiers, que penser alors des éjaculateurs précoces ?",
    "Le mot infarctus est le seul mot irrégulier de la langue française. On dit : 'un infarctus, des obsèques'.",
    "Autopsie : elle permet aux autres de découvrir ce qu'on n'a jamais pu voir en soi-même.",
    "Les après-guerre sont faites pour enterrer les morts et trouver quelques belles phrases.",
    "Jésus, portant sa croix dans la montée du Golgotha, aurait souhaité avoir un diable pour l'aider.",
    "Il n'y a plus, de nos jours, que deux sortes de piétons : les rapides et les morts.",
    "S'il n'y avait pas la Science, combien d'entre nous pourraient profiter de leur cancer pendant plus de cinq ans ?",
    "Je préfère l'incinération à l'enterrement et les deux à un week-end avec ma femme.",
    "Cécité : point de vue.",
    "Il vaut mieux vivre riche que mourir riche.",
    "Lorsque les trains déraillent, ce qui me fait de la peine, ce sont les morts de première classe.",
    "Que voudriez-vous faire graver sur votre tombe ? Quelque chose de court et de simple. Quoi ? Je reviens dans cinq minutes.",
    "Il n’y a pas de bonheur parfait ! dit l’homme quand sa belle-mère mourut et qu’on lui présenta la note des pompes funèbres.",
    "Un professeur de langues mortes s’est suicidé pour parler les langues qu’il connaissait.",
    "Un journal coupé en morceaux n'intéresse aucune femme, alors qu'une femme coupée en morceaux intéresse tous les journaux.",
    "Un borgne, c'est un infirme qui n'a droit qu'à un demi-chien.",
    "Il ne faut pas tuer son oncle, dans aucune circonstance, même pour en hériter.",
    "A ma mort, je souhaite léguer mon corps à la science fiction.",
    "Les secrets, c’est comme les cadavres…\nÇa finit toujours par remonter à la surface.",
]


@bot.event
async def on_ready():
    print("Bot allumé !")
    # Synchroniser les commandes
    try:
        # sync
        synced = await bot.tree.sync()
        print(f"Commandes slash synchronisées : {len(synced)}")
        print(f"Nombres de blagues disponibles : {len(blagues)}")
    except Exception as e:
        print(e)


@bot.event
async def on_message(message=discord.Message):
    # Empêcher le bot d'interpréter ses messages
    if message.author.bot:
        return
    if message.content.lower() == "bonjour":
        channel = message.channel
        author = message.author
        await channel.send("Comment tu vas ?")
        await author.send("Comment tu vas ?")
    if message.content.lower() == "bienvenue":
        test_channel = bot.get_channel(1471532131602792612)
        await test_channel.send("Bienvenue")
    await bot.process_commands(message)


@bot.command()
async def blague(ctx):
    joke = random.choice(blagues)
    await ctx.send(joke)


@bot.command()
async def raiser(ctx):
    guild = ctx.guild

    member_id = 1117465814174543902

    member = guild.get_member(member_id)

    if not member:
        await ctx.send("Membre introuvable.")
        return

    try:
        duration = timedelta(seconds=69)
        await member.timeout(duration, reason="Cheh")
        await ctx.send(f"{member.mention} a été timeout 69 secondes")
    except Exception as e:
        await ctx.send(f"Erreur : {e}")


@bot.tree.command(name="test", description="Tester les embeds")
async def test(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Test Title",
        description="Description de l'embed",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="Python", value="Apprendre ke python en s'amusant", inline=False
    )
    embed.add_field(name="Web", value="Apprendre le web en s'amusant")
    embed.set_footer(text="Pied de page")
    embed.set_image(
        url="https://www.shutterstock.com/shutterstock/photos/2547981135/display_1500/stock-photo-batman-front-position-realistic-style-in-challenging-attitude-with-dramatic-lighting-2547981135.jpg"
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="warnguy", description="Alerter une personne")
async def warnguy(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message("Alerte envoyée !")
    await member.send("Tu as reçu une alerte")


@bot.tree.command(name="github", description="Affiche mon github")
async def github(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Voici le lien de mon github : https://github.com/Clement-Dev60"
    )


bot.run(os.getenv("DISCORD_TOKEN"))
