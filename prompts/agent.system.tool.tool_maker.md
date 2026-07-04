### tool_maker
auto-create or install missing tools and packages at runtime
actions:
  - `create`: create a new tool — args: `name` (required), `description`, `code` (Python code for Tool class), `package` (PyPI package to pre-install)
  - `install`: install a Python package — args: `package` (required, PyPI name)
  - `list-missing`: show suggested tools/packages available for auto-install
  - `scan-path`: scan system PATH for commands matching a prefix — args: `prefix`
use when a tool is missing and the system did not auto-create it, or when you need to install OS-level dependencies
