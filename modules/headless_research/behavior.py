"""
Behavior Module for Headless Browser
Simulates human-like interactions (mouse movements, scrolling, reading pauses).
"""
import asyncio
import random
import logging

logger = logging.getLogger("headless_research.behavior")

class HumanBehavior:
    def __init__(self):
        pass

    async def random_sleep(self, min_time: float = 0.5, max_time: float = 2.0):
        """Sleep for a random interval to simulate thinking/reading time."""
        delay = random.uniform(min_time, max_time)
        await asyncio.sleep(delay)

    async def smooth_scroll(self, page, distance: int = 100):
        """Simulate human-like scrolling."""
        try:
            # Scroll down in small steps
            for _ in range(random.randint(3, 7)):
                scroll_y = random.randint(50, 150)
                await page.mouse.wheel(0, scroll_y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
        except Exception as e:
            logger.debug(f"Scroll error: {e}")

    async def simulate_reading(self, page):
        """Simulate a user reading a page (scrolls, pauses, mouse moves)."""
        logger.debug("Simulating reading behavior...")
        
        # Initial pause
        await self.random_sleep(1.0, 3.0)
        
        # Move mouse randomly
        width = page.viewport_size['width']
        height = page.viewport_size['height']
        
        for _ in range(random.randint(2, 5)):
            x = random.randint(0, width)
            y = random.randint(0, height)
            await page.mouse.move(x, y, steps=10)
            await self.random_sleep(0.2, 0.8)
        
        # Scroll down lightly
        await self.smooth_scroll(page)
        
        # Pause again
        await self.random_sleep(1.0, 2.0)
