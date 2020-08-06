import discord
from discord.ext import commands
import asyncio
from settings import *

ERROR_CHANNEL_NAME = "maintenance-channel"
SOFT_RED = 0xCD6D6D


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, e: commands.errors.CommandError
    ) -> None:
        if isinstance(e, commands.errors.UserInputError):
            await self.handle_user_input_error(ctx, e)
        else:
            if ctx.guild.id == GUILD_ID:
                channel = discord.utils.get(
                    ctx.guild.text_channels, name=ERROR_CHANNEL_NAME
                )
                if channel is not None:
                    await channel.send(embed=self._unhandled_error_embed(ctx, e))

    def _unhandled_error_embed(self, ctx, e) -> discord.Embed:
        embed = discord.Embed(colour=SOFT_RED)
        embed.add_field(
            name="Message", value=f"```{ctx.message.content}```", inline=False
        )
        embed.add_field(name="Error", value=str(e), inline=False)
        return embed

    def _get_error_embed(self, title: str, body: str) -> discord.Embed:
        """
        Return an embed that contains the exception.
        credits: https://github.com/python-discord
        """
        return discord.Embed(title=title, colour=SOFT_RED, description=body)

    @staticmethod
    def get_help_command(ctx: commands.Context):
        """
        Return a prepared `help` command invocation coroutine.
        credits: https://github.com/python-discord
        """
        if ctx.command:
            return ctx.send_help(ctx.command)

        return ctx.send_help()

    async def handle_user_input_error(
        self, ctx: commands.Context, e: commands.errors.UserInputError
    ) -> None:
        """
        Send an error message in `ctx` for UserInputError, sometimes invoking the help command too.
        * MissingRequiredArgument: send an error message with arg name and the help command
        * TooManyArguments: send an error message and the help command
        * BadArgument: send an error message and the help command
        * BadUnionArgument: send an error message including the error produced by the last converter
        * ArgumentParsingError: send an error message
        * Other: send an error message and the help command
        credits: https://github.com/python-discord
        """
        prepared_help_command = self.get_help_command(ctx)

        if isinstance(e, commands.errors.MissingRequiredArgument):
            embed = self._get_error_embed("Missing required argument", e.param.name)
            await ctx.send(embed=embed)
            await prepared_help_command
            self.bot.stats.incr("errors.missing_required_argument")
        elif isinstance(e, commands.errors.TooManyArguments):
            embed = self._get_error_embed("Too many arguments", str(e))
            await ctx.send(embed=embed)
            await prepared_help_command
            self.bot.stats.incr("errors.too_many_arguments")
        elif isinstance(e, commands.errors.BadArgument):
            embed = self._get_error_embed("Bad argument", str(e))
            await ctx.send(embed=embed)
            await prepared_help_command
            self.bot.stats.incr("errors.bad_argument")
        elif isinstance(e, commands.errors.BadUnionArgument):
            embed = self._get_error_embed("Bad argument", f"{e}\n{e.errors[-1]}")
            await ctx.send(embed=embed)
            self.bot.stats.incr("errors.bad_union_argument")
        elif isinstance(e, commands.errors.ArgumentParsingError):
            embed = self._get_error_embed("Argument parsing error", str(e))
            await ctx.send(embed=embed)
            self.bot.stats.incr("errors.argument_parsing_error")
        else:
            embed = self._get_error_embed(
                "Input error",
                "Something about your input seems off. Check the arguments and try again.",
            )
            await ctx.send(embed=embed)
            await prepared_help_command
            self.bot.stats.incr("errors.other_user_input_error")


def setup(bot):
    bot.add_cog(ErrorHandler(bot))