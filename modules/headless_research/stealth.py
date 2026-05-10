"""
Stealth Module for Headless Browser
Implements anti-detection techniques to bypass bot protection.
Inspired by HeadlessX's stealth architecture.
"""
import random
import logging
from fake_useragent import UserAgent

logger = logging.getLogger("headless_research.stealth")

# Common Stealth Scripts to inject
STEALTH_SCRIPTS = [
    # Mask navigator.webdriver
    """
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    """,
    # Mask Chrome runtime
    """
    window.chrome = {
        runtime: {}
    };
    """,
    # Spoof Plugins
    """
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });
    """,
    # Spoof Languages
    """
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });
    """
]

class StealthContext:
    def __init__(self):
        self.ua = UserAgent(platforms='pc')
    
    def get_random_user_agent(self) -> str:
        """Get a realistic desktop User-Agent."""
        try:
            return self.ua.random
        except Exception:
            # Fallback if fake-useragent fails
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def get_stealth_args(self) -> list:
        """Get Playwright launch arguments for stealth."""
        return [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-notifications",
            "--no-first-run",
            "--no-service-autorun",
            "--password-store=basic"
        ]
    
    async def apply_stealth(self, page):
        """Inject stealth scripts into a Playwright page."""
        try:
            for script in STEALTH_SCRIPTS:
                await page.add_init_script(script)
            
            # Additional evasion: Hardware concurrency
            await page.add_init_script("""
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 4
                });
            """)
            
            # Mask WebGL Vendor
            await page.add_init_script("""
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    // UNMASKED_VENDOR_WEBGL
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    // UNMASKED_RENDERER_WEBGL
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter(parameter);
                };
            """)
            
            logger.debug("Stealth scripts injected successfully.")
        except Exception as e:
            logger.error(f"Failed to apply stealth: {e}")
