import json
import os
import ast
import aiohttp
import asyncio
import bbcode
import discord
from discord.ext import commands, tasks
import glob
from datetime import datetime
import uuid
import functools
import googlesearch

smwc_map_link = 'https://smwc.me/m/'
smwc_link = 'https://www.smwcentral.net'
getmap = 'https://www.smwcentral.net/ajax.php?a=getmap&m='

pixi_spr_table = {
    '7FAB10': 0x6040,
    '7FAB1C': 0x6056,
    '7FAB28': 0x6057,
    '7FAB34': 0x606D,
    '7FAB9E': 0x6083,
    '7FAB40': 0x6099,
    '7FAB4C': 0x60AF,
    '7FAB58': 0x60C5,
    '7FAB64': 0x60DB,
    '7FAC00': 0x60F1,
    '7FAC08': 0x6030,
    '7FAC10': 0x6038
}


async def check_if_spr_table(addr, ctx):
    with open('spr_table.txt', 'r') as f:
        spr_tables: dict = ast.literal_eval(f.read())
    if len(addr) == 6 and addr.startswith('7F'):
        int_addr = int(addr, base=16)
        for k, v in pixi_spr_table.items():
            int_k = int(k, base=16)
            if int_k <= int_addr <= int_k + 12:
                await ctx.send(f'Remaps to ${v:04X} '
                               f'(this is the *start* of the sprite table, expanded to 22 slots)')
                return True
    if len(addr) == 6 and not addr.startswith('7E'):
        return False
    if len(addr) == 6:
        addr = addr[2:]
    if len(addr) == 2:
        addr = f'00{addr}'
    int_addr = int(addr, base=16)
    int_tables = [int(key, base=16) for key in spr_tables.keys()]
    for v in int_tables:
        if v <= int_addr < v + 12:
            addr = f'{v:04X}'
            break
    try:
        await ctx.send(f'Remaps to ${spr_tables[addr]:X} '
                       f'(this is the *start* of the sprite table, expanded to 22 slots)')
        return True
    except KeyError:
        return False


def setup(bot):
    bot.add_cog(Smw(bot))


def find_field(value: str, s2=0):
    s1 = value.find('\">', s2)
    s2 = value.find("</td>", s1)
    if s1 != -1 and s2 != -1:
        n = value[s1 + 2:s2]
        return n, s2
    else:
        return None, 0


def normalize_address(addr: str, ram: bool):
    if ram:
        ends = [0x7E0000, 0x7FFFFF]
        dp = "7E"
        add = "00"
    else:
        ends = [0x008000, 0x0FFFFF]
        dp = "00"
        add = "80"
    norm_addr = addr.replace("$", "")

    if len(norm_addr) == 1:
        norm_addr = '0' + norm_addr
    elif len(norm_addr) == 3:
        norm_addr = add[0] + norm_addr
    elif len(norm_addr) == 5:
        norm_addr = dp[0] + norm_addr

    if len(norm_addr) == 2:
        norm_addr = dp + add + norm_addr
    elif len(norm_addr) == 4:
        norm_addr = dp + norm_addr
    from contextlib import suppress
    with suppress(ValueError):
        if len(norm_addr) != 6:
            norm_addr = None
        elif int(norm_addr, base=16) < ends[0] or int(norm_addr, base=16) > ends[1]:
            norm_addr = None
        else:
            norm_addr = "$" + norm_addr.upper()
        return norm_addr


def clean_description(descr: str):
    descr = descr.replace("&ldquo;", "\"")
    descr = descr.replace("&rdquo;", "\"")
    s1 = descr.find("[url=")
    e1 = descr.find("]", s1)
    if s1 != -1 and e1 != -1:
        s2 = descr.find("[/")
        e2 = descr.find("]", s2)
        uri = descr[s1 + 5:e1]
        text = descr[e1 + 1:s2]
        to_rep = descr[s1:e2 + 1]
        descr = descr.replace(to_rep, f'[{text}]({uri})')
    s3 = descr.find("<!")
    s4 = descr.find(">", s3)
    if s3 != -1 and s4 != -1:
        descr = descr.replace(descr[s3:s4 + 1], "")
    s3 = descr.find("<a href=\"")
    s4 = descr.find("%22%3%E", s3)
    if s4 == -1:
        s4 = descr.find("\">")
    if s3 != -1 and s4 != -1:
        s5 = descr.find("</a>")
        uri = descr[s3 + 9:s4]
        text = descr[s4 + 2:s5]
        to_rep = descr[s3: s5 + 4]
        descr = descr.replace(to_rep, f'[{text}]({uri})')
    s3 = descr.find("[code]")
    s4 = descr.find("[/code]")
    if s3 != -1 and s4 != -1:
        to_rep = descr[s3: s3 + 6]
        to_rep2 = descr[s4: s4 + 7]
        descr = descr.replace(to_rep, "```\n")
        descr = descr.replace(to_rep2, "\n```")
    return descr


def clean_more_description(result, game, type_map):
    description = clean_description(result['description'])
    while clean_description(description) != description:
        description = clean_description(description)
    parser = bbcode.Parser()
    description = parser.strip(description)
    import re
    import html
    tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')
    no_tags = tag_re.sub('', description)
    description = html.escape(no_tags)
    description = html.unescape(description)
    description = discord.utils.escape_markdown(description, ignore_links=True)
    valid_values_link = f'https://www.smwcentral.net/?p=memorymap&a=detail&game={game}&region={type_map}&detail='
    from contextlib import suppress
    with suppress(KeyError):
        details = result['details']
        for key, value in details.items():
            url = valid_values_link + key
            description += f'\nClick [here]({url}) for the {value.lower()}'
    return description


async def get_link(address, game, type_map):
    link = smwc_map_link + game + "/" + type_map + "/"
    if type_map != 'regs' and type_map != 'sram':
        if type_map == 'rom' or type_map == 'hijacks' or type_map == 'tweaks':
            addr = normalize_address(address, False)
        else:
            addr = normalize_address(address, True)
    else:
        addr = address
    async with aiohttp.ClientSession() as cs:
        async with cs.get(link + addr.replace("$", "")) as r:
            res = await r.content.read()
            from bs4 import BeautifulSoup
            parsed = BeautifulSoup(str(res), "html.parser")
            kk = parsed.find('td', attrs={"class": "cell1 center"}, recursive=True)
            if kk is None:
                return None
            url = smwc_link + kk.contents[1].attrs['href'].replace("®", "&reg")
    return url


async def addr_result_send(ctx, addr, to_search, game, type_map):
    if addr is None:
        return await ctx.send("Something in your query went wrong")
    try:
        num_addr = int(addr.replace("$", ""), base=16)
    except ValueError:
        return await ctx.send(f'{addr} is not a valid address/hex number')
    result = None
    for item in to_search:
        start = int(item['address'].replace("$", ""), base=16)
        end = start + int(item['size'])
        if start <= num_addr < end:
            result = item
        elif start <= num_addr:
            pass
        else:
            break
    if result is None:
        return await ctx.send("Nothing was found")
    embed = discord.Embed(color=discord.Color.blue())
    embed.title = result['address']
    embed.url = smwc_map_link + game + "/" + type_map + "/" + result['address'].replace("$", "")
    embed.description = clean_more_description(result, game, type_map)
    if len(embed.description) > 2048:
        embed.description = embed.description[:2047] + '\u2026'
    embed.add_field(name="Type", value=result['type'], inline=True)
    embed.add_field(name="Size", value=result['size'], inline=True)
    embed.set_footer(text="Click on the address to jump to the SMWCentral page for that address")
    await ctx.send(embed=embed)


async def search_result_send(ctx, query, to_search, game, type_map):
    matches = []
    commons = ['to', 'the', 'in', 'of', 'a', 'and', 'not', 'on', 'with', 'by']
    per_word_matches = []
    for item in to_search:
        if item['description'].lower().find(query.lower()) != -1:
            matches.append(item)
    if not matches:
        for item in to_search:
            if all(item['description'].lower().find(word.lower()) != -1 if word not in commons else True for word in
                   query.split()):
                per_word_matches.append(item)
        if not per_word_matches:
            await ctx.send("Couldn't find anything")
        else:
            print("Per word matching was used")
            await send_matches(per_word_matches, ctx, game, type_map)
    else:
        await send_matches(matches, ctx, game, type_map)


async def send_matches(matches, ctx, game, type_map):
    embed = discord.Embed(color=discord.Color.blue())
    embed.title = "Search result:"
    embed.description = "The following addresses were found that match your query"
    for match in matches:
        match['description'] = clean_more_description(match, game, type_map)
    if len(matches) > 3:
        link = await move_to_folder(matches)
        await ctx.send(f"Your search result has more than 3 results: {link}")
        # filename = await move_to_folder(matches)
        # await ctx.send('Your search result has more than 3 results (I\'m sorry my website is down and until I fix'
        #                ' it you\'re gonna have to download the results)',
        #                file=discord.File(filename, filename='results.html'))
        # os.remove(filename)
    else:
        for match in matches:
            embed.add_field(name="Address", value=match['address'], inline=False)
            if len(match['description']) > 1024:
                match['description'] = discord.utils.escape_markdown(match['description'])[:1023] + '\u2026'
            embed.add_field(name="Description", value=match['description'], inline=False)
            embed.add_field(name="Type", value=match['type'], inline=True)
            embed.add_field(name="Size", value=match['size'], inline=True)
        await ctx.send(embed=embed)


async def get_map(smw_map):
    print('Loading map', smw_map)
    full_url = getmap + smw_map
    async with aiohttp.ClientSession() as cs:
        async with cs.get(full_url) as res:
            json_map = await res.content.read()
    print('Loaded map', smw_map)
    return json_map


async def move_to_folder(results):
    filename = f'{uuid.uuid4().hex}_{int(datetime.now().timestamp())}.html'
    html_result = generate_html_boilerplate(results)
    with open(filename, 'w') as local:
        local.write(html_result)
    os.rename(filename, '/home/pi/html/map_results/' + filename)
    return 'https://www.atarismwc.com/map_results/' + filename
    # return filename


def generate_html_boilerplate(results):
    boilerplate_code = """<!DOCTYPE html><html><head><title>Search result:</title></head>
<body style="margin-left: 2em;"><label>Search result for:</label><br><br>
<table style="width:50%"; border="1" align="left"><tr align="left">
<th>Address</th><th>Description</th><th>Type</th><th>Size</th> """
    for r in results:
        boilerplate_code += f'<tr class\"trow\"><td>{r["address"]}</td><td>{r["description"]}</td><td>{r["type"]}</td>' \
                            f'<td>{r["size"]}</td></tr>'

    boilerplate_code += '</tr></body></html>'
    return boilerplate_code


class Smw(commands.Cog):
    smwram = {}
    smwrom = {}
    smwregs = {}
    smwhijacks = {}
    smwsram = {}
    yiram = {}
    yisram = {}
    yirom = {}
    yiregs = {}
    yitweaks = {}

    # sm64ram = {}
    # sm64rom = {}
    # sm64regs = {}
    # smasram = {}
    # smasrom = {}
    # smassram = {}
    # smasregs = {}

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        choices = ['Are you now? Pff', 'This phrase was chosen at random', 'Yeah I mean that\'s valid I guess',
                   'You wish!', 'Not as much as me', 'Please DM Atari2.0 with your command of choice']
        text = ctx.message.content
        import re
        import random
        pre = re.compile(r'>>.+ ')
        for val in pre.findall(text):
            val = text.replace(val, '').strip()
            if val.find('BADA55') != -1:
                await ctx.send(random.choice(choices))
                return False
        return True

    @tasks.loop(hours=72)
    async def reload_maps_loop(self):
        await self.load_maps()

    @tasks.loop(hours=72)
    async def clear_map_results(self):
        for result in glob.glob('/home/pi/html/map_results/*.html'):
            try:
                os.remove(result)
            except Exception as e:
                print(str(e))
                pass

    @commands.command()
    async def ram(self, ctx, address: str):
        """Searches a ram address in the smw ram"""
        addr = normalize_address(address, True)
        await addr_result_send(ctx, addr, self.smwram, 'smw', 'ram')

    @commands.command()
    async def findram(self, ctx, *, query: str):
        """Searches a ram address via query"""
        await search_result_send(ctx, query, self.smwram, 'smw', 'ram')

    @commands.command()
    async def rom(self, ctx, address: str):
        """Searches a rom address in the smw rom"""
        addr = normalize_address(address, False)
        await addr_result_send(ctx, addr, self.smwrom, 'smw', 'rom')

    @commands.command()
    async def findrom(self, ctx, *, query: str):
        """Searches a rom address via query"""
        await search_result_send(ctx, query, self.smwrom, 'smw', 'rom')

    @commands.command(aliases=['reg'])
    async def regs(self, ctx, address: str):
        """Searches a regs address in the smw regs list"""
        await addr_result_send(ctx, address, self.smwregs, 'smw', 'regs')

    @commands.command()
    async def sram(self, ctx, address: str):
        """Searches a sram address in the smw sram map"""
        await addr_result_send(ctx, address, self.smwsram, 'smw', 'sram')

    @commands.command(aliases=['hijack'])
    async def hijacks(self, ctx, address: str):
        """Searches a hijacks in the SMWC hijack map"""
        addr = normalize_address(address, False)
        await addr_result_send(ctx, addr, self.smwhijacks, 'smw', 'hijacks')

    @commands.command()
    async def yiram(self, ctx, address: str):
        """Searches a ram address in the Yoshi's Island ram map"""
        addr = normalize_address(address, True)
        await addr_result_send(ctx, addr, self.yiram, 'yi', 'ram')

    @commands.command()
    async def yirom(self, ctx, address: str):
        """Searches a rom address in the Yoshi's Island rom map"""
        addr = normalize_address(address, False)
        await addr_result_send(ctx, addr, self.yirom, 'yi', 'rom')

    @commands.command()
    async def yisram(self, ctx, address: str):
        """Searches a sram address in the Yoshi's Island sram map"""
        await addr_result_send(ctx, address, self.yisram, 'yi', 'sram')

    @commands.command(aliases=['yireg'])
    async def yiregs(self, ctx, address: str):
        """Searches a register in the Yoshi's Island regs list"""
        await addr_result_send(ctx, address, self.yiregs, 'yi', 'regs')

    @commands.command(aliases=['yitweak'])
    async def yitweaks(self, ctx, address: str):
        """Searches a tweak address in the SMWC YI tweaks map"""
        addr = normalize_address(address, False)
        await addr_result_send(ctx, addr, self.yitweaks, 'yi', 'tweaks')

    @commands.command(hidden=True)
    async def reload_all_maps(self, ctx: commands.Context):
        """Reloads all the maps from SMWC"""
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.ban_members:
            await ctx.send("You don't have the power to run this command")
            return
        await self.load_maps()
        await ctx.send("Maps reloaded")

    @commands.command()
    async def resource(self, ctx, *, query: str):
        """Searches for a resource on SMWC"""
        async with ctx.typing():
            searchfunc = functools.partial(googlesearch.search, query + ' site:smwcentral.net',
                                           tld='com', lang='en', num=1, start=0, stop=1, pause=2.0)
            gen = await ctx.bot.loop.run_in_executor(None, searchfunc)
            nextfunc = functools.partial(next, gen)
            res = await ctx.bot.loop.run_in_executor(None, nextfunc)
            if res.startswith('https://www.smwcentral.net/?p=section&a=details&id'):
                await ctx.send(res)
            else:
                await ctx.send('No resource found')

    @commands.command()
    async def spctomp3(self, ctx):
        """Converts an SPC to an MP3 file (or at least attempts to) and sends it, note that the file must have a
        valid SPC header. If the SPC is long, this command can take a while to execute, mostly due to the conversion
        and upload procedures"""
        if len(ctx.message.attachments) == 0:
            return await ctx.send("There was no SPC attached to this command")
        filename = ctx.message.attachments[0].filename
        await ctx.message.attachments[0].save(filename)
        with open(filename, "rb") as f:
            data = f.read()
        header = bytearray(data[0:33]).decode('utf-8')
        size = os.stat(filename).st_size
        if header != "SNES-SPC700 Sound File Data v0.30" or not filename.endswith(".spc") or size != 66048:
            os.remove(filename)
            return await ctx.send("This is either not an SPC file or the header couldn't be read correctly")
        length = [data[0xA9], data[0xAA], data[0xAB]]
        fade = []
        offset = 0xAC
        for i in range(5):
            fade.append(data[offset + i])
        try:
            seconds = int(bytearray(length).decode('utf-8')) + (int(bytearray(fade).decode('utf-8')) / 1000)
        except ValueError:
            os.remove(filename)
            return await ctx.send("SPC length couldn't be read correctly from header")
        import time
        timestamp = time.strftime('%H:%M:%S', time.gmtime(seconds))
        ffmpeg_op = f'ffmpeg -i {filename} -vn -t {timestamp} -filter:a "afade=in:st=0:d=1, afade=out:st=' \
                    f'{int(seconds) - 10}:d=10" -ar 44100 -ac 2 -b:a 64k {filename.replace("spc", "mp3")} '
        async with ctx.typing():
            proc = await asyncio.create_subprocess_shell(ffmpeg_op, stdout=asyncio.subprocess.PIPE,
                                                         stderr=asyncio.subprocess.PIPE)
            await proc.communicate()
            if not os.path.isfile(filename.replace("spc", "mp3")):
                await ctx.send("Something went wrong in the conversion of the SPC, sorry")
            elif os.stat(filename.replace("spc", "mp3")).st_size > 8 * 1024 * 1024:
                await ctx.send("Generated mp3 file was too big to be sent")
                os.remove(filename.replace("spc", "mp3"))
            else:
                await ctx.send(file=discord.File(filename.replace("spc", "mp3")))
                os.remove(filename.replace("spc", "mp3"))
            os.remove(filename)

    @commands.command()
    async def remap(self, ctx, addr: str):
        """Remaps addresses to SA-1, or at least attempts to"""
        addr = addr.replace('$', '').upper()
        try:
            int_addr = int(addr, base=16)
        except ValueError:
            return await ctx.send('Invalid hex number for address')
        if len(addr) == 2:  # direct page can return the same address
            if await check_if_spr_table(addr, ctx):
                return
            return await ctx.send(f'Remaps to ${addr}')
        elif len(addr) == 4:
            if await check_if_spr_table(addr, ctx):
                return  # if sprite table, do the thing
            else:
                if 0x0000 <= int_addr <= 0x00FF:
                    return await ctx.send(f'Remaps to ${addr.replace("0", "3", 1)}')
                elif 0x1938 <= int_addr <= 0x19B7:
                    return await ctx.send(f'Remaps to $418A00, this is the *start* of the table, '
                                          f'expanded to 255 entries on SA-1')
                elif 0x0100 <= int_addr <= 0x1FFF:
                    return await ctx.send(f'Remaps to ${(int_addr | 0x6000):X}')
                elif 0xC800 <= int_addr <= 0xFFFF:
                    return await ctx.send(f'Remaps to $40{int_addr:X}')
            return await ctx.send(f'Not remapped')
        elif len(addr) > 6:
            return await ctx.send('Invalid address')
        elif len(addr) % 2 == 1:
            return await ctx.send('Please use $xx, $xxxx or $xxxxxx. No 1/3/5 digit addresses because I\'m lazy')

        if 0x7E1938 <= int_addr <= 0x7E19B7:
            await ctx.send(f'Remaps to $418A00, this is the *start* of the table, expanded to 255 entries on SA-1')
        elif 0x7EC800 <= int_addr <= 0x7EFFFF:
            offset = int_addr - 0x7EC800
            await ctx.send(f'Remaps to ${(0x40C800 + offset):X}')
        elif 0x7F9A7B <= int_addr <= 0x7F9C7A:
            offset = int_addr - 0x7F9A7B
            await ctx.send(f'Remaps to ${(0x418800 + offset):X}')
        elif 0x7FC700 <= int_addr <= 0x7FFFFF:
            offset = int_addr - 0x7FC700
            await ctx.send(f'Remaps to ${(0x41C800 + offset):X}')
        elif 0x700000 <= int_addr <= 0x7007FF:
            offset = int_addr - 0x700000
            await ctx.send(f'Remaps to ${(0x41C000 + offset):X}')
        elif 0x700800 <= int_addr <= 0x7027FF:
            offset = int_addr - 0x700800
            await ctx.send(f'Remaps to ${(0x41A000 + offset):X}')
        else:
            if await check_if_spr_table(addr, ctx):
                return
            if addr.lower().startswith('7e'):
                int_abs_addr = int(addr[2:], 16)
                if 0x0000 <= int_abs_addr <= 0x00FF:
                    return await ctx.send(f'Remaps to ${(int_abs_addr | 0x3000):X}')
                elif 0x1938 <= int_abs_addr <= 0x19B7:
                    return await ctx.send(f'Remaps to $418A00, this is the *start* of the table, '
                                          f'expanded to 256 entries on SA-1')
                elif 0x0100 <= int_abs_addr <= 0x1FFF:
                    return await ctx.send(f'Remaps to ${(int_abs_addr | 0x6000):X}')
                elif 0xC800 <= int_abs_addr <= 0xFFFF:
                    return await ctx.send(f'Remaps to $40{int_abs_addr:X}')
            await ctx.send('Not remapped')

    @clear_map_results.before_loop
    async def before_clear_loop(self):
        await self.bot.wait_until_ready()

    @reload_maps_loop.before_loop
    async def before_load_maps_loop(self):
        await self.bot.wait_until_ready()

    async def load_maps(self):
        self.smwrom = json.loads((await get_map('smwrom')).decode('utf-8'))
        self.smwram = json.loads((await get_map('smwram')).decode('utf-8'))
        self.smwregs = json.loads((await get_map('smwregs')).decode('utf-8'))
        self.smwhijacks = json.loads((await get_map('smwhijack')).decode('utf-8'))
        self.smwsram = json.loads((await get_map('smwsram')).decode('utf-8'))
        self.yiram = json.loads((await get_map('yiram')).decode('utf-8'))
        self.yirom = json.loads((await get_map('yirom')).decode('utf-8'))
        self.yiregs = json.loads((await get_map('yiregs')).decode('utf-8'))
        self.yitweaks = json.loads((await get_map('yitweaks')).decode('utf-8'))
        self.yisram = json.loads((await get_map('yisram')).decode('utf-8'))
        # self.sm64ram = json.loads((await get_map('sm64ram')).decode('utf-8'))
        # self.sm64rom = json.loads((await get_map('sm64rom')).decode('utf-8'))
        # self.sm64regs = json.loads((await get_map('sm64regs')).decode('utf-8'))
        # self.smasram = json.loads((await get_map('smasram')).decode('utf-8'))
        # self.smasrom = json.loads((await get_map('smasrom')).decode('utf-8'))
        # self.smassram = json.loads((await get_map('smassram')).decode('utf-8'))
        # self.smasregs = json.loads((await get_map('smasregs')).decode('utf-8'))
