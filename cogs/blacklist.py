import asyncpg
from discord.ext import commands


def setup(bot):
    bot.add_cog(Blacklist(bot))


async def create_blacklist_table(pool):
    async with pool.acquire() as conn:
        try:
            await conn.execute("CREATE extension IF NOT EXISTS \"uuid-ossp\";")
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS blacklisted_users 
            (
            user_id BIGINT NOT NULL,
            PRIMARY KEY (user_id)
            );
            """)
        except Exception as e:
            print(str(e))


class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_pool = bot.db_pool

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    async def load_blacklist(self):
        async with self.db_pool.acquire() as conn:
            res = await conn.fetch('SELECT * FROM blacklisted_users;')
            res = [int(r['user_id']) for r in res]
            self.bot.blacklisted_users.extend(res)

    @commands.command(hidden=True)
    async def show_blacklisted(self, ctx):
        await ctx.send(f'Blacklisted users are {self.bot.blacklisted_users}')

    @commands.command(hidden=True)
    async def blacklist(self, ctx, user_id: int):
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute('INSERT INTO blacklisted_users (user_id) VALUES ($1)', user_id)
                await ctx.send(f'User with id {user_id} was blacklisted from using the bot')
                self.bot.blacklisted_users.append(user_id)
            except asyncpg.UniqueViolationError as e:
                await ctx.send(str(e))

    @commands.command(hidden=True)
    async def remove_blacklist(self, ctx, user_id: int):
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute('DELETE FROM blacklisted_users WHERE user_id=$1', user_id)
                self.bot.blacklisted_users.remove(user_id)
                await ctx.send(f'User with id {user_id} was removed from the blacklist')
            except Exception as e:
                await ctx.send(str(e))