from prettytable import PrettyTable
from discord.ext import commands


def setup(bot):
    bot.add_cog(OPcodes(bot))


def read_op_from_file():
    with open("opcodes.txt", "r") as f:
        lines = f.readlines()
    opcodes = []
    for line in lines:
        s = line.split()
        op = {'hex': s[0], 'len': s[1], 'cycles': s[2], 'mode': s[3], 'flags': s[4], 'e': s[5], 'opcode': s[6],
              'usage': s[6] + ' ' + s[7] if len(s) > 7 else s[6]}
        opcodes.append(op)
    return opcodes


class OPcodes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.opcodes = read_op_from_file()

    @commands.command(aliases=['op'])
    async def opcode(self, ctx, to_src):
        """Searches for an OPCODE and gives back a table with the information on it"""
        if len(to_src) != 3:
            return await ctx.send("Your opcode wasn't 3 letters long")
        x = PrettyTable()
        found = False
        for opcode in self.opcodes:
            x.field_names = ['HEX', 'LEN', 'CYCLES', 'MODE', 'nvmxdizc', 'e','OPCODE', 'USAGE']
            if opcode['opcode'].lower() == to_src.lower():
                found = True
                x.add_row([value for value in opcode.values()])
        if found:
            table = str(x)
            await ctx.send('```\n' + table + '\n```')
        else:
            await ctx.send(f'Found nothing for opcode {to_src.upper()}')
