
import sys
import os
import logging

# Setup paths
sys.path.append(os.path.join(os.getcwd()))
from agent_zero.hybrid.tools.graph_tool import KnowledgeGraphTool

def test_graph_tool():
    print("[-] Initializing KnowledgeGraphTool...")
    try:
        tool = KnowledgeGraphTool()
        print("[+] Tool initialized.")
    except Exception as e:
        print(f"[!] Failed to initialize: {e}")
        return

    # 1. Test Schema
    print("\n[1] Testing get_schema()...")
    schema = tool.get_schema()
    print(f"[*] Schema Result: {schema}")
    
    # 2. Test Add Node (Only if connected)
    if "not connected" not in schema:
        print("\n[2] Testing add_node()...")
        res = tool.add_node({"label": "TestNode", "properties": {"name": "GraphUnitCheck", "status": "active"}})
        print(f"[*] Add Result: {res}")
        
        # 3. Test Query
        print("\n[3] Testing query_graph()...")
        query_res = tool.query_graph({"query": "MATCH (n:TestNode {name: 'GraphUnitCheck'}) RETURN n"})
        print(f"[*] Query Result: {query_res}")
        
        # Cleanup
        tool.query_graph({"query": "MATCH (n:TestNode {name: 'GraphUnitCheck'}) DELETE n"})
    else:
        print("\n[!] Skipping write tests (DB offline).")

if __name__ == "__main__":
    test_graph_tool()
