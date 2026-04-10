import discord  # type: ignore
import os
from dotenv import load_dotenv  # type: ignore
from discord.ext import commands, tasks  # type: ignore
from datetime import timedelta
import random
import json
from discord import app_commands  # type: ignore
from datetime import datetime
import asyncio
from discord.ui import View, Button, Modal, TextInput  # type: ignore
from blagues_api import BlaguesAPI, BlagueType  # type: ignore
from keepAlive import keep_alive  # type: ignore
import requests

keep_alive()

load_dotenv()

print("Lancement du bot...")

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
intents = discord.Intents.default()
intents.members = True
blagues = BlaguesAPI(os.getenv("BLAGUES_API_TOKEN"))


class ModifierRappelModal(Modal):
    def __init__(self, index):
        super().__init__(title=f"Modifier le rappel {index+1}")
        self.index = index
        self.input = TextInput(
            label="Nouveau message du rappel",
            style=discord.TextStyle.paragraph,
            placeholder="Tape ton nouveau rappel ici...",
            max_length=2000,
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        rappels[self.index]["message"] = self.input.value
        save_rappels(rappels)
        await interaction.response.send_message(
            f"✅ Rappel {self.index+1} mis à jour !", ephemeral=True
        )


statuses = [
    ("veille sur Gotham 🦇", discord.ActivityType.watching),
    ("protège la ville la nuit 🌃", discord.ActivityType.playing),
    ("traque le Joker 🤡", discord.ActivityType.competing),
    ("guette le Bat-Signal 🔦", discord.ActivityType.listening),
]

ZOU_MESSAGES = "zou_messages.json"

FILM = "films.json"

RAPPELS_FILE = "rappels.json"

SERIE = "series.json"


def load_series():
    with open(SERIE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_series(series):
    with open(SERIE, "w", encoding="utf-8") as f:
        json.dump(series, f, ensure_ascii=False, indent=4)


def load_films():
    with open(FILM, "r", encoding="utf-8") as f:
        return json.load(f)


def save_films(films):
    with open(FILM, "w", encoding="utf-8") as f:
        json.dump(films, f, ensure_ascii=False, indent=4)


def load_messages():
    with open(ZOU_MESSAGES, "r", encoding="utf-8") as f:
        return json.load(f)


def save_messages(messages):
    with open(ZOU_MESSAGES, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)


def load_rappels():
    try:
        with open(RAPPELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_rappels(rappels):
    with open(RAPPELS_FILE, "w", encoding="utf-8") as f:
        json.dump(rappels, f, indent=4, ensure_ascii=False)


rappels = load_rappels()

messages = load_messages()

films = load_films()

series = load_series()


@bot.event
async def on_ready():
    print("Bot allumé !")

    try:
        synced = await bot.tree.sync()
        print(f"Commandes slash synchronisées : {len(synced)}")

    except Exception as e:
        print(e)
    print(f"Nombre de messages chargés : {len(messages)}")

    try:
        blague = await blagues.count()
        print(f"Nombre de blagues api chargées : {blague.count}")
    except Exception as e:
        print(f"Erreur blagues api : {e}")

    if not change_status.is_running():
        change_status.start()

    for rappel in rappels:
        bot.loop.create_task(schedule_rappel(rappel))

    if not check_twitch.is_running():
        check_twitch.start()


@tasks.loop(seconds=5)
async def change_status():
    name, activity_type = random.choice(statuses)

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=activity_type, name=name),
    )


async def schedule_rappel(rappel):
    await bot.wait_until_ready()

    rappel_time = datetime.fromisoformat(rappel["date"])
    now = datetime.now()

    delay = (rappel_time - now).total_seconds()

    if delay <= 0:
        return

    await asyncio.sleep(delay)

    try:
        user = await bot.fetch_user(rappel["user_id"])
        creator = await bot.fetch_user(rappel["created_by"])
        await user.send(f"⏰ Rappel : {rappel['message']}")
        await creator.send(
            f"⏰ Le rappel : '{rappel['message']}', a bien été reçu par le destinataire"
        )
    except:
        pass

    global rappels
    rappels = [r for r in rappels if r != rappel]
    save_rappels(rappels)


@bot.event
async def on_message(message=discord.Message):
    # Empêcher le bot d'interpréter ses messages
    if message.author.bot:
        return


@bot.tree.command(name="blague", description="Envoyer une blague humour noir")
async def blague(interaction: discord.Interaction):
    blague = await blagues.random_categorized(BlagueType.DARK)  # type: ignore
    await interaction.response.send_message(f"{blague.joke}\n||{blague.answer}||")


@bot.tree.command(name="userinfo", description="Récupérer les infos d'un membre")
async def userinfo(interaction: discord.Interaction, member: discord.Member):
    embed = discord.Embed(title="Infos du membre", color=discord.Color.blue())
    embed.add_field(name="Nom", value=member.name)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Pseudo serveur", value=member.display_name)
    embed.add_field(name="Compte créé le", value=member.created_at)
    embed.add_field(name="A rejoint le serveur le", value=member.joined_at)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)

    await interaction.response.send_message(embed=embed)


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


@bot.tree.command(name="rappel", description="Créer un rappel avec date et heure")
@app_commands.describe(
    member="Utilisateur à qui envoyer le rappel",
    date="Format: JJ/MM/AAAA HH:MM",
    message="Message du rappel",
)
async def rappel(
    interaction: discord.Interaction, member: discord.Member, date: str, message: str
):
    created_by = interaction.user.id
    try:
        rappel_time = datetime.strptime(date, "%d/%m/%Y %H:%M")
    except ValueError:
        await interaction.response.send_message(
            "❌ Format invalide. Utilise : JJ/MM/AAAA HH:MM", ephemeral=True
        )
        return

    if rappel_time <= datetime.now():
        await interaction.response.send_message(
            "❌ La date doit être dans le futur.", ephemeral=True
        )
        return

    rappels.append(
        {
            "created_by": created_by,
            "user_id": member.id,
            "date": rappel_time.isoformat(),
            "message": message,
        }
    )

    save_rappels(rappels)

    bot.loop.create_task(schedule_rappel(rappels[-1]))

    await interaction.response.send_message(
        f"✅ Rappel enregistré pour le {date}", ephemeral=True
    )


@bot.tree.command(name="listrappels", description="Afficher et modifier vos rappels")
async def listrappels(interaction: discord.Interaction):
    user_id = interaction.user.id

    rappels_afficher = [
        (i, r) for i, r in enumerate(rappels) if r["created_by"] == user_id
    ]

    if not rappels_afficher:
        await interaction.response.send_message(
            "⚠️ Il n'y a pas de rappels", ephemeral=True
        )
        return

    message_text = "\n".join(f"{i+1}. {r['message']}" for i, r in rappels_afficher)

    view = View(timeout=None)

    for idx, rappel in rappels_afficher:
        button = Button(label=f"Modifier {idx+1}", style=discord.ButtonStyle.primary)

        async def make_callback(interaction: discord.Interaction, index=idx):
            if interaction.user.id != rappels[index]["created_by"]:
                await interaction.response.send_message(
                    "❌ Tu ne peux pas modifier ce rappel.", ephemeral=True
                )
                return

            # Ouvre un modal privé pour l'utilisateur
            modal = ModifierRappelModal(index)
            await interaction.response.send_modal(modal)

        button.callback = make_callback
        view.add_item(button)

    await interaction.response.send_message(message_text, view=view, ephemeral=True)


@bot.tree.command(name="zou", description="Envoyer une pensée positive à Zheum")
@app_commands.checks.cooldown(
    1, 3600, key=lambda i: i.user.id
)  # 1 fois toutes les heures
async def zou(interaction: discord.Interaction):
    member = interaction.guild.get_member(334307994940735500)
    author = interaction.user

    if not member:
        await interaction.response.send_message("Membre introuvable.", ephemeral=True)
        return

    compliment = random.choice(messages)

    await member.send(compliment)
    await author.send(f"Pensée positive envoyé ! {compliment}")
    await interaction.response.send_message(
        f"Pensée positive envoyé ! {compliment}", ephemeral=True
    )


@zou.error
async def zou_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏳ Attends encore {round(error.retry_after)} secondes.", ephemeral=True
        )


@bot.tree.command(name="addzou", description="Ajouter une pensée positive")
@app_commands.describe(message="La pensée positive à ajouter")
@app_commands.checks.has_permissions(administrator=True)
async def addzou(interaction: discord.Interaction, message: str):

    global messages
    if message in messages:
        await interaction.response.send_message(
            "⚠️ Ce message existe déjà.", ephemeral=True
        )
        return

    messages.append(message)
    save_messages(messages)

    await interaction.response.send_message(
        "✅ Pensée positive ajoutée avec succès !", ephemeral=True
    )


@addzou.error
async def addzou_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ Tu n'as pas la permission d'utiliser cette commande.", ephemeral=True
        )


@bot.tree.command(name="github", description="Affiche mon github")
async def github(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Voici le lien de mon github : https://github.com/Clement-Dev60"
    )


@bot.tree.command(name="koikonfé", description="Choisir entre film et série")
async def koikonfé(interaction: discord.Interaction):

    choix = random.choice(["film", "série"])

    await interaction.response.send_message(choix)


@bot.tree.command(name="film", description="Choisir un film au hasard dans la liste")
async def film(interaction: discord.Interaction):

    film = random.choice(films)

    await interaction.response.send_message(film)

    films.remove(film)
    with open("films.json", "w", encoding="utf-8") as f:
        json.dump(films, f, indent=4, ensure_ascii=False)


@film.error
async def film(interaction: discord.Interaction, error):
    if len(films) == 0:
        await interaction.response.send_message("La liste est vide", ephemeral=True)


@bot.tree.command(name="addfilm", description="Ajouter un film")
@app_commands.describe(film="Le film à ajouter")
@app_commands.checks.has_permissions(administrator=True)
async def addfilm(interaction: discord.Interaction, film: str):

    global films

    film = film.lower()
    films = [f.lower() for f in films]

    if film in films:
        await interaction.response.send_message(
            "⚠️ Ce film existe déjà.", ephemeral=True
        )
        return

    films.append(film)
    save_films(films)

    await interaction.response.send_message(
        "✅ Film ajoutée avec succès !", ephemeral=True
    )


@bot.tree.command(name="removefilm", description="Retirer un film")
@app_commands.describe(film="Le film à retirer")
@app_commands.checks.has_permissions(administrator=True)
async def removefilm(interaction: discord.Interaction, film: str):
    global films

    film = film.lower()
    films = [f.lower() for f in films]

    if not film in films:
        await interaction.response.send_message(
            "⚠️ Ce film n'est pas dans la liste.", ephemeral=True
        )
        return
    films.remove(film)
    save_films(films)
    await interaction.response.send_message(
        "✅ Film retiré avec succès !", ephemeral=True
    )


@bot.tree.command(name="listfilm", description="Afficher la liste de tous les films")
async def listfilm(interaction: discord.Interaction):
    global films
    if not films:
        await interaction.response.send_message("⚠️ La liste est vide", ephemeral=True)
        return

    listfilm = ""
    for film in films:
        listfilm += f"- {film}\n"

    await interaction.response.send_message(listfilm)


@bot.tree.command(name="serie", description="Choisir une série au hasard dans la liste")
async def serie(interaction: discord.Interaction):

    serie = random.choice(series)

    await interaction.response.send_message(serie)

    series.remove(serie)
    with open("series.json", "w", encoding="utf-8") as f:
        json.dump(series, f, indent=4, ensure_ascii=False)


@serie.error
async def serie(interaction: discord.Interaction, error):
    if len(series) == 0:
        await interaction.response.send_message("La liste est vide", ephemeral=True)


@bot.tree.command(name="addserie", description="Ajouter une série")
@app_commands.describe(serie="La série à ajouter")
@app_commands.checks.has_permissions(administrator=True)
async def addserie(interaction: discord.Interaction, serie: str):

    global series
    if serie in series:
        await interaction.response.send_message(
            "⚠️ Cette série existe déjà.", ephemeral=True
        )
        return

    series.append(serie)
    save_series(series)

    await interaction.response.send_message(
        "✅ Série ajoutée avec succès !", ephemeral=True
    )


@bot.tree.command(
    name="listserie", description="Afficher la liste de toutes les séries"
)
async def listserie(interaction: discord.Interaction):
    global series
    if not series:
        await interaction.response.send_message("⚠️ La liste est vide", ephemeral=True)
        return

    listserie = ""
    for serie in series:
        listserie += f"- {serie}\n"

    await interaction.response.send_message(listserie)


# --- Twitch ---


def get_twitch_token():
    r = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": os.getenv("TWITCH_CLIENT_ID"),
            "client_secret": os.getenv("TWITCH_CLIENT_SECRET"),
            "grant_type": "client_credentials",
        },
    )
    return r.json()["access_token"]


def is_live(token):
    headers = {
        "Client-ID": os.getenv("TWITCH_CLIENT_ID"),
        "Authorization": f"Bearer {token}",
    }
    streamer = os.getenv("TWITCH_STREAMER")
    r = requests.get(
        f"https://api.twitch.tv/helix/streams?user_login={streamer}", headers=headers
    )
    data = r.json().get("data", [])
    return data[0] if data else None


twitch_notified = False


@tasks.loop(seconds=60)
async def check_twitch():
    global twitch_notified

    token = get_twitch_token()
    stream = is_live(token)
    channel = bot.get_channel(int(os.getenv("TWITCH_CHANNEL_ID")))

    if stream and not twitch_notified:
        streamer = os.getenv("TWITCH_STREAMER")
        embed = discord.Embed(
            title=f"🔴 {streamer} est en live !",
            description=stream["title"],
            color=discord.Color.purple(),
            url=f"https://twitch.tv/{streamer}",
        )
        embed.add_field(name="Jeu", value=stream.get("game_name", "Inconnu"))
        embed.set_footer(text="Twitch Live")
        await channel.send("@everyone", embed=embed)
        twitch_notified = True

    elif not stream:
        streamer = os.getenv("TWITCH_STREAMER")
        embed = discord.Embed(
            title=f"🔴 {streamer} n'est plus en live !",
            color=discord.Color.purple(),
        )
        await channel.send("@everyone", embed=embed)
        twitch_notified = False


bot.run(os.getenv("DISCORD_TOKEN"))
