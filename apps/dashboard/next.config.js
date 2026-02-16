/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ['*.replit.dev', 'a0671a90-d05b-482a-97f6-b6ef9bd00a3a-00-3q0gmahupchg6.kirk.replit.dev'],
  env: {
    NEXT_PUBLIC_DISCORD_CLIENT_ID: process.env.NEXT_PUBLIC_DISCORD_CLIENT_ID,
    NEXT_PUBLIC_DASHBOARD_URL: process.env.NEXT_PUBLIC_DASHBOARD_URL,
  },
}

module.exports = nextConfig
