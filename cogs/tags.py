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
            author_id bigint NOT NULL,
            tag text NOT NULL,
            tag_body text NOT NULL,
            guild_id bigint NOT NULL,
            PRIMARY KEY (r_id, tag, author_id) 
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
    async def tag_create(self, ctx, tag_name: str, *, tag_body: str):
        """Adds a tag to the database"""
        async with self.db_pool.acquire() as c:
            res = await c.fetch('SELECT * FROM tags WHERE tag = $1 and guild_id = $2', tag_name, ctx.guild.id)
            if not res:
                await c.execute("""INSERT INTO tags (data, author_id, tag, tag_body, guild_id)
                                      VALUES ($1, $2, $3, $4, $5)""", datetime.now(), ctx.author.id, tag_name,
                                tag_body, ctx.guild.id)
                return await ctx.send("Tag {} was correctly created".format(tag_name))
            await ctx.send("Tag name was already present in the database")

    @commands.command(hidden=True)
    async def tag(self, ctx, *, tag_name: str):
        """Searches for a given tag"""
        async with self.db_pool.acquire() as c:
            res = await c.fetchrow('SELECT * FROM tags WHERE tag = $1 and guild_id = $2', tag_name, ctx.guild.id)
            if res is None:
                await ctx.send("Tag was not found, use tag_create to create a new one")
            else:
                await ctx.send(res['tag_body'])

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def tag_usr_list(self, ctx, user_id: discord.User = None):
        """Searches all tags created by a user (if no id was given it will automatically search with the id of the
        author of the command """
        if user_id is None:
            user_id = ctx.author
        async with self.bot.db_pool.acquire() as conn:
            res = await conn.fetch('SELECT tag FROM tags WHERE author_id = $1 and guild_id = $2', user_id.id,
                                   ctx.guild.id)
            if not res:
                await ctx.send("There were no tags created by this user")
            else:
                embed = discord.Embed(color=discord.Color.gold())
                embed.title = "Result"
                embed.description = ", ".join(val for dic in res for val in dic.values())
                await ctx.send(embed=embed)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def tag_delete(self, ctx, *, tag_name: str):
        """Deletes a tag, if the tag is not present it will do nothing"""
        async with self.db_pool.acquire() as conn:
            if await self.bot.is_owner(ctx.author):
                await conn.execute("""DELETE FROM tags WHERE tag = $1""", tag_name)
            else:
                await conn.execute("""DELETE FROM tags WHERE tag = $1 AND author_id = $2 AND guild_id = $3""",
                                   tag_name, ctx.author.id, ctx.guild.id)
            await ctx.send("Tag was successfully deleted")
