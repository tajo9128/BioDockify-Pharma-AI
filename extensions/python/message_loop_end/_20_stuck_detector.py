from helpers.extension import Extension
from agent import Agent, LoopData, StuckState
from helpers.print_style import PrintStyle
from tools.response import ResponseTool

SAFETY_MAX_ITERATIONS = 40

class StuckDetector(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not self.agent:
            return
        if not hasattr(loop_data, "iteration"):
            return

        iters = loop_data.iteration
        if iters < 5:
            return

        stuck: StuckState = self.agent.data.setdefault("_stuck_state", StuckState())
        fails = stuck.consecutive_fails

        if iters >= SAFETY_MAX_ITERATIONS and fails >= 3 and stuck.escalation_level < 5:
            stuck.escalation_level = 5
            PrintStyle(font_color="red", padding=True).print(
                f"🛑 Safety net: {iters} iterations with {fails} failures. Breaking loop."
            )
            self.agent.hist_add_warning(
                f"[Safety Net] Agent exceeded {SAFETY_MAX_ITERATIONS} iterations "
                f"with {fails} consecutive failures. Breaking loop."
            )
            tool = ResponseTool(
                agent=self.agent, name="response", method=None,
                args={}, message="", loop_data=loop_data,
            )
            resp = await tool.execute(
                text="I've been unable to complete this request after multiple attempts. "
                     "Please rephrase or try a different approach."
            )
            if resp.break_loop:
                await tool.after_execution(resp)

        if stuck.escalation_level >= 4:
            from helpers import cache
            cache.clear_all()
            PrintStyle(font_color="yellow", padding=True).print(
                "⟳ Safety net: cleared all caches after level 4+ stuck detection."
            )
