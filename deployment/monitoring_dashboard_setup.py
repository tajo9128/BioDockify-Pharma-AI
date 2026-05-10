"""
Grafana Dashboard Setup for BioDockify.
This script defines the JSON dashboard configurations for Monitoring Agent Zero and ChromaDB.
"""

import json
import os

DASHBOARDS = {
    "agent_zero_overview": {
        "title": "BioDockify - Agent Zero Overview",
        "panels": [
            {
                "title": "Agent Executions (Total)",
                "type": "graph",
                "targets": [{"expr": "sum(agent_zero_executions_total) by (status)"}]
            },
            {
                "title": "Self-Repair Success Rate",
                "type": "piechart",
                "targets": [{"expr": "sum(agent_zero_self_repairs_total) by (success)"}]
            },
            {
                "title": "Execution Duration (P95)",
                "type": "graph",
                "targets": [{"expr": "histogram_quantile(0.95, sum(agent_zero_execution_duration_seconds_bucket) by (le))"}]
            }
        ]
    },
    "vector_db_performance": {
        "title": "BioDockify - Vector DB Performance",
        "panels": [
            {
                "title": "ChromaDB Document Count",
                "type": "stat",
                "targets": [{"expr": "chroma_document_count"}]
            },
            {
                "title": "Query Duration (P95)",
                "type": "graph",
                "targets": [{"expr": "histogram_quantile(0.95, sum(chroma_query_duration_seconds_bucket) by (le))"}]
            }
        ]
    }
}

def setup_dashboards():
    """
    In a real production environment, this might use the Grafana API to POST these dashboards.
    For this Zero-Cost setup, we save them as JSON files for manual/provisioned import.
    """
    output_dir = "monitoring/grafana/dashboards"
    os.makedirs(output_dir, exist_ok=True)
    
    for name, config in DASHBOARDS.items():
        file_path = os.path.join(output_dir, f"{name}.json")
        with open(file_path, "w") as f:
            json.dump(config, f, indent=4)
        print(f"Provisioned dashboard JSON: {file_path}")

if __name__ == "__main__":
    setup_dashboards()
