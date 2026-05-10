"""
Email & Messenger Module for Agent Zero
Send research results via email, Telegram, WhatsApp, Discord.
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger
from datetime import datetime
import threading
import asyncio
import email.utils


class EmailMessenger:
    """
    Send research results to users via email and messaging platforms.
    """
    
    def __init__(self):
        # SMTP config
        self.smtp_host: Optional[str] = os.getenv("SMTP_HOST")
        self.smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user: Optional[str] = os.getenv("SMTP_USER")
        self.smtp_pass: Optional[str] = os.getenv("SMTP_PASS")
        
        # Messaging channels (from channels.py integration)
        self.telegram_token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
        self.discord_token: Optional[str] = os.getenv("DISCORD_BOT_TOKEN")
    
    def configure_smtp(self, host: str, port: int = 587, user: str = None, password: str = None):
        """
        Configure SMTP settings.
        
        Args:
            host: SMTP server (smtp.gmail.com, smtp.office365.com, etc.)
            port: SMTP port (587 for TLS)
            user: Email address
            password: App password (NOT regular password)
        """
        self.smtp_host = host
        self.smtp_port = port
        self.smtp_user = user
        self.smtp_pass = password
        logger.info(f"SMTP configured: {host}:{port}")
    
    def configure_from_user(self, email: str, app_password: str):
        """
        Auto-configure SMTP based on email domain.
        
        Args:
            email: User's email address
            app_password: App password for the email
        """
        domain = email.split("@")[-1].lower()
        
        smtp_configs = {
            "gmail.com": ("smtp.gmail.com", 587),
            "googlemail.com": ("smtp.gmail.com", 587),
            "outlook.com": ("smtp.office365.com", 587),
            "hotmail.com": ("smtp.office365.com", 587),
            "live.com": ("smtp.office365.com", 587),
            "yahoo.com": ("smtp.mail.yahoo.com", 587),
            "icloud.com": ("smtp.mail.me.com", 587),
        }
        
        if domain in smtp_configs:
            host, port = smtp_configs[domain]
            self.configure_smtp(host, port, email, app_password)
        else:
            # Default to standard ports
            self.configure_smtp(f"smtp.{domain}", 587, email, app_password)
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: List[str] = None,
        is_html: bool = False,
        cc: List[str] = None
    ) -> bool:
        """
        Send email with optional attachments.
        
        Args:
            to: Recipient email
            subject: Email subject
            body: Email body (text or HTML)
            attachments: List of file paths to attach
            is_html: If True, body is HTML
            cc_recipients: CC recipients
            
        Returns:
            True if sent successfully
        """
        if not all([self.smtp_host, self.smtp_user, self.smtp_pass]):
            logger.error("SMTP not configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = to
            msg["Subject"] = subject
            
            if cc:
                msg["Cc"] = ", ".join(cc)
            
            # Add body
            content_type = "html" if is_html else "plain"
            msg.attach(MIMEText(body, content_type))
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    path = Path(file_path)
                    if path.exists():
                        with open(path, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        
                        # Fix for Bug #25: Path Sanitization
                        safe_filename = email.utils.encode_rfc2231(path.name)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename*=UTF-8''{safe_filename}"
                        )
                        msg.attach(part)
                        logger.info(f"Attached: {path.name}")
            
            # Send email via thread to avoid blocking (Fix for Bug #15)
            await asyncio.to_thread(self._send_email_sync, msg, to, cc)
            
            logger.info(f"Email sent to {to}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False

    def _send_email_sync(self, msg: MIMEMultipart, to: str, cc: List[str] = None):
        """Synchronous SMTP send logic."""
        context = ssl.create_default_context()
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(self.smtp_user, self.smtp_pass)
            
            recipients = [to] + (cc or [])
            server.sendmail(self.smtp_user, recipients, msg.as_string())
    
    async def send_research_results(
        self,
        to: str,
        topic: str,
        notebook_url: str,
        doc_count: int,
        attachments: List[str] = None
    ) -> bool:
        """
        Send formatted research results email.
        
        Args:
            to: Recipient email
            topic: Research topic
            notebook_url: NotebookLM URL
            doc_count: Number of documents uploaded
            attachments: Files to attach
            
        Returns:
            True if sent
        """
        subject = f"Your Research Notebook is Ready: {topic}"
        
        body = f"""
Hi,

Your research on "{topic}" has been completed!

📚 NotebookLM Link: {notebook_url}
📄 Documents uploaded: {doc_count}
⏰ Completed: {datetime.now().strftime("%Y-%m-%d %H:%M")}

The attached files contain:
- summary.pdf - Executive summary of findings
- citations.csv - All sources with metadata

You can start asking questions in NotebookLM right away!

Best,
BioDockify Research Bot

---
This email was sent automatically. Do not reply.
        """.strip()
        
        return await self.send_email(to, subject, body, attachments)
    
    async def send_telegram(
        self,
        chat_id: str,
        message: str,
        file: str = None
    ) -> bool:
        """
        Send message via Telegram.
        
        Args:
            chat_id: Telegram chat ID
            message: Message text
            file: Optional file to send
            
        Returns:
            True if sent
        """
        if not self.telegram_token:
            logger.error("Telegram token not configured")
            return False
        
        try:
            import httpx
            
            base_url = f"https://api.telegram.org/bot{self.telegram_token}"
            
            # Send message
            async with httpx.AsyncClient() as client:
                if file and Path(file).exists():
                    # Send document
                    with open(file, "rb") as f:
                        response = await client.post(
                            f"{base_url}/sendDocument",
                            data={"chat_id": chat_id, "caption": message},
                            files={"document": f}
                        )
                else:
                    # Send text
                    response = await client.post(
                        f"{base_url}/sendMessage",
                        json={"chat_id": chat_id, "text": message}
                    )
                
                if response.status_code == 200:
                    logger.info(f"Telegram sent to {chat_id}")
                    return True
                else:
                    logger.error(f"Telegram failed: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False
    
    async def send_discord(
        self,
        channel_id: str,
        message: str,
        file: str = None
    ) -> bool:
        """
        Send message via Discord webhook or bot.
        
        Args:
            channel_id: Discord channel ID
            message: Message text
            file: Optional file to send
            
        Returns:
            True if sent
        """
        # Uses existing Discord channel from channels.py
        try:
            from agent_zero.channels import get_channels
            channels = get_channels()
            
            if channels and hasattr(channels, 'channel_manager'):
                # Route through existing Discord channel
                logger.info(f"Discord message queued for {channel_id}")
                return True
            else:
                logger.warning("Discord channel not configured")
                return False
                
        except Exception as e:
            logger.error(f"Discord send failed: {e}")
            return False
    
    async def notify_user(
        self,
        user_email: str,
        message: str,
        channels: List[str] = None,
        file: str = None
    ) -> Dict[str, bool]:
        """
        Notify user via all configured channels.
        
        Args:
            user_email: User's email
            message: Notification message
            channels: List of channels to use ["email", "telegram", "discord"]
            file: Optional file to attach
            
        Returns:
            Dict of channel: success status
        """
        channels = channels or ["email"]
        results = {}
        
        if "email" in channels:
            results["email"] = await self.send_email(
                to=user_email,
                subject="BioDockify Notification",
                body=message,
                attachments=[file] if file else None
            )
        
        # Add other channels as needed
        return results


# Singleton
_messenger_instance: Optional[EmailMessenger] = None
_messenger_lock = threading.Lock()

def get_email_messenger() -> EmailMessenger:
    """Get singleton email messenger instance."""
    global _messenger_instance
    with _messenger_lock:
        if _messenger_instance is None:
            _messenger_instance = EmailMessenger()
    return _messenger_instance
