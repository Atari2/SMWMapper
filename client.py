import discord
import functools
from discord.ext import commands
from cogs import db, tags, blacklist


async def run_on_startup(bot):
    await bot.wait_until_ready()
    await bot.change_presence(activity=discord.Game(name="write >>help for help"))
    await tags.create_tags_table(bot.db_pool)
    await blacklist.create_blacklist_table(bot.db_pool)
    await bot.get_cog('Smw').load_maps()
    await bot.get_cog('Blacklist').load_blacklist()


class SMWMapper(commands.Bot):

    blacklisted_users = []
    credentials = {}

    def __init__(self, command_prefix, *exts, **options):
        super().__init__(command_prefix, **options)
        self.db_pool = options.pop('db_pool')
        self.credentials = options.pop('credentials')
        self.sftp_credentials = options.pop('sftp')
        for ext in exts:
            try:
                self.load_extension(ext)
            except Exception as e:
                print(str(e))
        startup_task = functools.partial(run_on_startup, self)
        self.loop.create_task(startup_task())

    @classmethod
    async def create(cls, command_prefix, credentials, *exts):
        db_creds = credentials.pop('db')
        sftp_creds = credentials.pop('sftp')
        db_pool = await db.db_connect(db_creds)
        intents = discord.Intents.all()
        intents.presences = False
        intents.typing = False
        self = SMWMapper(command_prefix, *exts, intents=intents, db_pool=db_pool,
                         credentials=credentials, sftp=sftp_creds)
        return self
