import discord
from discord.ext import commands
from datetime import datetime
import asyncpg


def setup(bot):
    bot.add_cog(Tags(bot))


# Creates the table and the extension for uuid-ossp if not existing already
async def create_tags_table(dbpool: asyncpg.pool):
    try:
        async with dbpool.acquire() as dbconn:
            await dbconn.execute("CREATE extension IF NOT EXISTS \"uuid-ossp\";")
            await dbconn.execute("""
            CREATE TABLE IF NOT EXISTS tags 
            (
            r_id uuid DEFAULT uuid_generate_v4(),
            data timestamp NOT NULL,
            author_id text NOT NULL,
            tag text NOT NULL,
            tag_body text NOT NULL,
            PRIMARY KEY (r_id, tag) 
            );
            """)
    except Exception as e:
        print(str(e))


class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_pool = bot.db_pool

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def tag_create(self, ctx, tag_name, *, tag_body):
        """Adds a tag to the database"""
        async with self.db_pool.acquire() as c:
            res = await c.fetch('SELECT * FROM tags WHERE tag = $1', str(tag_name))
            if not res:
                await c.execute("""INSERT INTO tags (data, author_id, tag, tag_body)
                                      VALUES ($1, $2, $3, $4)""", datetime.now(), str(ctx.author.id), tag_name,
                                tag_body)
                return await ctx.send("Tag {} was correctly created".format(tag_name))
            await ctx.send("Tag name was already present in the database")

    @commands.command(hidden=True)
    async def tag(self, ctx, tag_name):
        """Searches for a given tag"""
        async with self.db_pool.acquire() as c:
            res = await c.fetchrow('SELECT * FROM tags WHERE tag = $1', str(tag_name))
            if res is None:
                await ctx.send("Tag was not found, use tag_create to create a new one")
            else:
                await ctx.send(res['tag_body'])

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def tag_usr_list(self, ctx, user_id=None):
        """Searches all tags created by a user (if no id was given it will automatically search with the id of the
        author of the command """
        if user_id is None:
            user_id = ctx.author.id
        async with self.bot.db_pool.acquire() as conn:
            res = await conn.fetch('SELECT tag FROM tags WHERE author_id = $1', str(user_id))
            if not res:
                await ctx.send("There were no tags created by this user")
            else:
                embed = discord.Embed(color=discord.Color.gold())
                embed.title = "Result"
                embed.description = ", ".join(val for dic in res for val in dic.values())
                await ctx.send(embed=embed)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def tag_delete(self, ctx, tag_name):
        """Deletes a tag, if the tag is not present it will do nothing"""
        async with self.db_pool.acquire() as conn:
            if await self.bot.is_owner(ctx.author):
                await conn.execute("""DELETE FROM tags WHERE tag = $1""", str(tag_name))
            else:
                await conn.execute("""DELETE FROM tags WHERE tag = $1 AND author_id = $2""", str(tag_name),
                                   str(ctx.author.id))
            await ctx.send("Tag was successfully deleted")
