from helpers.tool import Tool, Response
import os, sys, textwrap, subprocess, shutil
from helpers.print_style import PrintStyle


class ToolMakerTool(Tool):
    async def execute(self, action: str = "create", **kwargs):
        if action == "create":
            return await self._create_tool(kwargs.get("name", ""), kwargs.get("description", ""),
                                           kwargs.get("code", ""), kwargs.get("package", ""))
        elif action == "install":
            return await self._install_package(kwargs.get("package", ""))
        elif action == "list-missing":
            return await self._list_missing()
        elif action == "scan-path":
            return await self._scan_path(kwargs.get("prefix", ""))
        return Response(message="ToolMakerTool actions: create, install, list-missing, scan-path", break_loop=False)

    async def _create_tool(self, name: str, description: str, code: str, package: str) -> Response:
        if not name:
            return Response(message="Error: 'name' is required", break_loop=False)

        if package:
            install_ok = await self._install_package(package)
            if "Error" in install_ok.message:
                return install_ok

        usr_dir = self.agent.get_data("usr_dir") or "usr"
        tools_dir = os.path.join(usr_dir, "tools")
        os.makedirs(tools_dir, exist_ok=True)
        tool_path = os.path.join(tools_dir, f"{name}.py")

        if os.path.exists(tool_path):
            return Response(message=f"Tool '{name}' already exists at {tool_path}", break_loop=False)

        if code:
            with open(tool_path, "w") as f:
                f.write(code)
        else:
            class_name = name.title().replace("_", "") + "Tool"
            with open(tool_path, "w") as f:
                f.write(textwrap.dedent(f'''\
                from helpers.tool import Tool, Response

                class {class_name}(Tool):
                    async def execute(self, **kwargs):
                        """Auto-created tool: {description or name}"""
                        return Response(
                            message="Tool '{name}' executed. Override this method with custom logic.",
                            break_loop=False,
                        )
                '''))

        PrintStyle(font_color="green", padding=True).print(f"✓ ToolMaker: created tool '{name}' at {tool_path}")
        return Response(message=f"Tool '{name}' created successfully", break_loop=False)

    async def _install_package(self, package: str) -> Response:
        if not package:
            return Response(message="Error: 'package' is required", break_loop=False)
        PrintStyle(font_color="yellow", padding=True).print(f"⟳ ToolMaker: installing package '{package}'...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                PrintStyle(font_color="green", padding=True).print(f"✓ ToolMaker: installed '{package}'")
                return Response(message=f"Package '{package}' installed successfully", break_loop=False)
            else:
                return Response(message=f"Failed to install '{package}': {result.stderr[:500]}", break_loop=False)
        except Exception as e:
            return Response(message=f"Error installing '{package}': {e}", break_loop=False)

    async def _list_missing(self) -> Response:
        lines = ["Common tools that can be auto-installed via ToolMaker:"]
        lines.append("  tool_maker action=install package=<pypi_name>")
        lines.append("  tool_maker action=create name=<tool_name> code=<python_code>")
        lines.append("")
        lines.append("Suggested packages:")
        for tool, pkg in [("curl", "pycurl"), ("nmap", "python-nmap"), ("git", "gitpython"),
                          ("docker", "docker"), ("pandas", "pandas"), ("numpy", "numpy"),
                          ("pillow", "Pillow"), ("requests", "requests")]:
            lines.append(f"  tool_maker action=install package={pkg}")
        return Response(message="\n".join(lines), break_loop=False)

    async def _scan_path(self, prefix: str = "") -> Response:
        lines = [f"System commands matching prefix '{prefix}':"]
        found = 0
        for dir in os.environ.get("PATH", "").split(os.pathsep):
            if not dir or not os.path.isdir(dir):
                continue
            try:
                for fname in os.listdir(dir):
                    if prefix and not fname.startswith(prefix):
                        continue
                    if found < 50:
                        lines.append(f"  {fname}")
                        found += 1
                    else:
                        break
            except Exception:
                continue
        if found == 0:
            lines.append("  (none found)")
        else:
            lines.append(f"  ... and {found} total matches")
        lines.append("")
        lines.append("Use tool_maker action=create name=<cmd> to wrap any system command as an agent tool")
        return Response(message="\n".join(lines), break_loop=False)
