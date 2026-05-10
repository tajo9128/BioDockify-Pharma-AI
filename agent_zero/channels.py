"""
Agent Zero Channels - Telegram, WhatsApp, Discord, Feishu Integration

Provides messaging channel integration for Agent Zero using NanoBot's channel system.
Users can chat with Agent Zero via:
- Telegram Bot
- WhatsApp (via webhook)
- Discord Bot
- Feishu (Lark)

Configuration is stored in runtime config and services/channels.json
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from loguru import logger

# Robust path resolution
BASE_DIR = Path(__file__).parent.parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "channels.json"


@dataclass
class TelegramConfig:
    """Telegram channel configuration."""
    enabled: bool = False
    token: str = ""
    allowed_users: list[str] = field(default_factory=list)


@dataclass
class WhatsAppConfig:
    """WhatsApp channel configuration."""
    enabled: bool = False
    phone_id: str = ""
    access_token: str = ""
    verify_token: str = ""
    allowed_users: list[str] = field(default_factory=list)


@dataclass
class DiscordConfig:
    """Discord channel configuration."""
    enabled: bool = False
    token: str = ""
    allowed_guilds: list[str] = field(default_factory=list)


@dataclass
class FeishuConfig:
    """Feishu/Lark channel configuration."""
    enabled: bool = False
    app_id: str = ""
    app_secret: str = ""


@dataclass
class ChannelsConfig:
    """All channels configuration."""
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    whatsapp: WhatsAppConfig = field(default_factory=WhatsAppConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    feishu: FeishuConfig = field(default_factory=FeishuConfig)


class AgentZeroChannels:
    """
    Multi-channel messaging for Agent Zero.
    
    Enables Agent Zero to be accessed via Telegram, WhatsApp, Discord, Feishu.
    """
    
    _instance = None
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = str(DEFAULT_CONFIG_PATH)
        self.config_path = Path(config_path)
        self.config: ChannelsConfig = ChannelsConfig()
        self._channel_manager = None
        self._bus = None
        self._running = False
        
        self._load_config()
    
    @classmethod
    def get_instance(cls) -> "AgentZeroChannels":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _load_config(self) -> None:
        """Load channels configuration from file."""
        import json
        
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text())
                
                if "telegram" in data:
                    self.config.telegram = TelegramConfig(**data["telegram"])
                if "whatsapp" in data:
                    self.config.whatsapp = WhatsAppConfig(**data["whatsapp"])
                if "discord" in data:
                    self.config.discord = DiscordConfig(**data["discord"])
                if "feishu" in data:
                    self.config.feishu = FeishuConfig(**data["feishu"])
                    
                logger.info(f"Channels config loaded from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load channels config: {e}")
    
    def _save_config(self) -> None:
        """Save channels configuration to file."""
        import json
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "telegram": {
                "enabled": self.config.telegram.enabled,
                "token": self.config.telegram.token,
                "allowed_users": self.config.telegram.allowed_users,
            },
            "whatsapp": {
                "enabled": self.config.whatsapp.enabled,
                "phone_id": self.config.whatsapp.phone_id,
                "access_token": self.config.whatsapp.access_token,
                "verify_token": self.config.whatsapp.verify_token,
                "allowed_users": self.config.whatsapp.allowed_users,
            },
            "discord": {
                "enabled": self.config.discord.enabled,
                "token": self.config.discord.token,
                "allowed_guilds": self.config.discord.allowed_guilds,
            },
            "feishu": {
                "enabled": self.config.feishu.enabled,
                "app_id": self.config.feishu.app_id,
                "app_secret": self.config.feishu.app_secret,
            }
        }
        
        self.config_path.write_text(json.dumps(data, indent=2))
        logger.info(f"Channels config saved to {self.config_path}")
    
    def update_telegram(self, enabled: bool, token: str, allowed_users: list[str] = None) -> None:
        """Update Telegram configuration."""
        self.config.telegram.enabled = enabled
        self.config.telegram.token = token
        if allowed_users is not None:
            self.config.telegram.allowed_users = allowed_users
        self._save_config()
    
    def update_whatsapp(self, enabled: bool, phone_id: str, access_token: str, verify_token: str) -> None:
        """Update WhatsApp configuration."""
        self.config.whatsapp.enabled = enabled
        self.config.whatsapp.phone_id = phone_id
        self.config.whatsapp.access_token = access_token
        self.config.whatsapp.verify_token = verify_token
        self._save_config()
    
    def update_discord(self, enabled: bool, token: str, allowed_guilds: list[str] = None) -> None:
        """Update Discord configuration."""
        self.config.discord.enabled = enabled
        self.config.discord.token = token
        if allowed_guilds is not None:
            self.config.discord.allowed_guilds = allowed_guilds
        self._save_config()
    
    async def start_channels(self) -> None:
        """Start all enabled messaging channels."""
        if self._running:
            return
        
        try:
            from nanobot.bus.queue import MessageBus
            from nanobot.channels.manager import ChannelManager
            from nanobot.config.schema import Config
            
            # Create message bus
            self._bus = MessageBus()
            
            # Build NanoBot config from our config
            nanobot_config = self._build_nanobot_config()
            
            # Create channel manager
            self._channel_manager = ChannelManager(nanobot_config, self._bus)
            
            # Start channels
            self._running = True
            await self._channel_manager.start_all()
            
        except ImportError as e:
            logger.error(f"NanoBot channels not available: {e}")
        except Exception as e:
            logger.error(f"Failed to start channels: {e}")
    
    async def stop_channels(self) -> None:
        """Stop all messaging channels."""
        if not self._running:
            return
        
        self._running = False
        
        if self._channel_manager:
            await self._channel_manager.stop_all()
            self._channel_manager = None
    
    def _build_nanobot_config(self):
        """Build NanoBot Config object from our config."""
        # This is a simplified version - NanoBot expects its own Config schema
        # We create a compatible structure
        from types import SimpleNamespace
        
        config = SimpleNamespace()
        config.channels = SimpleNamespace()
        
        # Telegram
        config.channels.telegram = SimpleNamespace()
        config.channels.telegram.enabled = self.config.telegram.enabled
        config.channels.telegram.token = self.config.telegram.token
        config.channels.telegram.allowed_users = self.config.telegram.allowed_users
        
        # WhatsApp
        config.channels.whatsapp = SimpleNamespace()
        config.channels.whatsapp.enabled = self.config.whatsapp.enabled
        config.channels.whatsapp.phone_id = self.config.whatsapp.phone_id
        config.channels.whatsapp.access_token = self.config.whatsapp.access_token
        config.channels.whatsapp.verify_token = self.config.whatsapp.verify_token
        
        # Discord
        config.channels.discord = SimpleNamespace()
        config.channels.discord.enabled = self.config.discord.enabled
        config.channels.discord.token = self.config.discord.token
        
        # Feishu
        config.channels.feishu = SimpleNamespace()
        config.channels.feishu.enabled = self.config.feishu.enabled
        config.channels.feishu.app_id = self.config.feishu.app_id
        config.channels.feishu.app_secret = self.config.feishu.app_secret
        
        # Providers (for transcription)
        config.providers = SimpleNamespace()
        config.providers.groq = SimpleNamespace()
        config.providers.groq.api_key = ""
        
        return config
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all channels."""
        status = {
            "running": self._running,
            "channels": {}
        }
        
        # Add config status
        status["channels"]["telegram"] = {
            "configured": bool(self.config.telegram.token),
            "enabled": self.config.telegram.enabled,
            "running": False
        }
        status["channels"]["whatsapp"] = {
            "configured": bool(self.config.whatsapp.phone_id),
            "enabled": self.config.whatsapp.enabled,
            "running": False
        }
        status["channels"]["discord"] = {
            "configured": bool(self.config.discord.token),
            "enabled": self.config.discord.enabled,
            "running": False
        }
        status["channels"]["feishu"] = {
            "configured": bool(self.config.feishu.app_id),
            "enabled": self.config.feishu.enabled,
            "running": False
        }
        
        # Update with actual running status
        if self._channel_manager:
            manager_status = self._channel_manager.get_status()
            for name, s in manager_status.items():
                if name in status["channels"]:
                    status["channels"][name]["running"] = s.get("running", False)
        
        return status


def get_channels() -> AgentZeroChannels:
    """Get the Agent Zero channels instance."""
    return AgentZeroChannels.get_instance()
