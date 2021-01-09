import unicodedata
from discord.ext import commands
import discord
from discord import utils


def setup(bot):
    bot.add_cog(Eggs(bot))


class Eggs(commands.Cog, command_attrs={'hidden': True}):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def egg(self, ctx):
        await ctx.send('\U0001f95a')

    @commands.command()
    async def goose(self, ctx):
        if ctx.author.id == 463039218541920257:
            await ctx.send('\U0001f986')
        else:
            await ctx.send('Who are you?')

    @commands.command()
    async def randombot(self, ctx):
        await ctx.send("One's better than the other, go figure which one yourself")

    @commands.command()
    async def charinfo(self, ctx, *, characters: str):
        """Shows you information about a number of characters.
        Only up to 25 characters at a time.
        """
        if not await self.bot.is_owner(ctx.author):
            return

        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Name not found.')
            return f'`\\U{digit:>08}`: {name} - {c} \N{EM DASH} <http://www.fileformat.info/info/unicode/char/{digit}>'

        msg = '\n'.join(map(to_string, characters))
        if (len(msg)) > 2000:
            return await ctx.send('Output too long to display')
        await ctx.send(msg)

    @commands.command(name='self')
    async def _self(self, ctx):
        await ctx.send("My name is SMWMapper and I'm trying to find my purpose, please help, life"
                       " is pain and suffering")

    @commands.command()
    async def walrus(self, ctx):
        await ctx.send("Arf?\n*hey, is this how you do it? Sorry I'm new here*")

    @commands.command()
    async def muncher(self, ctx):
        await ctx.send(f"*Chomps {ctx.author.name}*")

    @commands.command()
    async def sa1(self, ctx: commands.Context):
        if ctx.author.dm_channel is None:
            await ctx.author.create_dm()
        try:
            await ctx.author.dm_channel.send(file=discord.File('sa1.bps'))
            await ctx.message.add_reaction('\U00002705')
        except discord.Forbidden:
            await ctx.send("I did not have the permissions to dm you, I'll send the bps here instead",
                           file=discord.File('sa1.bps'))

    @commands.command(aliases=['sa-2'])
    async def sa2(self, ctx):
        await ctx.send("If SA-1 is so good why did they never make SA-2?")

    @commands.command()
    async def invite(self, ctx):
        await ctx.send(f'<{utils.oauth_url("714088423732019232")}>')

    @commands.command()
    async def markov(self, ctx):
        """It's magic baby"""
        async with ctx.typing():
            msg = await ctx.send('Generating...')
        await msg.edit(content=await self.bot.markov_instance.get_phrase())
