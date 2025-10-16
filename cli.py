"""Command-line interface for D&D Session Processor"""
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from src.pipeline import DDSessionProcessor
from src.config import Config

console = Console()


@click.group()
def cli():
    """D&D Session Transcription & Diarization System"""
    pass


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option(
    '--session-id',
    '-s',
    help='Unique session identifier (defaults to filename)',
    default=None
)
@click.option(
    '--party',
    help='Party configuration ID (e.g., "default"). Overrides --characters and --players',
    default=None
)
@click.option(
    '--characters',
    '-c',
    help='Comma-separated list of character names',
    default=None
)
@click.option(
    '--players',
    '-p',
    help='Comma-separated list of player names',
    default=None
)
@click.option(
    '--output-dir',
    '-o',
    help='Output directory',
    type=click.Path(),
    default=None
)
@click.option(
    '--skip-diarization',
    is_flag=True,
    help='Skip speaker diarization (faster but no speaker labels)'
)
@click.option(
    '--skip-classification',
    is_flag=True,
    help='Skip IC/OOC classification (faster but no content separation)'
)
@click.option(
    '--skip-snippets',
    is_flag=True,
    help='Skip exporting per-segment audio snippets'
)
@click.option(
    '--num-speakers',
    '-n',
    type=int,
    default=4,
    help='Expected number of speakers (default: 4)'
)
def process(
    input_file,
    session_id,
    party,
    characters,
    players,
    output_dir,
    skip_diarization,
    skip_classification,
    skip_snippets,
    num_speakers
):
    """Process a D&D session recording"""

    input_path = Path(input_file)

    # Default session ID to filename
    if session_id is None:
        session_id = input_path.stem

    # Create processor based on party config or manual entry
    if party:
        # Use party configuration
        console.print(f"[cyan]Using party configuration: {party}[/cyan]")
        processor = DDSessionProcessor(
            session_id=session_id,
            num_speakers=num_speakers,
            party_id=party
        )
    else:
        # Parse character and player names
        character_names = characters.split(',') if characters else []
        player_names = players.split(',') if players else []

        processor = DDSessionProcessor(
            session_id=session_id,
            character_names=character_names,
            player_names=player_names,
            num_speakers=num_speakers
        )

    # Process
    try:
        result = processor.process(
            input_file=input_path,
            output_dir=output_dir,
            skip_diarization=skip_diarization,
            skip_classification=skip_classification,
            skip_snippets=skip_snippets
        )

        # Show success message
        console.print("\n[bold green]✓ Processing completed successfully![/bold green]")

    except Exception as e:
        console.print(f"\n[bold red]✗ Processing failed: {e}[/bold red]")
        raise click.Abort()


@cli.command()
@click.argument('session_id')
@click.argument('speaker_id')
@click.argument('person_name')
def map_speaker(session_id, speaker_id, person_name):
    """
    Map a speaker ID to a person name.

    Example: python cli.py map-speaker session1 SPEAKER_00 "Alice"
    """
    from src.diarizer import SpeakerProfileManager

    manager = SpeakerProfileManager()
    manager.map_speaker(session_id, speaker_id, person_name)

    console.print(f"[green]✓ Mapped {speaker_id} → {person_name} for session {session_id}[/green]")


@cli.command()
@click.argument('session_id')
def show_speakers(session_id):
    """Show speaker mappings for a session"""
    from src.diarizer import SpeakerProfileManager

    manager = SpeakerProfileManager()

    if session_id not in manager.profiles:
        console.print(f"[yellow]No speaker profiles found for session: {session_id}[/yellow]")
        return

    profiles = manager.profiles[session_id]

    table = Table(title=f"Speaker Profiles for {session_id}")
    table.add_column("Speaker ID", style="cyan")
    table.add_column("Person Name", style="green")

    for speaker_id, person_name in profiles.items():
        table.add_row(speaker_id, person_name)

    console.print(table)


@cli.command()
def list_parties():
    """List all available party configurations"""
    from src.party_config import PartyConfigManager

    manager = PartyConfigManager()
    parties = manager.list_parties()

    if not parties:
        console.print("[yellow]No party configurations found.[/yellow]")
        return

    table = Table(title="Available Party Configurations")
    table.add_column("Party ID", style="cyan")
    table.add_column("Party Name", style="green")
    table.add_column("Campaign", style="yellow")
    table.add_column("Characters", style="magenta")

    for party_id in parties:
        party = manager.get_party(party_id)
        character_names = ", ".join([c.name for c in party.characters])
        table.add_row(
            party_id,
            party.party_name,
            party.campaign or "N/A",
            character_names
        )

    console.print(table)


@cli.command()
@click.argument('party_id', default='default')
def show_party(party_id):
    """Show detailed information about a party configuration"""
    from src.party_config import PartyConfigManager

    manager = PartyConfigManager()
    party = manager.get_party(party_id)

    if not party:
        console.print(f"[red]Party '{party_id}' not found.[/red]")
        return

    console.print(f"\n[bold cyan]{party.party_name}[/bold cyan]")
    console.print(f"[dim]Campaign: {party.campaign or 'N/A'}[/dim]")
    console.print(f"[dim]DM: {party.dm_name}[/dim]\n")

    table = Table(title="Characters")
    table.add_column("Name", style="cyan")
    table.add_column("Player", style="green")
    table.add_column("Race", style="yellow")
    table.add_column("Class", style="magenta")
    table.add_column("Aliases", style="dim")

    for char in party.characters:
        aliases = ", ".join(char.aliases) if char.aliases else "—"
        table.add_row(
            char.name,
            char.player,
            char.race,
            char.class_name,
            aliases
        )

    console.print(table)

    if party.notes:
        console.print(f"\n[dim]Notes: {party.notes}[/dim]")


@cli.command()
@click.argument('party_id')
@click.argument('output_file', type=click.Path())
def export_party(party_id, output_file):
    """
    Export a party configuration to a JSON file.

    Example: python cli.py export-party default my_party.json
    """
    from src.party_config import PartyConfigManager

    manager = PartyConfigManager()

    try:
        manager.export_party(party_id, Path(output_file))
        console.print(f"[green]SUCCESS: Exported party '{party_id}' to {output_file}[/green]")
    except ValueError as e:
        console.print(f"[red]ERROR: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--party-id', help='Override party ID from file')
def import_party(input_file, party_id):
    """
    Import a party configuration from a JSON file.

    Example: python cli.py import-party my_party.json
    Example: python cli.py import-party my_party.json --party-id my_campaign
    """
    from src.party_config import PartyConfigManager

    manager = PartyConfigManager()

    try:
        imported_id = manager.import_party(Path(input_file), party_id)
        console.print(f"[green]SUCCESS: Imported party as '{imported_id}'[/green]")
    except Exception as e:
        console.print(f"[red]ERROR: Error importing party: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.argument('output_file', type=click.Path())
def export_all_parties(output_file):
    """
    Export all party configurations to a JSON file.

    Example: python cli.py export-all-parties backup.json
    """
    from src.party_config import PartyConfigManager

    manager = PartyConfigManager()

    try:
        manager.export_all_parties(Path(output_file))
        party_count = len(manager.list_parties())
        console.print(f"[green]SUCCESS: Exported {party_count} parties to {output_file}[/green]")
    except Exception as e:
        console.print(f"[red]ERROR: {e}[/red]")
        raise click.Abort()


@cli.command()
def list_characters():
    """List all character profiles"""
    from src.character_profile import CharacterProfileManager

    manager = CharacterProfileManager()
    characters = manager.list_characters()

    if not characters:
        console.print("[yellow]No character profiles found.[/yellow]")
        return

    table = Table(title="Character Profiles")
    table.add_column("Character", style="cyan")
    table.add_column("Player", style="green")
    table.add_column("Race/Class", style="yellow")
    table.add_column("Level", style="magenta")
    table.add_column("Sessions", style="blue")

    for char_name in characters:
        profile = manager.get_profile(char_name)
        table.add_row(
            char_name,
            profile.player,
            f"{profile.race} {profile.class_name}",
            str(profile.level),
            str(profile.total_sessions)
        )

    console.print(table)


@cli.command()
@click.argument('character_name')
@click.option('--format', '-f', type=click.Choice(['markdown', 'text']), default='markdown',
              help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Save to file instead of printing')
def show_character(character_name, format, output):
    """Show detailed character profile and overview"""
    from src.character_profile import CharacterProfileManager

    manager = CharacterProfileManager()
    overview = manager.generate_character_overview(character_name, format=format)

    if output:
        Path(output).write_text(overview, encoding='utf-8')
        console.print(f"[green]Saved character overview to {output}[/green]")
    else:
        from rich.markdown import Markdown
        if format == 'markdown':
            console.print(Markdown(overview))
        else:
            console.print(overview)


@cli.command()
@click.argument('character_name')
@click.argument('output_file', type=click.Path())
def export_character(character_name, output_file):
    """Export a character profile to JSON file"""
    from src.character_profile import CharacterProfileManager

    manager = CharacterProfileManager()

    try:
        manager.export_profile(character_name, Path(output_file))
        console.print(f"[green]SUCCESS: Exported character '{character_name}' to {output_file}[/green]")
    except ValueError as e:
        console.print(f"[red]ERROR: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--character-name', help='Override character name from file')
def import_character(input_file, character_name):
    """Import a character profile from JSON file"""
    from src.character_profile import CharacterProfileManager

    manager = CharacterProfileManager()

    try:
        imported_name = manager.import_profile(Path(input_file), character_name)
        console.print(f"[green]SUCCESS: Imported character '{imported_name}'[/green]")
    except Exception as e:
        console.print(f"[red]ERROR: {e}[/red]")
        raise click.Abort()


@cli.command()
def config():
    """Show current configuration"""
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Whisper Model", Config.WHISPER_MODEL)
    table.add_row("Whisper Backend", Config.WHISPER_BACKEND)
    table.add_row("LLM Backend", Config.LLM_BACKEND)
    table.add_row("Chunk Length", f"{Config.CHUNK_LENGTH_SECONDS}s")
    table.add_row("Chunk Overlap", f"{Config.CHUNK_OVERLAP_SECONDS}s")
    table.add_row("Sample Rate", f"{Config.AUDIO_SAMPLE_RATE} Hz")
    table.add_row("Output Directory", str(Config.OUTPUT_DIR))
    table.add_row("Temp Directory", str(Config.TEMP_DIR))

    console.print(table)


@cli.command()
def check_setup():
    """Check if all dependencies are properly installed"""
    console.print("[bold]Checking setup...[/bold]\n")

    checks = []

    # Check FFmpeg
    import subprocess
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        checks.append(("FFmpeg", True, "Installed"))
    except (subprocess.CalledProcessError, FileNotFoundError):
        checks.append(("FFmpeg", False, "Not found - please install from https://ffmpeg.org"))

    # Check PyTorch
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            checks.append(("PyTorch", True, f"Installed with CUDA"))
        else:
            checks.append(("PyTorch", True, f"Installed (CPU only)"))
    except ImportError:
        checks.append(("PyTorch", False, "Not installed"))

    # Check faster-whisper
    try:
        import faster_whisper
        checks.append(("faster-whisper", True, "Installed"))
    except ImportError:
        checks.append(("faster-whisper", False, "Not installed"))

    # Check PyAnnote
    try:
        import pyannote.audio
        checks.append(("pyannote.audio", True, "Installed"))
    except ImportError:
        checks.append(("pyannote.audio", False, "Not installed"))

    # Check Ollama connection
    try:
        import ollama
        client = ollama.Client(host=Config.OLLAMA_BASE_URL)
        client.list()
        checks.append(("Ollama", True, f"Running at {Config.OLLAMA_BASE_URL}"))
    except Exception as e:
        checks.append(("Ollama", False, f"Not running - {str(e)[:50]}"))

    # Display results
    table = Table(title="Dependency Check")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    for name, success, details in checks:
        status = "[green]✓[/green]" if success else "[red]✗[/red]"
        table.add_row(name, status, details)

    console.print(table)

    # Overall status
    all_ok = all(check[1] for check in checks)
    if all_ok:
        console.print("\n[bold green]✓ All dependencies are ready![/bold green]")
    else:
        console.print("\n[bold yellow]⚠ Some dependencies are missing. Please install them.[/bold yellow]")
        console.print("\nRun: pip install -r requirements.txt")


if __name__ == '__main__':
    cli()
