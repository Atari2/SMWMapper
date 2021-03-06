import unicodedata
from discord.ext import commands
import discord
from discord import utils

SMWC_GUILD = 161245277179609089
SMWC_WOI_CHANNEL = 381187250265784320


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
    async def cattp(self, ctx, err: int):
        cat_codes = [100, 101, 102, 200, 201, 202, 204, 206, 207, 300, 301, 302, 303, 304, 305, 307,
                     400, 401, 402, 403, 404, 405, 406, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 420,
                     421, 422, 423, 424, 425, 426, 429, 431, 444, 450, 451, 499, 500, 501, 502, 503, 504, 506, 507, 508,
                     509, 510, 511, 599]
        if err not in cat_codes:
            await ctx.send('No cat was available, sorry :(')
        else:
            await ctx.send(f'https://http.cat/{err}')

    @commands.cooldown(1, 30, type=commands.BucketType.user)
    @commands.command()
    async def markov(self, ctx: commands.Context, *, starting_input: str = None):
        """It's magic baby"""
        if ctx.guild.id == SMWC_GUILD and ctx.channel.id != SMWC_WOI_CHANNEL:
            await ctx.send(f'This command may only be used in {ctx.guild.get_channel(SMWC_WOI_CHANNEL).mention}')
            return
        if starting_input:
            starting_input = starting_input.lower()
        async with ctx.typing():
            msg = await ctx.send('Generating...')
        await msg.edit(content=await self.bot.markov_instance.get_phrase(starting_input))

    @markov.error
    async def handle_err(self, ctx, err):
        if isinstance(err, commands.CommandOnCooldown):
            await ctx.send(f'You have to wait {err.retry_after} seconds before using this command again')
