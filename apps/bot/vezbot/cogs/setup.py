"""Setup wizard cog."""

from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from vezbot.database import AsyncSessionLocal
from vezbot.repositories import GuildBrandRepository, GuildRepository
from vezbot.services.branding_service import build_lore_embed, get_default_brand
from vezbot.utils.logging import get_logger
from vezbot.utils.permissions import is_admin

logger = get_logger(__name__)


class SetupView(discord.ui.View):
    """Setup wizard view with buttons."""

    def __init__(self, cog: "SetupCog", interaction: discord.Interaction) -> None:
        super().__init__(timeout=300.0)
        self.cog = cog
        self.original_interaction = interaction
        self.state: dict = {}

    @discord.ui.button(label="Begin Setup", style=discord.ButtonStyle.primary)
    async def begin_setup(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Start setup wizard."""
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        embed = build_lore_embed(
            get_default_brand(interaction.guild.id),
            title="Setup Wizard - Step 1",
            description="Let's configure your server. First, select the ticket hub channel.",
        )

        view = ChannelSelectView(self.cog, self, "ticket_hub")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Cancel setup."""
        await interaction.response.send_message("Setup cancelled.", ephemeral=True)
        self.stop()


class ChannelSelectView(discord.ui.View):
    """Channel selection view."""

    def __init__(
        self, cog: "SetupCog", parent_view: SetupView, step: str
    ) -> None:
        super().__init__(timeout=300.0)
        self.cog = cog
        self.parent_view = parent_view
        self.step = step

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        placeholder="Select a channel...",
        channel_types=[discord.ChannelType.text],
    )
    async def channel_select(
        self, interaction: discord.Interaction, select: discord.ui.ChannelSelect
    ) -> None:
        """Handle channel selection."""
        if not select.values:
            await interaction.response.send_message(
                "Please select a channel.", ephemeral=True
            )
            return

        channel = select.values[0]
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "Please select a text channel.", ephemeral=True
            )
            return

        # Validate permissions
        me = channel.guild.get_member(interaction.client.user.id) if interaction.client.user else None
        if not me:
            await interaction.response.send_message(
                "Unable to verify bot permissions.", ephemeral=True
            )
            return

        perms = channel.permissions_for(me)
        if not (perms.view_channel and perms.manage_threads):
            await interaction.response.send_message(
                "Bot needs 'View Channel' and 'Manage Threads' permissions in this channel.",
                ephemeral=True,
            )
            return

        self.parent_view.state["ticket_hub_channel_id"] = channel.id

        # Test private thread capability
        can_private = await self.cog.test_private_threads(channel)

        if can_private:
            embed = build_lore_embed(
                get_default_brand(interaction.guild.id),
                title="Setup Wizard - Step 2",
                description=f"✅ Private threads are available in {channel.mention}.\n\nSelect staff roles:",
            )
            self.parent_view.state["use_private_threads"] = True
        else:
            embed = build_lore_embed(
                get_default_brand(interaction.guild.id),
                title="Setup Wizard - Step 2",
                description=(
                    f"⚠️ Private threads are not available in {channel.mention}.\n"
                    "The bot will use public threads with restricted permissions instead.\n\n"
                    "Select staff roles:"
                ),
            )
            self.parent_view.state["use_private_threads"] = False

        view = RoleSelectView(self.cog, self.parent_view)
        await interaction.response.edit_message(embed=embed, view=view)


class RoleSelectView(discord.ui.View):
    """Role selection view."""

    def __init__(self, cog: "SetupCog", parent_view: SetupView) -> None:
        super().__init__(timeout=300.0)
        self.cog = cog
        self.parent_view = parent_view

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Select staff roles...", min_values=1, max_values=10)
    async def role_select(
        self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ) -> None:
        """Handle role selection."""
        if not select.values:
            await interaction.response.send_message(
                "Please select at least one role.", ephemeral=True
            )
            return

        self.parent_view.state["staff_role_ids"] = [role.id for role in select.values]

        # Module selection
        embed = build_lore_embed(
            get_default_brand(interaction.guild.id),
            title="Setup Wizard - Step 3",
            description="Enable modules:",
        )

        view = ModuleSelectView(self.cog, self.parent_view)
        await interaction.response.edit_message(embed=embed, view=view)


class ModuleSelectView(discord.ui.View):
    """Module selection view."""

    def __init__(self, cog: "SetupCog", parent_view: SetupView) -> None:
        super().__init__(timeout=300.0)
        self.cog = cog
        self.parent_view = parent_view
        self.parent_view.state["modules"] = {
            "tickets": True,  # Always enabled
            "embeds": False,
            "polls": False,
            "reminders": False,
        }

    @discord.ui.button(label="Tickets ✓", style=discord.ButtonStyle.success, disabled=True)
    async def tickets_toggle(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Tickets are always enabled."""
        await interaction.response.defer()

    @discord.ui.button(label="Embeds", style=discord.ButtonStyle.secondary)
    async def embeds_toggle(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Toggle embeds module."""
        enabled = self.parent_view.state["modules"]["embeds"]
        self.parent_view.state["modules"]["embeds"] = not enabled
        button.label = f"Embeds {'✓' if not enabled else ''}"
        button.style = discord.ButtonStyle.success if not enabled else discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Polls", style=discord.ButtonStyle.secondary)
    async def polls_toggle(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Toggle polls module."""
        enabled = self.parent_view.state["modules"]["polls"]
        self.parent_view.state["modules"]["polls"] = not enabled
        button.label = f"Polls {'✓' if not enabled else ''}"
        button.style = discord.ButtonStyle.success if not enabled else discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Reminders", style=discord.ButtonStyle.secondary)
    async def reminders_toggle(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Toggle reminders module."""
        enabled = self.parent_view.state["modules"]["reminders"]
        self.parent_view.state["modules"]["reminders"] = not enabled
        button.label = f"Reminders {'✓' if not enabled else ''}"
        button.style = discord.ButtonStyle.success if not enabled else discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.primary, row=1)
    async def continue_setup(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Continue to review."""
        embed = await self.cog.build_review_embed(interaction.guild, self.parent_view.state)
        view = ReviewView(self.cog, self.parent_view)
        await interaction.response.edit_message(embed=embed, view=view)


class ReviewView(discord.ui.View):
    """Review and save view."""

    def __init__(self, cog: "SetupCog", parent_view: SetupView) -> None:
        super().__init__(timeout=300.0)
        self.cog = cog
        self.parent_view = parent_view

    @discord.ui.button(label="Save & Activate", style=discord.ButtonStyle.success)
    async def save(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Save configuration."""
        await interaction.response.defer(ephemeral=True)

        try:
            await self.cog.save_config(interaction.guild, self.parent_view.state)
            embed = build_lore_embed(
                get_default_brand(interaction.guild.id),
                title="Setup Complete",
                description="Your server has been configured successfully!",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to save config: {e}", guild_id=interaction.guild.id)
            await interaction.followup.send(
                f"Failed to save configuration: {str(e)}", ephemeral=True
            )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Cancel setup."""
        await interaction.response.send_message("Setup cancelled.", ephemeral=True)
        self.stop()


class SetupCog(commands.Cog):
    """Setup wizard cog."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="setup", description="Run the setup wizard")
    @is_admin()
    async def setup(self, interaction: discord.Interaction) -> None:
        """Start setup wizard."""
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        brand = get_default_brand(interaction.guild.id)
        embed = build_lore_embed(
            brand,
            title="Welcome to Vezbot Setup",
            description=(
                "This wizard will guide you through configuring your server.\n\n"
                "You can run this wizard again at any time to update your settings."
            ),
        )

        view = SetupView(self, interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def test_private_threads(self, channel: discord.TextChannel) -> bool:
        """Test if private threads are available."""
        try:
            # Try to create a test thread (we'll delete it immediately)
            test_thread = await channel.create_thread(
                name="test-private-thread-check",
                type=discord.ChannelType.private_thread,
            )
            await test_thread.delete()
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False

    async def build_review_embed(
        self, guild: discord.Guild, state: dict
    ) -> discord.Embed:
        """Build review summary embed."""
        brand = get_default_brand(guild.id)

        channel = guild.get_channel(state.get("ticket_hub_channel_id", 0))
        channel_mention = channel.mention if channel else "Not set"

        staff_roles = [
            guild.get_role(rid) for rid in state.get("staff_role_ids", [])
        ]
        role_mentions = ", ".join(r.mention for r in staff_roles if r) or "None"

        modules = state.get("modules", {})
        enabled_modules = [k for k, v in modules.items() if v]

        fields = [
            {"name": "Ticket Hub", "value": channel_mention, "inline": True},
            {"name": "Thread Type", "value": "Private" if state.get("use_private_threads") else "Public (Restricted)", "inline": True},
            {"name": "Staff Roles", "value": role_mentions, "inline": False},
            {"name": "Enabled Modules", "value": ", ".join(enabled_modules) or "None", "inline": False},
        ]

        return build_lore_embed(
            brand,
            title="Setup Review",
            description="Review your configuration:",
            fields=fields,
        )

    async def save_config(self, guild: discord.Guild, state: dict) -> None:
        """Save configuration to database."""
        async with AsyncSessionLocal() as session:
            # Save guild config
            guild_repo = GuildRepository(session)
            config = await guild_repo.get_or_create(guild.id)
            config.config_json = {
                "ticket_hub_channel_id": state.get("ticket_hub_channel_id"),
                "use_private_threads": state.get("use_private_threads", True),
                "staff_role_ids": state.get("staff_role_ids", []),
                "modules": state.get("modules", {}),
            }
            await session.commit()

            logger.info(
                "Configuration saved",
                guild_id=guild.id,
                ticket_hub=state.get("ticket_hub_channel_id"),
            )


async def setup(bot: commands.Bot) -> None:
    """Load the cog."""
    await bot.add_cog(SetupCog(bot))
