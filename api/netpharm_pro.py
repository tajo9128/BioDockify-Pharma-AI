"""Network Pharmacology Pro API — additive extension (actions on netpharm.pro)."""
from helpers.api import ApiHandler, Request, Response
import json
import logging
import os

log = logging.getLogger("netpharm_pro")
STORE = "/a0/tmp/netpharm_pro" if os.name != "nt" else os.environ.get("NETPHARM_STORE", "tmp/netpharm_pro")


class NetpharmProHandler(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "")
        if action == "pathway_ora":
            return self._ora(input)
        elif action == "network_analysis":
            return self._network(input)
        elif action == "herb_network":
            return self._herb(input)
        elif action == "export_cytoscape":
            return self._export(input)

        return {"actions": ["pathway_ora", "network_analysis", "herb_network", "export_cytoscape"],
                "hint": "Network Pharmacology Pro — pathway ORA (BH FDR), PPI topology/hubs, "
                        "herb-compound-target multilayer with Cytoscape export."}

    @staticmethod
    def _ora(input: dict) -> dict:
        from modules.netpharm.pro import pathway_ora
        genes = input.get("genes") or []
        if isinstance(genes, str):
            genes = [g.strip() for g in genes.replace("\n", ",").split(",") if g.strip()]
        r = pathway_ora(genes)
        return {"success": "error" not in r, **r}

    @staticmethod
    def _network(input: dict) -> dict:
        from modules.netpharm.pro import network_analysis
        edges = input.get("edges") or []
        if isinstance(edges, str):  # "A,B\nA,C" tolerance
            edges = [l.split(",")[:2] for l in edges.splitlines() if "," in l]
        r = network_analysis(edges, int(input.get("hubs_top", 10) or 10))
        return {"success": "error" not in r, **r}

    @staticmethod
    def _herb(input: dict) -> dict:
        from modules.netpharm.pro import herb_network
        herbs = input.get("herbs") or []
        if not herbs:
            return {"error": "provide herbs: [{herb, compounds: [..]}]"}
        r = herb_network(herbs)
        return {"success": "error" not in r, **r}

    @staticmethod
    def _export(input: dict) -> dict:
        """Persist a network JSON for download (id → file in job dir)."""
        import uuid
        payload = input.get("network")
        if not payload:
            return {"error": "provide the network object (e.g. herb_network result)"}
        os.makedirs(STORE, exist_ok=True)
        fid = uuid.uuid4().hex[:8]
        with open(os.path.join(STORE, f"{fid}.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        return {"success": True, "file_id": fid,
                "hint": "GET /api/netpharm_pro?action=… returns JSON; open the saved file directly with Cytoscape."}
