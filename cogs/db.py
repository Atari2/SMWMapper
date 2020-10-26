from discord.ext import commands
import asyncpg


def setup(bot):
    bot.add_cog(Sqldb(bot))


async def db_connect(kwargs):
    pool: asyncpg.pool = await asyncpg.create_pool(**kwargs)
    return pool


class Sqldb(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_pool = bot.db_pool

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command(hidden=True)
    async def execute(self, ctx, *, query: str):
        try:
            query = query.replace("\n", ";")
            if not query.endswith(";"):
                query = query + ";"
            async with self.db_pool.acquire() as dbconn:
                await dbconn.execute(query)
        except Exception as e:
            await ctx.send(str(e))

    @commands.command(hidden=True)
    async def fetch(self, ctx, *, query: str):
        try:
            query = query.replace("\n", ";")
            if not query.endswith(";"):
                query = query + ";"
            async with self.db_pool.acquire() as dbconn:
                res = await dbconn.fetch(query)
            await ctx.send(res)
        except Exception as e:
            await ctx.send(str(e))
