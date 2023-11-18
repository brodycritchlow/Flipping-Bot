import datetime

import nextcord
import nextcord.ext.tasks as tasks
from main import update_user_nicknames
from nextcord.ext import commands


@bot.command()
async def runtime(ctx):
    # Calculate the number of hours the bot has been running
    uptime = datetime.datetime.now() - bot.start_time
    hours = uptime.total_seconds() // 3600

    # Return the formatted message
    await ctx.send(f"The bot has been running for {hours} hours.")

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    bot.start_time = datetime.datetime.now()
    update_user_nicknames.start(1045873228729548860)
import nextcord.ext.tasks as tasks
