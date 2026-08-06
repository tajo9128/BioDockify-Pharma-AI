"""
KB → Agent Memory Bridge

After each Agent Zero monologue, syncs recently-added Knowledge Base entries
into the agent's FAISS fragments store. This closes the loop: when Agent Zero
stores a docking result or literature search via auto_store(), it will
"remember" that it did so in future conversations, and can answer questions
like "what do we know about aspirin?" by recalling the KB entry it saved.

Only entries added since the last sync (tracked by timestamp in agent data)
are processed. Max 10 entries per monologue to avoid latency.
"""
import os
import json
import time
import logging

from helpers.extension import Extension
from helpers.defer import DeferredTask, THREAD_BACKGROUND
from agent import LoopData

log = logging.getLogger("kb_sync")

_KB_INDEX = os.path.realpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", "..", "data", "knowledge_base", "index.json"
))
_SYNC_KEY = "_kb_sync_last_ts"
_MAX_SYNC = 10


class KBMemorySync(Extension):
    """Sync new KB entries into agent FAISS memory after each monologue."""

    def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not self.agent:
            return

        task = DeferredTask(thread_name=THREAD_BACKGROUND)
        task.start_task(self._sync, loop_data)

    async def _sync(self, loop_data: LoopData, **kwargs):
        if not self.agent:
            return
        try:
            if not os.path.isfile(_KB_INDEX):
                return

            with open(_KB_INDEX, "r", encoding="utf-8") as f:
                index = json.load(f)

            entries = index.get("entries", [])
            if not entries:
                return

            # Retrieve last sync timestamp from agent data
            last_ts_str = self.agent.get_data(_SYNC_KEY) or ""
            last_ts = last_ts_str if last_ts_str else "1970-01-01 00:00:00"

            # Find entries added after last sync
            new_entries = [
                e for e in entries
                if e.get("created_at", "1970-01-01") > last_ts
            ][-_MAX_SYNC:]

            if not new_entries:
                return

            # Import memory system
            from plugins._memory.helpers.memory import Memory
            db = await Memory.get(self.agent)

            synced = 0
            for entry in new_entries:
                title = entry.get("title", "Untitled")
                category = entry.get("category", "misc")
                source = entry.get("source", "")
                created = entry.get("created_at", "")
                kb_id = entry.get("id", "")

                # Read a short excerpt from the .md file
                excerpt = ""
                fp = entry.get("file", "")
                if fp and os.path.isfile(fp):
                    try:
                        with open(fp, "r", encoding="utf-8") as f:
                            excerpt = f.read(600).strip()
                    except Exception:
                        pass

                fragment = (
                    f"[KB Entry stored] {title} | Category: {category}"
                    + (f" | Source: {source}" if source else "")
                    + (f" | Date: {created}" if created else "")
                    + (f"\nSummary: {excerpt[:400]}" if excerpt else "")
                    + f"\n[KB ID: {kb_id}]"
                )

                try:
                    await db.save(fragment, metadata={
                        "type": "kb_sync",
                        "kb_id": kb_id,
                        "category": category,
                        "title": title,
                    })
                    synced += 1
                except Exception as e:
                    log.debug(f"KB sync save failed for {kb_id}: {e}")

            if synced:
                # Update the last sync timestamp
                latest_ts = max(e.get("created_at", "") for e in new_entries)
                self.agent.set_data(_SYNC_KEY, latest_ts)
                log.info(f"KB sync: {synced} new entries added to agent memory")

        except Exception as e:
            log.debug(f"KB sync error: {e}")
