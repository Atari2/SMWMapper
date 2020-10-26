import asyncio
import io
import subprocess
import textwrap
import traceback
from contextlib import redirect_stdout

import discord
from discord.ext.commands import ExtensionNotLoaded, ExtensionNotFound, NoEntryPointError, ExtensionFailed
from discord.ext import commands


def setup(bot):
    bot.add_cog(Admin(bot))


def get_syntax_error(e):
    if e.text is None:
        return f'```py\n{e.__class__.__name__}: {e}\n```'
    return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'


def cleanup_code(content):
    """Automatically removes code blocks from the code"""
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])

    return content.strip('` \n')


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self.session = set()

    async def run_process(self, command):
        try:
            process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await self.bot.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.group(invoke_without_command=True, hidden=True)
    async def plz(self, ctx):
        if ctx.invoked_subcommand is None:
            return

    @plz.command(name='parseid')
    async def _parseid(self, ctx, uiid: int):
        from datetime import datetime
        try:
            user: discord.User = await self.bot.fetch_user(uiid)
            embed: discord.Embed = discord.Embed(color=discord.Color.blue())
            embed.set_author(name=f'Requested by {ctx.author.name}', icon_url=ctx.author.avatar_url)
            embed.set_thumbnail(url=user.avatar_url)
            embed.add_field(name='Username', value=user.name, inline=False)
            embed.add_field(name='Discriminator', value=user.discriminator, inline=False)
            embed.add_field(name='In server?', value='Yes' if user in ctx.guild.members else 'No', inline=True)
            embed.add_field(name='Is bot?', value='Yes' if user.bot is True else 'No', inline=True)
            embed.set_footer(text=f'At {datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}')
            await ctx.send(embed=embed)
        except discord.NotFound:
            await ctx.send("User couldn't be found")
        except discord.HTTPException:
            await ctx.send("An unknown HTTP exception occurred")

    @plz.command(name='parsesf')
    async def _snowflake(self, ctx, snowflake: int):
        from datetime import datetime
        depoch = 1420070400000
        binary = bin(snowflake)[2:].zfill(64)
        uid = binary[52:]
        pid = binary[47:52]
        wid = binary[42:47]
        ms = int(binary[:42], base=2)
        ms += depoch
        time = datetime.fromtimestamp(ms / 1000).strftime('%Y-%m-%d %H:%M:%S.%f')
        embed: discord.Embed = discord.Embed(color=discord.Color.blue())
        embed.set_author(name=f'Requested by {ctx.author.name}', icon_url=ctx.author.avatar_url)
        embed.add_field(name='Unique id:', value=uid)
        embed.add_field(name='Process id:', value=pid)
        embed.add_field(name='Worker id:', value=wid)
        embed.add_field(name='Timestamp:', value=time)
        await ctx.send(embed=embed)

    @plz.command(name='uptime')
    async def _uptime(self, ctx):
        import psutil
        import os
        import time
        p = psutil.Process(os.getpid())
        p.create_time()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.create_time()))
        await ctx.send("SMWMapper has been up since {} CET".format(timestamp))

    @plz.command(name='ping')
    async def _ping(self, ctx):
        """Returns the ping of the bot"""
        await ctx.send(f'{self.bot.latency:0.3f} seconds')

    @plz.command(name='ver')
    async def _ver(self, ctx):
        """Displays information about the bot's version and OS"""
        import sys
        py_ver = str(sys.version)[:str(sys.version).find(' ')]
        info = f'Running on {sys.platform} with Python {py_ver}'
        await ctx.send(info)

    @plz.command(name='usage')
    async def _usage(self, ctx):
        """Displays usage info about the system (not the bot)"""
        import psutil
        import math
        cpu_usage = psutil.cpu_percent()
        ram = dict(psutil.virtual_memory()._asdict())
        await ctx.send(
            f'Cpu usage {cpu_usage}% / Memory usage {ram["percent"]}% ({(ram["used"] / math.pow(1024, 3)):0.2f}'
            f' GB out of {(ram["total"] / math.pow(1024, 3)):0.2f} GB)')

    @plz.command(name='enable')
    async def _enable(self, ctx, cmd_name: str):
        cmd = self.bot.get_command(cmd_name)
        if cmd is not None:
            if cmd.enabled is True:
                await ctx.send(f"The command {cmd_name} is already enabled")
            else:
                cmd.enabled = True
                await ctx.send(f"The command {cmd_name} was enabled")
        else:
            await ctx.send(f"The command {cmd_name} wasn't found")

    @plz.command(name='disable')
    async def _disable(self, ctx, cmd_name: str):
        cmd = self.bot.get_command(cmd_name)
        if cmd is not None:
            cmd.enabled = False
            await ctx.send(f"Command {cmd_name} was disabled")
        else:
            await ctx.send(f"Command {cmd_name} wasn't found")

    @commands.command(hidden=True)
    async def reload(self, ctx, cog):
        try:
            self.bot.reload_extension(cog.lower())
            await ctx.message.add_reaction('\U0001f501')
        except (ExtensionNotLoaded or ExtensionNotFound or ExtensionFailed or NoEntryPointError) as e:
            await ctx.send(f"Extension couldn't be reloaded. Exception was {str(e)}")

    @commands.command(hidden=True)
    async def sh(self, ctx, *, command):
        """Runs a shell command"""
        from pages import TextPages

        async with ctx.typing():
            stdout, stderr = await self.run_process(command)

        if stderr:
            text = f'stdout:\n{stdout}\nstderr:\n{stderr}'
        else:
            text = stdout

        try:
            pages = TextPages(ctx, text)
            await pages.paginate()
        except Exception as e:
            await ctx.send(str(e))

    @commands.command(pass_context=True, hidden=True, name='eval')
    async def _eval(self, ctx, *, body: str):
        """Evaluates a piece of python code"""
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }
        env.update(globals())

        body = cleanup_code(body)

        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, " ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            print(str(e))
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except Exception as e:
                print(str(e))
                pass
            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')
