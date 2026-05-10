"""
Channels API Routes - Telegram, WhatsApp, Discord, Feishu configuration and control.

Endpoints:
- GET /api/channels/status - Get status of all messaging channels
- POST /api/channels/telegram - Configure Telegram bot
- POST /api/channels/whatsapp - Configure WhatsApp
- POST /api/channels/discord - Configure Discord bot
- POST /api/channels/start - Start all enabled channels
- POST /api/channels/stop - Stop all channels
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/channels", tags=["Messaging Channels"])


# ========== Request Models ==========

class TelegramConfigRequest(BaseModel):
    enabled: bool
    token: str
    allowed_users: Optional[List[str]] = None


class WhatsAppConfigRequest(BaseModel):
    enabled: bool
    phone_id: str
    access_token: str
    verify_token: str


class DiscordConfigRequest(BaseModel):
    enabled: bool
    token: str
    allowed_guilds: Optional[List[str]] = None


class FeishuConfigRequest(BaseModel):
    enabled: bool
    app_id: str
    app_secret: str


# ========== Helper Function ==========

def get_channels():
    """Get channels instance."""
    try:
        from agent_zero.channels import get_channels
        return get_channels()
    except ImportError:
        raise HTTPException(status_code=503, detail="Channels integration not available")


# ========== Endpoints ==========

@router.get("/status")
async def get_channels_status():
    """Get status of all messaging channels."""
    channels = get_channels()
    return channels.get_status()


@router.post("/telegram")
async def configure_telegram(request: TelegramConfigRequest):
    """Configure Telegram bot."""
    channels = get_channels()
    channels.update_telegram(
        enabled=request.enabled,
        token=request.token,
        allowed_users=request.allowed_users
    )
    return {"status": "ok", "message": "Telegram configuration updated"}


@router.post("/whatsapp")
async def configure_whatsapp(request: WhatsAppConfigRequest):
    """Configure WhatsApp."""
    channels = get_channels()
    channels.update_whatsapp(
        enabled=request.enabled,
        phone_id=request.phone_id,
        access_token=request.access_token,
        verify_token=request.verify_token
    )
    return {"status": "ok", "message": "WhatsApp configuration updated"}


@router.post("/discord")
async def configure_discord(request: DiscordConfigRequest):
    """Configure Discord bot."""
    channels = get_channels()
    channels.update_discord(
        enabled=request.enabled,
        token=request.token,
        allowed_guilds=request.allowed_guilds
    )
    return {"status": "ok", "message": "Discord configuration updated"}


@router.post("/feishu")
async def configure_feishu(request: FeishuConfigRequest):
    """Configure Feishu/Lark."""
    channels = get_channels()
    # Update feishu config
    channels.config.feishu.enabled = request.enabled
    channels.config.feishu.app_id = request.app_id
    channels.config.feishu.app_secret = request.app_secret
    channels._save_config()
    return {"status": "ok", "message": "Feishu configuration updated"}


@router.post("/start")
async def start_channels():
    """Start all enabled messaging channels."""
    channels = get_channels()
    try:
        await channels.start_channels()
        return {"status": "ok", "message": "Channels started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_channels():
    """Stop all messaging channels."""
    channels = get_channels()
    await channels.stop_channels()
    return {"status": "ok", "message": "Channels stopped"}
