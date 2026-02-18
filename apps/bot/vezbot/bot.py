"""Discord bot instance and setup."""

import traceback
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from vezbot.config import settings
from vezbot.database import AsyncSessionLocal, get_session
from vezbot.models.audit import ErrorLog
from vezbot.utils.logging import get_logger, get_correlation_id, set_correlation_id

logger = get_logger(__name__)


class Vezbot(commands.Bot):
    """Main bot class."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self) -> None:
        """Called when bot is starting up."""
        logger.info("Setting up bot...")

        # Load cogs
        try:
            await self.load_extension("vezbot.cogs.setup")
        except Exception as e:
            logger.error(f"Failed to load setup cog: {e}")
        try:
            await self.load_extension("vezbot.cogs.tickets")
        except Exception as e:
            logger.error(f"Failed to load tickets cog: {e}")
        try:
            await self.load_extension("vezbot.cogs.embeds")
        except Exception as e:
            logger.error(f"Failed to load embeds cog: {e}")
        try:
            await self.load_extension("vezbot.cogs.polls")
        except Exception as e:
            logger.error(f"Failed to load polls cog: {e}")
        try:
            await self.load_extension("vezbot.cogs.reminders")
        except Exception as e:
            logger.error(f"Failed to load reminders cog: {e}")
        try:
            await self.load_extension("vezbot.cogs.admin")
        except Exception as e:
            logger.error(f"Failed to load admin cog: {e}")

        # Sync commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    async def on_ready(self) -> None:
        """Called when bot is ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """Handle app command errors."""
        correlation_id = get_correlation_id()
        set_correlation_id(correlation_id)

        # Log error
        error_msg = str(error)
        error_type = type(error).__name__
        stack_trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))

        logger.error(
            "Command error",
            error_type=error_type,
            error_message=error_msg,
            correlation_id=correlation_id,
            guild_id=interaction.guild_id,
            user_id=interaction.user.id,
            command=interaction.command.name if interaction.command else None,
        )

        # Save to error log
        try:
            async with AsyncSessionLocal() as session:
                error_log = ErrorLog(
                    guild_id=interaction.guild_id,
                    correlation_id=correlation_id,
                    error_type=error_type,
                    message=error_msg,
                    stack_trace=stack_trace,
                    context_json={
                        "command": interaction.command.name if interaction.command else None,
                        "user_id": interaction.user.id,
                    },
                )
                session.add(error_log)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to save error log: {e}")

        # User-friendly error message
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "You don't have permission to use this command.", ephemeral=True
            )
        elif isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"This command is on cooldown. Try again in {error.retry_after:.1f} seconds.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"An error occurred: {error_msg}", ephemeral=True
            )

    async def on_interaction(self, interaction: discord.Interaction) -> None:
        """Set correlation ID for each interaction."""
        set_correlation_id(get_correlation_id())


# Global bot instance
bot = Vezbot()
