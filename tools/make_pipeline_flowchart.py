import os
from pathlib import Path
from graphviz import Digraph

TOOLS_DIR = Path(__file__).resolve().parent
GRAPHVIZ_BIN = TOOLS_DIR / "graphviz" / "Graphviz-14.0.2-win64" / "bin"
if GRAPHVIZ_BIN.exists():
    os.environ["PATH"] = f"{GRAPHVIZ_BIN}{os.pathsep}" + os.environ.get("PATH", "")
    os.environ.setdefault("GRAPHVIZ_DOT", str(GRAPHVIZ_BIN / "dot.exe"))

STAGES = [
    ("Audio Input", "Audio Conversion"),
    ("Audio Conversion", "Chunking"),
    ("Chunking", "Transcription"),
    ("Transcription", "Merge Overlaps"),
    ("Merge Overlaps", "Speaker Diarization"),
    ("Speaker Diarization", "IC/OOC Classification"),
    ("IC/OOC Classification", "Output Generation"),
    ("Output Generation", "Audio Snippet Export"),
]

def make_flowchart(output_path: str = "docs/pipeline_flowchart") -> str:
    dot = Digraph("Pipeline", graph_attr={"rankdir": "LR", "splines": "spline"})
    dot.attr("node", shape="rectangle", style="rounded,filled", color="#0C111F", fillcolor="#161B26", fontname="Helvetica", fontcolor="#E2E8F0")
    dot.attr("edge", color="#718096", arrowsize="0.8")

    for src, dst in STAGES:
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
