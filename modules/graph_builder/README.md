# Neo4j Graph Builder

A robust Python module for loading research data into a Neo4j Knowledge Graph, designed for the BioDockify platform.

## Features

- **Resilient**: Gracefully handles offline scenarios (updates are skipped if DB is down).
- **Schema Management**: Auto-creates uniqueness constraints.
- **Simple API**: Easy functions `add_paper()` and `connect_compound()`.

## Dependencies

- Neo4j Database (Download Community Edition at https://neo4j.com/download/)
- Python driver: `neo4j`

## Usage

```python
from modules.graph_builder import create_constraints, add_paper, connect_compound

# Initialize schema
create_constraints()

# Add Data
add_paper({
    "pmid": "12345",
    "title": "Aspirin effectiveness",
    "year": 2023
})

connect_compound("12345", "Aspirin")
```

## Configuration

By default, it connects to locally hosted Neo4j:
- URI: `bolt://localhost:7687`
- Auth: `neo4j` / `neo4j`

Edit `modules/graph_builder/loader.py` to change defaults or pass arguments to `Neo4jLoader`.
