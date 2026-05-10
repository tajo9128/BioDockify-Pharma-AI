import asyncio
import logging
from nanobot.supervisor.execution_supervisor import ExecutionSupervisor

async def main():
    """
    Main entry point for NanoBot Execution Supervisor.
    """
    # Configure structured logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    supervisor = ExecutionSupervisor(check_interval=10) # Faster for demo/test
    
    try:
        await supervisor.start()
        
        # Keep alive - in a real app, this would be part of the main NanoBot process
        while True:
            await asyncio.sleep(3600)
            
    except asyncio.CancelledError:
        supervisor.stop()
    except KeyboardInterrupt:
        supervisor.stop()

if __name__ == "__main__":
    asyncio.run(main())
