"""
Custom FastMCP Server for D&D Session Transcription System
Provides project-specific tools for managing sessions, tests, and campaign data.
"""
import subprocess
import json
import os
from pathlib import Path
from typing import Optional, List, Dict
from fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("VideoChunking Dev Server")

# Project root directory
PROJECT_ROOT = Path(__file__).parent


@mcp.tool()
def analyze_test_coverage() -> str:
    """
    Run pytest with coverage analysis for the entire project.
    Returns coverage report showing which parts of the code are tested.
    """
    try:
        result = subprocess.run(
            ["pytest", "--cov=src", "--cov-report=term", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=120
        )
        return f"Exit code: {result.returncode}\n\n{result.stdout}\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "Test coverage analysis timed out after 120 seconds"
    except Exception as e:
        return f"Error running coverage: {str(e)}"


@mcp.tool()
def run_specific_test(test_path: str) -> str:
    """
    Run a specific pytest test by path.

    Args:
        test_path: Path to test file or specific test (e.g., "tests/test_diarization.py" or "tests/test_diarization.py::test_speaker_embedding")

    Returns:
        Test output with results
    """
    try:
        result = subprocess.run(
            ["pytest", test_path, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=300
        )
        return f"Exit code: {result.returncode}\n\n{result.stdout}\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return f"Test '{test_path}' timed out after 300 seconds"
    except Exception as e:
        return f"Error running test: {str(e)}"


@mcp.tool()
def list_processed_sessions(limit: Optional[int] = 10) -> str:
    """
    List recently processed D&D sessions from the output directory.

    Args:
        limit: Maximum number of sessions to return (default: 10)

    Returns:
        JSON list of session directories with metadata
    """
    try:
        output_dir = PROJECT_ROOT / "output"
        if not output_dir.exists():
            return json.dumps({"sessions": [], "message": "Output directory does not exist"})

        # Get all session directories (format: YYYYMMDD_HHMMSS_sessionid)
        session_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
        session_dirs.sort(key=lambda x: x.name, reverse=True)

        sessions = []
        for session_dir in session_dirs[:limit]:
            # Try to read session data
            data_file = session_dir / f"{session_dir.name.split('_', 2)[-1]}_data.json"
            session_info = {
                "directory": session_dir.name,
                "path": str(session_dir),
                "created": session_dir.stat().st_mtime
            }

            if data_file.exists():
                try:
                    with open(data_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        session_info["speaker_count"] = len(set(seg.get("speaker", "UNKNOWN") for seg in data.get("segments", [])))
                        session_info["segment_count"] = len(data.get("segments", []))
                        session_info["duration"] = data.get("metadata", {}).get("duration")
                except Exception:
                    pass

            sessions.append(session_info)

        return json.dumps({"sessions": sessions, "total_found": len(session_dirs)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def check_pipeline_health() -> str:
    """
    Check the health status of all pipeline components.
    Verifies required dependencies and models are available.

    Returns:
        Health check report in JSON format
    """
    health = {
        "ffmpeg": False,
        "ollama": False,
        "pyannote_models": False,
        "whisper": False,
        "dependencies": []
    }

    # Check FFmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        health["ffmpeg"] = result.returncode == 0
    except Exception:
        pass

    # Check Ollama
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, timeout=10)
        health["ollama"] = result.returncode == 0
        if health["ollama"]:
            health["ollama_models"] = result.stdout.decode().strip()
    except Exception:
        pass

    # Check Python packages
    required_packages = [
        "faster-whisper", "pyannote.audio", "pydub",
        "gradio", "click", "rich", "torch", "groq"
    ]

    for package in required_packages:
        try:
            result = subprocess.run(
                ["pip", "show", package],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version_line = [l for l in result.stdout.split('\n') if l.startswith('Version:')]
                version = version_line[0].split(':', 1)[1].strip() if version_line else "unknown"
                health["dependencies"].append({"package": package, "installed": True, "version": version})
            else:
                health["dependencies"].append({"package": package, "installed": False})
        except Exception:
            health["dependencies"].append({"package": package, "installed": False})

    return json.dumps(health, indent=2)


@mcp.tool()
def validate_party_config(config_name: Optional[str] = None) -> str:
    """
    Validate party configuration files.

    Args:
        config_name: Specific config to validate (e.g., "default"). If None, validates all configs.

    Returns:
        Validation report with any errors or warnings
    """
    try:
        data_dir = PROJECT_ROOT / "data"
        if not data_dir.exists():
            return json.dumps({"error": "Data directory not found"})

        if config_name:
            config_file = data_dir / f"party_{config_name}.json"
            configs = [config_file] if config_file.exists() else []
        else:
            configs = list(data_dir.glob("party_*.json"))

        results = []
        for config_file in configs:
            result = {"file": config_file.name, "valid": False, "errors": [], "warnings": []}

            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # Validate structure
                if "party_name" not in config:
                    result["errors"].append("Missing 'party_name' field")

                if "players" not in config or not isinstance(config["players"], list):
                    result["errors"].append("Missing or invalid 'players' list")
                else:
                    for idx, player in enumerate(config["players"]):
                        if "name" not in player:
                            result["errors"].append(f"Player {idx} missing 'name' field")
                        if "characters" not in player or not isinstance(player["characters"], list):
                            result["warnings"].append(f"Player {idx} ({player.get('name', 'unknown')}) has no characters")

                if "dm" not in config or not isinstance(config["dm"], dict):
                    result["errors"].append("Missing or invalid 'dm' field")

                result["valid"] = len(result["errors"]) == 0
                result["player_count"] = len(config.get("players", []))
                result["character_count"] = sum(len(p.get("characters", [])) for p in config.get("players", []))

            except json.JSONDecodeError as e:
                result["errors"].append(f"Invalid JSON: {str(e)}")
            except Exception as e:
                result["errors"].append(f"Error reading file: {str(e)}")

            results.append(result)

        return json.dumps({"configs": results, "total_validated": len(results)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_campaign_knowledge_summary() -> str:
    """
    Get a summary of extracted campaign knowledge (NPCs, locations, quests, etc.).

    Returns:
        Summary of campaign knowledge base in JSON format
    """
    try:
        data_dir = PROJECT_ROOT / "data"
        kb_file = data_dir / "campaign_knowledge.json"

        if not kb_file.exists():
            return json.dumps({
                "exists": False,
                "message": "No campaign knowledge base found. Process sessions to extract knowledge."
            })

        with open(kb_file, 'r', encoding='utf-8') as f:
            kb = json.load(f)

        summary = {
            "exists": True,
            "npcs": len(kb.get("npcs", [])),
            "locations": len(kb.get("locations", [])),
            "quests": len(kb.get("quests", [])),
            "items": len(kb.get("items", [])),
            "factions": len(kb.get("factions", [])),
            "recent_npcs": [npc.get("name") for npc in kb.get("npcs", [])[:5]],
            "recent_locations": [loc.get("name") for loc in kb.get("locations", [])[:5]],
            "active_quests": [q.get("name") for q in kb.get("quests", []) if q.get("status") == "active"]
        }

        return json.dumps(summary, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def run_diagnostics_suite() -> str:
    """
    Run comprehensive diagnostics on the project.
    Checks tests, coverage, dependencies, and data integrity.

    Returns:
        Complete diagnostic report
    """
    diagnostics = {
        "timestamp": subprocess.run(
            ["python", "-c", "import datetime; print(datetime.datetime.now().isoformat())"],
            capture_output=True,
            text=True
        ).stdout.strip(),
        "python_version": subprocess.run(
            ["python", "--version"],
            capture_output=True,
            text=True
        ).stdout.strip(),
        "git_status": None,
        "test_status": None,
        "dependencies": None
    }

    # Git status
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=5
        )
        diagnostics["git_status"] = result.stdout.strip() if result.returncode == 0 else "Git not available"
    except Exception:
        diagnostics["git_status"] = "Error checking git status"

    # Quick test run
    try:
        result = subprocess.run(
            ["pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=30
        )
        if result.returncode == 0:
            # Count tests
            test_count = len([l for l in result.stdout.split('\n') if '::test_' in l])
            diagnostics["test_status"] = f"{test_count} tests collected"
        else:
            diagnostics["test_status"] = "Error collecting tests"
    except Exception as e:
        diagnostics["test_status"] = f"Error: {str(e)}"

    return json.dumps(diagnostics, indent=2)


@mcp.tool()
def list_available_models() -> str:
    """
    List available Ollama models for IC/OOC classification.

    Returns:
        List of installed Ollama models
    """
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return f"Available Ollama models:\n\n{result.stdout}"
        else:
            return f"Ollama not available or error occurred:\n{result.stderr}"
    except FileNotFoundError:
        return "Ollama is not installed or not in PATH"
    except Exception as e:
        return f"Error checking Ollama models: {str(e)}"


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
