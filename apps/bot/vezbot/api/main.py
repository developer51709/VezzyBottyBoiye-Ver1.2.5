"""FastAPI application for webhooks."""

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from vezbot.config import settings
from vezbot.database import AsyncSessionLocal
from vezbot.integrations.twitch import TwitchIntegration
from vezbot.models.integrations import IntegrationConfig
from vezbot.utils.logging import configure_logging, get_logger

configure_logging(settings.log_level)
logger = get_logger(__name__)

app = FastAPI(title="Vezbot API")


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "vezbot-api", "status": "running"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/webhooks/twitch")
async def twitch_webhook(request: Request) -> Response:
    """Handle Twitch EventSub webhook."""
    # Handle challenge
    body = await request.body()
    body_str = body.decode()

    try:
        import json

        data = json.loads(body_str)
        if data.get("challenge"):
            # Return challenge for verification
            return Response(content=data["challenge"], media_type="text/plain")
    except Exception:
        pass

    # Get signature
    signature = request.headers.get("twitch-eventsub-message-signature", "")

    # Find matching integration config
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(IntegrationConfig).where(
                IntegrationConfig.provider == "twitch",
                IntegrationConfig.enabled == True,
            )
        )
        configs = result.scalars().all()

        for config in configs:
            integration = TwitchIntegration(config)
            payload = {"headers": {"twitch-eventsub-message-signature": signature}, "body": body_str}
            await integration.handle_webhook(payload)

    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
