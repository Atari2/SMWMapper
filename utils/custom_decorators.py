from discord.ext import commands
import functools


class CustomCheckFailure(commands.CheckFailure):
    message = ''

    def __init__(self, ctx, utype, uid):
        self.message = f'Command {ctx.command.qualified_name} can only be used in {utype} with id {uid}'
        super().__init__(message=self.message)


def check_id(ctx, idtype: str, uid: int):
    try:
        return getattr(ctx, idtype).id == uid
    except AttributeError:
        return False


def partial_multi_predicate(id_tuple: dict, ctx):
    return all(partial_predicate(uid, utype, ctx) for utype, uid in id_tuple.items())


def partial_predicate(uid, utype, ctx):
    if not check_id(ctx, utype, uid):
        raise CustomCheckFailure(ctx, utype, uid)
    return True


def is_in_guild(guild_id: int):
    predicate = functools.partial(partial_predicate, guild_id, 'guild')
    return commands.check(predicate)


def is_in_channel(chn_id: int):
    predicate = functools.partial(partial_predicate, chn_id, 'channel')
    return commands.check(predicate)


def is_by_user(user_id: int):
    predicate = functools.partial(partial_predicate, user_id, 'author')
    return commands.check(predicate)


def multiple_is_by(**mappings):
    predicate = functools.partial(partial_multi_predicate, mappings)
    return commands.check(predicate)
