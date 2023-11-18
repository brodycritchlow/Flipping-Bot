"""
RBXFlip Bot

- Emulates a fake flip of roblox limiteds

20% below or 20% above
"""

import datetime
import os
import random
import sqlite3

import nextcord
from dotenv import load_dotenv
from nextcord.ext import commands, menus, tasks

from utility import get_items, get_rand

load_dotenv()
intents = nextcord.Intents.all()

bot = commands.Bot(intents=intents)


@tasks.loop(seconds=10)
async def update_user_nicknames(guild_id: int):
    guild = bot.get_guild(guild_id)

    for member in guild.members:
        if not member.bot:
            user_id = str(member.id)

            # Fetch the user's total value and RAP from the database
            c.execute("SELECT SUM(value) FROM items WHERE user_id=?", (user_id,))
            total_value = c.fetchone()[0] or 0
            c.execute("SELECT SUM(rap) FROM items WHERE user_id=?", (user_id,))
            total_rap = c.fetchone()[0] or 0

            # Update the user's nickname with the total value and RAP
            nickname = f"{member.name} ({total_value:,} | {total_rap:,})"

            try:
                await member.edit(nick=nickname)
            except nextcord.errors.Forbidden:
                # "Can't edit owner of server."
                ...


# Connect to the database
conn = sqlite3.connect(r"databases\items.db")
c = conn.cursor()

conni = sqlite3.connect(r"databases\item_claims.db")
ci = conn.cursor()

# create a table to store item claims
ci.execute(
    """CREATE TABLE IF NOT EXISTS item_claims (
                user_id INTEGER,
                code_name TEXT,
                claimed_at TIMESTAMP
            )"""
)
conni.commit()
# Create the items table if it doesn't exist
c.execute(
    """CREATE TABLE IF NOT EXISTS items
             (user_id INTEGER, item_name TEXT, rap INTEGER, value INTEGER)"""
)


def get_items_for_user(user_id):
    c.execute("SELECT * FROM items WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    items = []
    for row in rows:
        item = {"name": row[1], "rap": row[2], "value": row[3]}
        items.append(item)
    return items


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    update_user_nicknames.start(1045873228729548860)


@bot.slash_command(description="Gives you 3 random limiteds")
async def restart(interaction: nextcord.Interaction):
    c.execute("DELETE FROM items WHERE user_id = ?", (interaction.user.id,))
    ci.execute("DELETE FROM item_claims WHERE user_id = ?", (interaction.user.id,))

    items = get_rand()

    # Create embed
    embed = nextcord.Embed(
        title="Items Recieved",
    )

    i = 1
    total_value = 0

    # Add fields to embed and insert data into database
    for item in items:
        embed.add_field(
            name=f"Item {i}",
            value=f"**NAME**: {item.item_name}\n**RAP**: {item.rap}\n**VALUE**: {item.default_value}",
            inline=False,
        )
        i += 1
        total_value += item.default_value

        # Insert data into database
        c.execute(
            "INSERT INTO items VALUES (?, ?, ?, ?)",
            (str(interaction.user.id), item.item_name, item.rap, item.default_value),
        )

    embed.set_footer(text=f"TOTAL VALUE: {total_value:,}")

    await interaction.send(embed=embed)

    # Commit changes to database
    conn.commit()


@bot.slash_command()
async def code(interaction: nextcord.Interaction, code: str):
    # check if the code has already been claimed
    ci.execute(
        "SELECT * FROM item_claims WHERE user_id = ? AND code_name = ?",
        (interaction.user.id, code),
    )
    existing_claim = ci.fetchone()
    if existing_claim:
        claimed_at = datetime.datetime.fromisoformat(existing_claim[2])
        minutes_since_claim = (
            datetime.datetime.now() - claimed_at
        ).total_seconds() / 60
        await interaction.response.send_message(
            f"You've already claimed this code. Please wait {int(10 - minutes_since_claim)} minutes before claiming again."
        )
        return

    # add the code claim to the database
    ci.execute(
        "INSERT INTO item_claims VALUES (?, ?, ?)",
        (interaction.user.id, code, datetime.datetime.now().isoformat()),
    )
    conni.commit()

    # get random items
    items = get_items(1_200_000)

    embed = nextcord.Embed(
        title="Items Received",
    )

    i = 1
    total_value = 0

    if code == "NEW":
        for item in items:
            embed.add_field(
                name=f"Item {i}",
                value=f"**NAME**: {item.item_name}\n**RAP**: {item.rap}\n**VALUE**: {item.default_value}",
                inline=False,
            )
            i += 1
            total_value += item.default_value

            c.execute(
                "INSERT INTO items VALUES (?, ?, ?, ?)",
                (
                    str(interaction.user.id),
                    item.item_name,
                    item.rap,
                    item.default_value,
                ),
            )

        embed.set_footer(text=f"TOTAL VALUE: {total_value:,}")

        await interaction.response.send_message(embed=embed)

    conn.commit()


class InventoryPaginator(menus.ListPageSource):
    def __init__(self, user_items):
        super().__init__(
            sorted(user_items, key=lambda i: int(i["value"]), reverse=True), per_page=5
        )

    async def format_page(self, menu, items):
        embed = nextcord.Embed(title="Inventory")

        total_val = 0
        for item in items:
            embed.add_field(
                name=item["name"],
                value=f'**RAP**: {item["rap"]}\n**Value**: {item["value"]}',
                inline=False,
            )
            total_val += item["value"]

        embed.set_footer(text=f"TOTAL VALUE: {total_val}")
        return embed


@bot.slash_command()
async def inventory(interaction: nextcord.Interaction):
    # Retrieve user's items from the database
    user_items = get_items_for_user(interaction.user.id)
    if not user_items:
        await interaction.send("Your inventory is empty!")
        return

    # Create a paginator for the user's items
    paginator = menus.MenuPages(
        source=InventoryPaginator(user_items), clear_reactions_after=True
    )
    await paginator.start(interaction=interaction)


# nextcord.SlashOption("item", choices=fetch_choices(612107033608585252)

global trades
trades = {}


@bot.slash_command(description="Coinflip with your items")
async def duel(
    interaction: nextcord.Interaction,
    items: str = None,
    quantity: int = 1,
    side: str = "h",
):
    user_id = interaction.user.id

    if side.lower() == "h":
        side = 1
        chc = "Heads"
        opp = "Tails"
    elif side.lower() == "head":
        side = 1
        chc = "Heads"
        opp = "Tails"
    elif side.lower() == "heads":
        side = 1
        chc = "Heads"
        opp = "Tails"
    else:
        side = 0
        chc = "Tails"
        opp = "Heads"

    # Retrieve items from database
    if items:
        item_names = items.split(", ")
        c.execute(
            "SELECT * FROM items WHERE user_id = ? AND item_name IN ({})".format(
                ",".join("?" for _ in item_names)
            ),
            (user_id,) + tuple(item_names),
        )
    else:
        c.execute("SELECT * FROM items WHERE user_id = ?", (user_id,))

    items = sorted(c.fetchall(), key=lambda i: i[-1], reverse=True)[:8]

    if not items:
        await interaction.send("You don't have any items to duel!")
        return

    if len(items) < quantity:
        await interaction.send(
            "You don't have enough of those items to duel that many!"
        )
        return

    # Get random items to gamble
    total_value = sum([i[-1] for i in items])
    random_items = get_items(total_value)

    if not random_items:
        random_items = items

    # Flip the coin
    coinflip = random.randint(0, 1)

    if coinflip == side:
        # Duplicate the items that the user gambled
        for itm in random_items:
            c.execute(
                "INSERT INTO items VALUES (?, ?, ?, ?)",
                (user_id, itm.item_name, itm.rap, itm.default_value),
            )

        await interaction.send(f"The coin landed on {chc}! You have won.")

        embed = nextcord.Embed(title=f"{interaction.user.name}'s winnings")

        for item in random_items:
            embed.add_field(
                name=item.item_name,
                value=f"**RAP**: {item.rap}\n**Value**: {item.default_value}",
                inline=False,
            )

        await interaction.send(embed=embed)

    else:
        # Remove the items that the user gambled

        for i in items:
            c.execute(
                "DELETE FROM items WHERE user_id = ? AND item_name = ?", (user_id, i[1])
            )

        await interaction.send(f"The coin landed on {opp}! You have lost.")

        embed = nextcord.Embed(title=f"{interaction.user.name}'s loss")

        for i in items:
            embed.add_field(
                name=i[1], value=f"**RAP**: {i[2]}\n**Value**: {i[3]}", inline=False
            )

        await interaction.send(embed=embed)

    # Commit changes to database
    conn.commit()


TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
