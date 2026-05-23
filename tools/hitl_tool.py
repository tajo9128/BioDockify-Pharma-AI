"""HITL Tool — agent manages human-in-the-loop intervention gates."""
from helpers.tool import Tool, Response


class HitlTool(Tool):
    async def execute(self, action: str = "status", **kwargs):
        if action == "init":
            pid = kwargs.get("pipeline_id", "")
            mode = kwargs.get("mode", "co_pilot")
            if not pid:
                return Response(message="Provide pipeline_id. Use: HITL action=init pipeline_id=ID mode=co_pilot", break_loop=False)
            lines = [f"=== HITL INIT: {pid} ===", f"Mode: {mode}", "=" * 40]
            lines.append("Call POST /api/hitl action=init to start intervention tracking.")
            return Response(message="\n".join(lines), break_loop=False)

        if action == "status":
            pid = kwargs.get("pipeline_id", "")
            if not pid:
                return Response(message="Provide pipeline_id. Use: HITL action=status pipeline_id=ID", break_loop=False)
            return Response(message="Call POST /api/hitl action=status to get gate approval state.", break_loop=False)

        if action == "approve":
            pid = kwargs.get("pipeline_id", "")
            gate_id = kwargs.get("gate_id", "")
            comment = kwargs.get("comment", "")
            if not pid or not gate_id:
                return Response(message="Provide pipeline_id and gate_id. Use: HITL action=approve pipeline_id=ID gate_id=5 comment=\"LGTM\"", break_loop=False)
            lines = [f"=== HITL APPROVE ===", f"Pipeline: {pid}, Gate: {gate_id}", "=" * 40]
            lines.append(f"Comment: {comment}")
            lines.append("Call POST /api/hitl action=approve to approve this gate.")
            return Response(message="\n".join(lines), break_loop=False)

        if action == "reject":
            pid = kwargs.get("pipeline_id", "")
            gate_id = kwargs.get("gate_id", "")
            reason = kwargs.get("reason", "")
            if not pid or not gate_id:
                return Response(message="Provide pipeline_id, gate_id, and reason.", break_loop=False)
            return Response(message=f"Gate {gate_id} rejection recorded. Reason: {reason}", break_loop=False)

        if action == "modes":
            lines = ["=== HITL INTERVENTION MODES ===", "=" * 40]
            for mode, info in {"full_auto":"Fully autonomous","gate_only":"Pause at 3 gates","checkpoint":"Pause at 9 phases","co_pilot":"Deep collaboration","step_by_step":"Pause every stage","express":"Quick review","regulatory":"FDA/EMA compliance","custom":"User-defined"}.items():
                lines.append(f"  {mode}: {info}")
            return Response(message="\n".join(lines), break_loop=False)

        return Response(message="HITL actions: init, status, approve, reject, collaborate, inject_guidance, modes", break_loop=False)
