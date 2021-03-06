import discord
import functools
from discord.ext import commands
from cogs import db, tags, blacklist
import random


class MarkovTokens:
    tokens = {}
    final_tokens = ['.', '!', '?']
    starting_tokens = []
    tok_keys = []
    banned_words = []

    def __init__(self, filename):
        with open('banned_words.txt', 'r') as f:
            self.banned_words = [line.strip() for line in f.readlines()]
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        gen_lines = filter(lambda x:
                           not (x.startswith('>')
                                or x.startswith('>>')
                                or x.startswith('!mb')
                                or x.startswith('!rb')
                                or x.startswith('!ar')
                                or x.startswith('.rb')
                                or x.startswith('.ar')
                                or x.startswith('r!')
                                or x == ''
                                or x.isspace()),
                           lines)
        for line in gen_lines:
            line_tokens = line.casefold().strip('||').split()

            if line_tokens:
                self.starting_tokens.append(line_tokens[0])
            for i, tok in enumerate(line_tokens):
                if tok in self.banned_words:
                    continue
                if tok not in self.tokens:
                    self.tokens[tok] = []
                else:
                    try:
                        self.tokens[tok].append(line_tokens[i + 1])
                    except IndexError:
                        pass
        self.tok_keys = list(self.tokens.keys())

    async def get_partial_phrase(self, starting_input: str = None) -> str:
        cur_tok = starting_input or random.choice(self.starting_tokens)
        if starting_input and starting_input not in self.tokens.keys():
            phrase = 'Invalid start, doesn\'t match any of my tokens.'
            return phrase
        phrase = cur_tok
        end = False
        while not end:
            possibilities = self.tokens[cur_tok]
            try:
                cur_tok = random.choice(possibilities)
                phrase += ' ' + cur_tok
            except IndexError:
                cur_tok = random.choice(self.tok_keys)
            if cur_tok[-1] in self.final_tokens:
                end = True
        return phrase

    async def get_phrase(self, starting_input: str) -> str:
        new_phrase = await self.get_partial_phrase(starting_input)
        while new_phrase.endswith('?'):
            new_phrase += '\n' + await self.get_partial_phrase()
            if len(new_phrase) >= 2000:
                break

        return discord.utils.escape_mentions(new_phrase[:2000])


async def run_on_startup(bot):
    await bot.wait_until_ready()
    await bot.change_presence(activity=discord.Game(name="write >>help for help"))
    await tags.create_tags_table(bot.db_pool)
    await blacklist.create_blacklist_table(bot.db_pool)
    await bot.get_cog('Smw').load_maps()
    await bot.get_cog('Blacklist').load_blacklist()


class SMWMapper(commands.Bot):
    markov_instance: MarkovTokens
    blacklisted_users = []
    credentials = {}

    def __init__(self, command_prefix, *exts, **options):
        super().__init__(command_prefix, **options)
        self.db_pool = options.pop('db_pool')
        self.credentials = options.pop('credentials')
        self.markov_instance = MarkovTokens('messages.csv')
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
        db_pool = await db.db_connect(db_creds)
        intents = discord.Intents.all()
        intents.presences = False
        intents.typing = False
        self = SMWMapper(command_prefix, *exts, intents=intents, db_pool=db_pool,
                         credentials=credentials)
        return self
