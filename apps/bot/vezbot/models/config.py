"""Guild configuration models."""

from typing import Any

from sqlalchemy import BigInteger, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vezbot.models.base import Base, TimestampMixin


class GuildConfig(Base, TimestampMixin):
    """Guild configuration and module settings."""

    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Discord guild ID
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    brand: Mapped["GuildBrand"] = relationship(
        "GuildBrand", back_populates="guild", uselist=False
    )

    def __repr__(self) -> str:
        return f"<GuildConfig(id={self.id})>"


class GuildBrand(Base, TimestampMixin):
    """Guild branding configuration."""

    __tablename__ = "guild_brands"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.id"), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    primary_color: Mapped[int] = mapped_column(default=0x5865F2)  # Discord blurple
    accent_color: Mapped[int] = mapped_column(default=0x57F287)  # Discord green
    neutral_color: Mapped[int] = mapped_column(default=0x2F3136)  # Discord dark
    footer_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tagline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    microcopy_voice: Mapped[str] = mapped_column(
        String(50), default="casual"
    )  # formal, casual, mystic
    embed_tone_preset: Mapped[str] = mapped_column(
        String(50), default="scroll"
    )  # scroll, codex, dispatch, decree

    # Relationships
    guild: Mapped["GuildConfig"] = relationship(
        "GuildConfig", back_populates="brand", foreign_keys=[guild_id]
    )

    def __repr__(self) -> str:
        return f"<GuildBrand(guild_id={self.guild_id}, display_name={self.display_name})>"
