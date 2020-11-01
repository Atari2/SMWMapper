import discord
from discord.ext import commands
import json
import client
import asyncio
import logging
import glob


def get_creds(filename):
    with open(filename, 'rb') as f:
        return json.load(f)


async def get_bot():
    credentials = get_creds('config.json')
    exts = [ext.replace('.py', '').replace('\\', '.').replace('/', '.') for ext in glob.glob('cogs/*.py')]
    exts.append('jishaku')
    prefix = commands.when_mentioned_or('>>', '!smw ')
    _bot = await client.SMWMapper.create(prefix, credentials, *exts)
    return _bot

loop = asyncio.get_event_loop()
bot = loop.run_until_complete(get_bot())
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


@bot.event
async def on_connect():
    print('Connected')


@bot.event
async def on_resumed():
    print('Resumed')


@bot.event
async def on_message(message: discord.Message):
    if message.author.id not in bot.blacklisted_users:
        await bot.process_commands(message)


@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('------')


bot.run(bot.credentials.pop('token'))
