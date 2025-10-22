import os
import sys
from pathlib import Path
from graphviz import Digraph

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent

sys.path.append(str(PROJECT_ROOT))

from src.status_tracker import STAGES

GRAPHVIZ_BIN = TOOLS_DIR / "graphviz" / "Graphviz-14.0.2-win64" / "bin"
if GRAPHVIZ_BIN.exists():
    os.environ["PATH"] = f"{GRAPHVIZ_BIN}{os.pathsep}" + os.environ.get("PATH", "")
    os.environ.setdefault("GRAPHVIZ_DOT", str(GRAPHVIZ_BIN / "dot.exe"))

def make_flowchart(output_path: str = "docs/pipeline_flowchart") -> str:
    dot = Digraph("Pipeline", graph_attr={"rankdir": "LR", "splines": "spline"})
    dot.attr("node", shape="rectangle", style="rounded,filled", color="#0C111F", fillcolor="#161B26", fontname="Helvetica", fontcolor="#E2E8F0")
    dot.attr("edge", color="#718096", arrowsize="0.8")

    if not STAGES:
        dot.node("No stages defined")
    else:
        dot.edge("Audio Input", STAGES[0]["name"])
        for i in range(len(STAGES) - 1):
            src = STAGES[i]["name"]
            dst = STAGES[i + 1]["name"]
            dot.edge(src, dst)

    output = dot.render(output_path, format="svg", cleanup=True)
    return output

if __name__ == "__main__":
    try:
        output_file = make_flowchart()
        print(f"Generated {output_file}")
    except Exception as exc:
        print(f"Failed to generate flowchart: {exc}")
        raise
