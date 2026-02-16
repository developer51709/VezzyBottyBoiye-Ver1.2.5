# Vezbot Dashboard

## Overview
A monorepo containing a Discord bot (Python) and its web dashboard (Next.js). The dashboard provides server configuration, ticket management, and branding customization for the Vezbot Discord bot.

## Project Architecture
- `apps/dashboard/` - Next.js 16 frontend dashboard (TypeScript, Tailwind CSS, Radix UI)
- `apps/bot/` - Python Discord bot with FastAPI backend (requires Discord API tokens)
- `packages/shared/` - Shared schemas and configuration

## Running
- **Dashboard**: Runs on port 5000 via `cd apps/dashboard && npm run dev`
- **Bot**: Requires Discord API tokens and database setup (not run by default)

## Key Configuration
- Next.js configured with `allowedDevOrigins` for Replit proxy compatibility
- Dashboard uses next-auth with Discord OAuth for authentication
- Bot uses PostgreSQL (asyncpg), Redis, and Discord.py

## Recent Changes
- 2026-02-16: Imported project, upgraded Next.js from 14.x to 16.x for Replit compatibility
- 2026-02-16: Configured dev server to bind to 0.0.0.0:5000
