"""Thread creation utilities with private thread fallback."""

from typing import TYPE_CHECKING

import discord
from discord import ChannelType

from vezbot.utils.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from vezbot.bot import Vezbot


async def create_ticket_thread(
    channel: discord.TextChannel,
    name: str,
    creator: discord.Member,
    bot: "Vezbot",
    reason: str = "Ticket creation",
) -> tuple[discord.Thread, bool]:
    """
    Create a ticket thread, attempting private thread first.

    Returns:
        Tuple of (thread, is_private)
    """
    # Attempt private thread first
    try:
        thread = await channel.create_thread(
            name=name,
            type=ChannelType.private_thread,
            reason=reason,
        )
        logger.info(
            f"Created private thread {thread.id} in channel {channel.id}",
            guild_id=channel.guild.id,
            thread_id=thread.id,
        )
        return thread, True
    except discord.Forbidden:
        logger.warning(
            f"Private threads not available in {channel.id}, falling back to public thread",
            guild_id=channel.guild.id,
            channel_id=channel.id,
        )
    except discord.HTTPException as e:
        # Check if it's a private thread availability issue
        if "private" in str(e).lower() or "PRIVATE_THREADS" in str(e):
            logger.warning(
                f"Private threads not available: {e}, falling back to public thread",
                guild_id=channel.guild.id,
                channel_id=channel.id,
            )
        else:
            raise

    # Fallback to public thread with restricted permissions
    try:
        thread = await channel.create_thread(
            name=name,
            type=ChannelType.public_thread,
            reason=reason,
        )

        # Set permissions: deny @everyone, allow creator and staff
        everyone = channel.guild.default_role
        overwrites = {
            everyone: discord.PermissionOverwrite(view_channel=False),
            creator: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        # Add staff roles (you may want to fetch from config)
        # For now, we'll add the creator and let staff be added manually

        await thread.edit(overwrites=overwrites)

        logger.info(
            f"Created public thread {thread.id} with restricted permissions",
            guild_id=channel.guild.id,
            thread_id=thread.id,
        )
        return thread, False
    except Exception as e:
        logger.error(f"Failed to create public thread: {e}", guild_id=channel.guild.id)
        raise
