"""Error handling (legacy)."""

import asyncio
import logging

from nextcord import Embed, Message
from nextcord.ext.commands import Bot, Cog, Context, errors

from domain import ChannelName, Color, Standby, ValidTextChannel
from utils import util_functions as uf

logger = logging.getLogger(__name__)


class ErrorHandler(Cog):
    def __init__(self) -> None:
        self.standby = Standby

    async def send_help_command(self, ctx: Context) -> None:
        """Send a help message."""
        if ctx.command:
            await ctx.send_help(ctx.command)
        else:
            await ctx.send_help()

    @Cog.listener()
    async def on_command_error(self, ctx: Context, e: errors.CommandError) -> None:
        """Triggered when a command raises an error."""
        logger.error(f"Command error: {e}")
        if isinstance(e, errors.UserInputError):
            logger.error("UserInputError")
            await self.handle_user_input_error(ctx, e)
        elif isinstance(e, errors.CommandNotFound):
            logger.error("CommandNotFound")
            await self._sleep_and_delete(
                await ctx.channel.send(
                    embed=self._get_error_embed(
                        title="Command not found",
                        body=ctx.message.content,
                    ),
                ),
            )
        else:
            channel = uf.get_channel(ChannelName.ERRORS)
            if channel is not None:
                await channel.send(
                    embed=unhandled_error_embed(ctx.message.content, ctx.channel, e),
                )

    def _get_error_embed(self, title: str, body: str) -> Embed:
        """Return an embed that contains the exception.

        Credit: https://github.com/python-discord
        """
        return Embed(title=title, color=Color.SOFT_RED, description=body)

    async def _sleep_and_delete(self, msg: Message) -> None:
        """Delete message after a delay."""
        await asyncio.sleep(20)
        try:
            await msg.delete()
        except:
            logger.warning(f"Can't delete message {msg}")

    async def handle_user_input_error(
        self,
        ctx: Context,
        e: errors.UserInputError,
    ) -> None:
        """Error handling dispatcher.

        Credits: https://github.com/python-discord
        """
        if isinstance(e, errors.MissingRequiredArgument):
            embed = self._get_error_embed("Missing required argument", e.param.name)
            await ctx.send(embed=embed)
            await self.send_help_command(ctx)
        elif isinstance(e, errors.TooManyArguments):
            embed = self._get_error_embed("Too many arguments", str(e))
            await ctx.send(embed=embed)
            await self.send_help_command(ctx)
        elif isinstance(e, errors.BadArgument):
            embed = self._get_error_embed("Bad argument", str(e))
            await ctx.send(embed=embed)
            await self.send_help_command(ctx)
        elif isinstance(e, errors.BadUnionArgument):
            embed = self._get_error_embed("Bad argument", f"{e}\n{e.errors[-1]}")
            await ctx.send(embed=embed)
        elif isinstance(e, errors.ArgumentParsingError):
            embed = self._get_error_embed("Argument parsing error", str(e))
            await ctx.send(embed=embed)
        else:
            embed = self._get_error_embed(
                "Input error",
                "Something about your input seems off. Check "
                "the arguments and try again."
                if str(e) == ""
                else str(e),
            )
            await ctx.send(embed=embed)
            if str(e) == "":
                await self.send_help_command(ctx)


def unhandled_error_embed(cont: str, chan: ValidTextChannel, e: Exception) -> Embed:
    """Generate an error embed."""
    embed = Embed(color=Color.SOFT_RED)
    embed.add_field(name="Message", value=f"```{cont}```", inline=False)
    embed.add_field(name="Trigger channel", value=chan, inline=False)
    embed.add_field(name="Error", value=str(e), inline=False)
    return embed


def setup(bot: Bot) -> None:
    """Automatically called during bot setup."""
    bot.add_cog(ErrorHandler())
