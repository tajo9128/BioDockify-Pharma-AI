"""
Telegram Channel - Integration with Telegram Bot API.
"""
from typing import Optional
import logging
from agent_zero.hybrid.channels.base import BaseChannel
from agent_zero.hybrid.bus import MessageBus, OutboundMessage

logger = logging.getLogger(__name__)

class TelegramChannel(BaseChannel):
    """Telegram Bot integration."""
    
    def __init__(self, bus: MessageBus, config: dict):
        super().__init__("telegram", bus, config)
        self.token = config.get("token", "")
        self.app = None
        
    async def _connect(self):
        if not self.token:
            logger.error("Telegram token missing!")
            self.enabled = False
            return
            
        try:
            # Import here to avoid hard dependency if not used
            from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
            from telegram import Update
            
            self.app = ApplicationBuilder().token(self.token).build()
            
            # Register handlers
            async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
                if not update.message or not update.message.text:
                    return
                    
                user = update.effective_user
                chat_id = str(update.effective_chat.id)
                
                await self.process_incoming(
                    content=update.message.text,
                    sender_id=str(user.id),
                    sender_name=user.full_name,
                    chat_id=chat_id,
                    raw_data=update.to_dict()
                )
                
            self.app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
            
            # Start polling in background
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            logger.info("Telegram channel connected via polling")
            
        except ImportError:
            logger.error("python-telegram-bot not installed. Telegram channel disabled.")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to connect Telegram: {e}")
            self.enabled = False
            
    async def _disconnect(self):
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            
    async def send_message(self, message: OutboundMessage):
        if not self.app:
            return
            
        try:
            await self.app.bot.send_message(
                chat_id=int(message.chat_id),
                text=message.content,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
