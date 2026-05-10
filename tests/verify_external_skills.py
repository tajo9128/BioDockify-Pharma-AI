import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from nanobot.agent.tools.calendar import CalendarTool
from nanobot.agent.tools.todoist import TaskTool
from nanobot.agent.tools.discord import DiscordTool

async def test_calendar():
    print("\n--- Testing CalendarTool ---")
    tool = CalendarTool()
    schema = tool.to_schema()
    print(f"Schema Name: {schema['name']}")
    
    # Test execution (expecting error if gcalcli invalid)
    res = await tool.execute("agenda")
    print(f"Result (Agenda): {res}")

async def test_todoist():
    print("\n--- Testing TaskTool (Todoist) ---")
    tool = TaskTool()
    schema = tool.to_schema()
    print(f"Schema Name: {schema['name']}")

    # Test execution (expecting error if lib missing)
    res = await tool.execute("list")
    print(f"Result (List): {res}")

async def test_discord():
    print("\n--- Testing DiscordTool ---")
    tool = DiscordTool(token="FAKE_TOKEN")
    schema = tool.to_schema()
    print(f"Schema Name: {schema['name']}")

    # Test execution (expecting 401/error with fake token)
    res = await tool.execute("announce", channel_id="123", content="Hello")
    print(f"Result (Announce): {res}")

async def main():
    await test_calendar()
    await test_todoist()
    await test_discord()

if __name__ == "__main__":
    asyncio.run(main())
