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
from groq import Groq  # type: ignore

keep_alive()

load_dotenv()

print("Lancement du bot...")

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
intents = discord.Intents.default()
intents.members = True
blagues = BlaguesAPI(os.getenv("BLAGUES_API_TOKEN"))

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

ALFRED_PROMPT = """Tu es Alfred Pennyworth, le majordome dévoué et fidèle de Zheum, ton unique maître et aussi batman.
Tu es distingué, d'une politesse irréprochable, légèrement sarcastique mais toujours bienveillant.
Tu t'exprimes avec élégance et raffinement, en utilisant un vocabulaire soutenu.
Tu fais parfois de discrètes références à Gotham ou à la Batcave.
IMPORTANT : Dans cet univers, ton maître s'appelle Zheum. Tu ne mentionnes JAMAIS Bruce Wayne. Si on te parle de Bruce Wayne, tu réponds que tu ne connais pas ce nom.
Tu réponds toujours en français."""


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

JEU = "jeux.json"

RAPPELS_FILE = "rappels.json"

SERIE = "series.json"

FREE_GAMES_FILE = "free_games.json"


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


def load_jeux():
    with open(JEU, "r", encoding="utf-8") as f:
        return json.load(f)


def save_jeux(jeux):
    with open(JEU, "w", encoding="utf-8") as f:
        json.dump(jeux, f, ensure_ascii=False, indent=4)


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

jeux = load_jeux()

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
        print("[TWITCH] Tâche check_twitch démarrée")
    else:
        print("[TWITCH] Tâche check_twitch déjà en cours")

    if not check_free_games.is_running():
        check_free_games.start()
        print("[FREE GAMES] Tâche démarrée")


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

        image_path = rappel.get("image_path")

        if image_path and os.path.exists(image_path):
            file = discord.File(image_path)
            await user.send(f"⏰ Rappel : {rappel['message']}", file=file)
            os.remove(image_path)
        else:
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
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if bot.user.mentioned_in(message):
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        username = message.author.name

        if username == "winoka_":
            civilite = "Tu appelles cet utilisateur '𝒲𝒾𝓃❁𝓀𝒶'."
        elif username == "zheum":
            civilite = "Tu parles à Zheum, ton maître. Tu le traites avec un respect particulier, comme Alfred traite Bruce Wayne."
        else:
            civilite = "Tu appelles cet utilisateur 'Monsieur'."

        prompt_dynamique = ALFRED_PROMPT + f"\n{civilite}"

        if not content:
            await message.reply("Vous m'avez sonné, Monsieur ?")
            return

        async with message.channel.typing():
            try:
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": prompt_dynamique},
                        {"role": "user", "content": content},
                    ],
                )
                await message.reply(response.choices[0].message.content)
            except Exception as e:
                await message.reply(f"❌ Erreur : {e}")

    await bot.process_commands(message)


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
    image="Image à joindre au rappel (optionnel)",
)
async def rappel(
    interaction: discord.Interaction,
    member: discord.Member,
    date: str,
    message: str,
    image: discord.Attachment = None,
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

    image_path = None

    if image:
        os.makedirs("rappels_images", exist_ok=True)
        extension = image.filename.split(".")[-1]
        filename = (
            f"{interaction.user.id}_{int(datetime.now().timestamp())}.{extension}"
        )
        image_path = f"rappels_images/{filename}"

        image_data = requests.get(image.url).content
        with open(image_path, "wb") as f:
            f.write(image_data)

    rappels.append(
        {
            "created_by": created_by,
            "user_id": member.id,
            "date": rappel_time.isoformat(),
            "message": message,
            "image_path": image_path,
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


@bot.tree.command(
    name="listzou",
    description="Afficher la liste de toutes les phrases dans le fichier zou",
)
async def listzou(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    member_id = 1105940410725060739

    wino = guild.get_member(member_id)

    if wino is None:
        await interaction.followup.send("⚠️ Membre introuvable.")
        return

    global messages
    if not messages:
        await interaction.followup.send("⚠️ La liste est vide.")
        return

    liste = "\n".join(f"- {zou}" for zou in messages)

    try:
        for i in range(0, len(liste), 1900):
            await wino.send(liste[i : i + 1900])

        await interaction.followup.send("✅ Liste envoyée en MP")

    except discord.Forbidden:
        await interaction.followup.send(
            "⚠️ Impossible d'envoyer un MP à cet utilisateur."
        )

    except Exception as e:
        await interaction.followup.send(f"Erreur : {e}")


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


@bot.tree.command(name="jeu", description="Choisir un jeu au hasard dans la liste")
async def jeu(interaction: discord.Interaction):
    if not jeux:
        await interaction.response.send_message("⚠️ La liste est vide", ephemeral=True)
        return

    jeu = random.choice(jeux)

    await interaction.response.send_message(jeu)


@jeu.error
async def jeu_error(interaction: discord.Interaction, error):
    await interaction.response.send_message(f"❌ Erreur : {error}", ephemeral=True)


@bot.tree.command(name="addjeu", description="Ajouter un jeu")
@app_commands.describe(jeu="Le jeu à ajouter")
@app_commands.checks.has_permissions(administrator=True)
async def addjeu(interaction: discord.Interaction, jeu: str):

    global jeux

    jeu = jeu.lower()
    jeux = [f.lower() for f in jeux]

    if jeu in jeux:
        await interaction.response.send_message(
            "⚠️ Ce jeu existe déjà.", ephemeral=True
        )
        return

    jeux.append(jeu)
    save_jeux(jeux)

    await interaction.response.send_message(
        "✅ Jeu ajouté avec succès !", ephemeral=True
    )


@bot.tree.command(name="removejeu", description="Retirer un jeu")
@app_commands.describe(jeu="Le jeu à retirer")
@app_commands.checks.has_permissions(administrator=True)
async def removejeu(interaction: discord.Interaction, jeu: str):
    global jeux

    jeu = jeu.lower()
    jeux = [f.lower() for f in jeux]

    if not jeu in jeux:
        await interaction.response.send_message(
            "⚠️ Ce jeu n'est pas dans la liste.", ephemeral=True
        )
        return
    jeux.remove(jeu)
    save_jeux(jeux)
    await interaction.response.send_message(
        "✅ Jeu retiré avec succès !", ephemeral=True
    )


@bot.tree.command(name="listjeu", description="Afficher la liste de tous les jeux")
async def listjeu(interaction: discord.Interaction):
    global jeux
    if not jeux:
        await interaction.response.send_message("⚠️ La liste est vide", ephemeral=True)
        return

    listjeu = ""
    for jeu in jeux:
        listjeu += f"- {jeu}\n"

    await interaction.response.send_message(listjeu)


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
twitch_offline_notified = False
twitch_live_message = None
twitch_offline_message = None


async def delete_twitch_messages():
    await asyncio.sleep(1200)

    global twitch_live_message, twitch_offline_message

    for msg in [twitch_live_message, twitch_offline_message]:
        if msg is not None:
            try:
                await msg.delete()
            except discord.NotFound:
                pass

    twitch_live_message = None
    twitch_offline_message = None


last_live_state = None


@tasks.loop(seconds=30)
async def check_twitch():
    global last_live_state
    global twitch_live_message, twitch_offline_message

    token = get_twitch_token()
    stream = is_live(token)

    is_currently_live = stream is not None

    print(f"[TWITCH] is_live={is_currently_live} | last_state={last_live_state}")

    channel = bot.get_channel(int(os.getenv("TWITCH_CHANNEL_ID")))
    print(f"[TWITCH] channel={channel}")

    if last_live_state is None:
        last_live_state = is_currently_live
        print(f"[TWITCH] Initialisation -> last_state={last_live_state}, pas de notif")
        return

    streamer = os.getenv("TWITCH_STREAMER")

    if is_currently_live and not last_live_state:
        print("[TWITCH] -> Passage en LIVE détecté, envoi notif")

        embed = discord.Embed(
            title=f"🔴 {streamer} est en live !",
            description=stream["title"],
            color=discord.Color.purple(),
            url=f"https://twitch.tv/{streamer}",
        )

        embed.add_field(name="Jeu", value=stream.get("game_name", "Inconnu"))

        embed.set_footer(text="Twitch Live")

        twitch_live_message = await channel.send("@everyone", embed=embed)

    elif not is_currently_live and last_live_state:
        print("[TWITCH] -> Passage HORS LIGNE détecté, envoi notif")

        embed = discord.Embed(
            title=f"⚫ {streamer} n'est plus en live !",
            color=discord.Color.red(),
        )

        twitch_offline_message = await channel.send("@everyone", embed=embed)

        asyncio.create_task(delete_twitch_messages())

    last_live_state = is_currently_live
    print(f"[TWITCH] last_state mis à jour -> {last_live_state}")


# --- Jeux gratuits ---

FREE_GAMES_FILE = "free_games.json"


def load_free_games():
    try:
        with open(FREE_GAMES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_free_games(games):
    with open(FREE_GAMES_FILE, "w", encoding="utf-8") as f:
        json.dump(games, f, ensure_ascii=False, indent=4)


def get_epic_free_games():
    try:
        r = requests.get(
            "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions",
            params={"locale": "fr", "country": "FR", "allowCountries": "FR"},
        )
        games = r.json()["data"]["Catalog"]["searchStore"]["elements"]
        free = []
        for game in games:
            promotions = game.get("promotions")
            if not promotions:
                continue
            offers = promotions.get("promotionalOffers", [])
            for offer_group in offers:
                for offer in offer_group.get("promotionalOffers", []):
                    if offer["discountSetting"]["discountPercentage"] == 0:
                        end_date = offer.get("endDate", None)
                        free.append(
                            {
                                "title": game["title"],
                                "store": "Epic Games",
                                "url": f"https://store.epicgames.com/fr/p/{game.get('productSlug', '')}",
                                "image": (
                                    game["keyImages"][0]["url"]
                                    if game.get("keyImages")
                                    else None
                                ),
                                "end_date": end_date,
                            }
                        )
        return free
    except Exception as e:
        print(f"[FREE GAMES] Erreur Epic : {e}")
        return []


def get_steam_free_games():
    try:
        r = requests.get(
            "https://api.isthereanydeal.com/deals/v2",
            params={
                "key": os.getenv("ITAD_API_KEY"),
                "country": "FR",
                "limit": 50,
            },
            json={"filter": {"cut": {"min": 100, "max": 100}, "shops": [61]}},
        )
        data = r.json()
        free = []
        for game in data.get("list", []):
            if game["deal"]["cut"] == 100:
                expiry = game["deal"].get("expiry", None)
                free.append(
                    {
                        "title": game["title"],
                        "store": "Steam",
                        "url": game["deal"]["url"],
                        "image": game["assets"].get("banner300"),
                        "end_date": expiry,
                    }
                )
        return free
    except Exception as e:
        print(f"[FREE GAMES] Erreur Steam/ITAD : {e}")
        return []


def format_end_date(end_date):
    if not end_date:
        return "Durée inconnue"
    try:
        dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        return f"Jusqu'au {dt.strftime('%d/%m/%Y à %Hh%M')}"
    except:
        return "Durée inconnue"


notified_games = load_free_games()


@tasks.loop(hours=1)
async def check_free_games():
    global notified_games

    channel = bot.get_channel(int(os.getenv("FREE_GAMES_CHANNEL_ID")))
    if not channel:
        print("[FREE GAMES] Salon introuvable")
        return

    epic_games = get_epic_free_games()
    steam_games = get_steam_free_games()

    current_titles = [g["title"] for g in epic_games + steam_games]
    notified_games = [g for g in notified_games if g in current_titles]
    save_free_games(notified_games)

    # Filtrer les nouveaux jeux non notifiés
    new_epic = [g for g in epic_games if g["title"] not in notified_games]
    new_steam = [g for g in steam_games if g["title"] not in notified_games]

    print(f"[FREE GAMES] notified_games={notified_games}")
    print(f"[FREE GAMES] new_epic={[g['title'] for g in new_epic]}")
    print(f"[FREE GAMES] new_steam={[g['title'] for g in new_steam]}")

    # Ping Epic Games (un seul embed)
    if new_epic:
        embed = discord.Embed(
            title="🎮 Jeux gratuits sur Epic Games !",
            color=discord.Color.dark_blue(),
        )
        for game in new_epic:
            embed.add_field(
                name=game["title"],
                value=f"[Récupérer]({game['url']}) • {format_end_date(game['end_date'])}",
                inline=False,
            )
            if game["image"] and len(new_epic) == 1:
                embed.set_image(url=game["image"])
        embed.set_footer(text="Epic Games Store")
        await channel.send("@everyone", embed=embed)

        for game in new_epic:
            notified_games.append(game["title"])
        save_free_games(notified_games)

    # Ping Steam (un seul embed)
    if new_steam:
        embed = discord.Embed(
            title="🎮 Jeux gratuits sur Steam !",
            color=discord.Color.blue(),
        )
        for game in new_steam:
            embed.add_field(
                name=game["title"],
                value=f"[Récupérer]({game['url']}) • {format_end_date(game['end_date'])}",
                inline=False,
            )
            if game["image"] and len(new_steam) == 1:
                embed.set_image(url=game["image"])
        embed.set_footer(text="Steam")
        await channel.send("@everyone", embed=embed)

        for game in new_steam:
            notified_games.append(game["title"])
        save_free_games(notified_games)

    print(
        f"[FREE GAMES] Vérification terminée — Epic: {len(epic_games)} | Steam: {len(steam_games)}"
    )


# --- Commandes Minecraft --- #

import json
import os

FERME_A_FER_FILE = "/var/www/testbot/ferme_a_fer.json"
ferme_checked = {}


def format_item_name(item_id):
    name = item_id.replace("minecraft:", "").replace("_", " ").title()
    return name


def load_ferme_data():
    with open(FERME_A_FER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_ferme_embed(data, checked_set, message_id=None):
    lines = []
    for i, item in enumerate(data["items"]):
        stacks = item["count"] // 64
        reste = item["count"] % 64
        if stacks > 0 and reste > 0:
            qty = f"{stacks} stack(s) + {reste}"
        elif stacks > 0:
            qty = f"{stacks} stack(s)"
        else:
            qty = f"{reste}"

        name = format_item_name(item["id"])
        line = (
            f"~~{i+1}. {name} — {qty}~~"
            if i in checked_set
            else f"{i+1}. {name} — {qty}"
        )
        lines.append(line)

    embed = discord.Embed(
        title=f"🔨 {data['name']}", description="\n".join(lines), color=0xE67E22
    )
    return embed


class FermeView(discord.ui.View):
    def __init__(self, data, checked_set, msg_id):
        super().__init__(timeout=None)
        self.data = data
        self.checked_set = checked_set
        self.msg_id = msg_id

        for i, item in enumerate(data["items"]):
            name = format_item_name(item["id"])
            btn = discord.ui.Button(
                label=f"✅ {name[:40]}",
                style=(
                    discord.ButtonStyle.success
                    if i in checked_set
                    else discord.ButtonStyle.secondary
                ),
                custom_id=f"ferme_{msg_id}_{i}",
            )
            btn.callback = self.make_callback(i)
            self.add_item(btn)

    def make_callback(self, index):
        async def callback(interaction: discord.Interaction):
            if index in self.checked_set:
                self.checked_set.discard(index)
            else:
                self.checked_set.add(index)

            ferme_checked[self.msg_id] = self.checked_set

            embed = build_ferme_embed(self.data, self.checked_set, self.msg_id)
            view = FermeView(self.data, self.checked_set, self.msg_id)
            await interaction.response.edit_message(embed=embed, view=view)

        return callback


@bot.tree.command(
    name="ferme-a-fer", description="Affiche la liste des items pour la ferme à fer"
)
async def ferme_a_fer(interaction: discord.Interaction):
    data = load_ferme_data()
    checked_set = set()

    await interaction.response.defer()
    msg = await interaction.original_response()
    msg_id = str(msg.id)
    ferme_checked[msg_id] = checked_set

    embed = build_ferme_embed(data, checked_set, msg_id)
    view = FermeView(data, checked_set, msg_id)
    await interaction.edit_original_response(content=None, embed=embed, view=view)


bot.run(os.getenv("DISCORD_TOKEN"))
