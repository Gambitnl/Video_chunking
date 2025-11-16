"""Command-line interface for D&D Session Processor"""
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from src.pipeline import DDSessionProcessor
from src.config import Config
from src.logger import get_log_file_path, set_console_log_level, LOG_LEVEL_CHOICES
from src.audit import log_audit_event, audit_enabled
from src.story_notebook import StoryNotebookManager, load_notebook_context_file

console = Console()


def _audit(ctx, action: str, *, status: str = "info", **metadata):
    """Record an audit event when auditing is enabled."""
    context = ctx.obj or {}
    if not context.get("audit_enabled", audit_enabled()):
        return
    actor = context.get("audit_actor") or Config.AUDIT_LOG_ACTOR
    log_audit_event(
        action,
        actor=actor,
        source="cli",
        status=status,
        metadata=metadata or {},
    )


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(LOG_LEVEL_CHOICES, case_sensitive=False),
    default=None,
    help="Set console log verbosity for this CLI session."
)
@click.option(
    "--audit-actor",
    default=None,
    help="Label audit log entries for this session (default: AUDIT_LOG_ACTOR)."
)
@click.option(
    "--no-audit",
    is_flag=True,
    help="Temporarily disable audit logging for this CLI invocation."
)
@click.pass_context
def cli(ctx, log_level, audit_actor, no_audit):
    """D&D Session Transcription & Diarization System"""
    ctx.ensure_object(dict)
    if log_level:
        set_console_log_level(log_level)
    ctx.obj["audit_actor"] = audit_actor or Config.AUDIT_LOG_ACTOR
    ctx.obj["audit_enabled"] = Config.AUDIT_LOG_ENABLED and not no_audit


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
@click.pass_context
def process(
    ctx,
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
    _audit(
        ctx,
        "cli.process.start",
        session_id=session_id,
        input_file=str(input_path),
        party=party,
        skip_diarization=skip_diarization,
        skip_classification=skip_classification,
        skip_snippets=skip_snippets,
        num_speakers=num_speakers,
    )

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
        console.print(f"[dim]Verbose log: {get_log_file_path()}[/dim]")
        _audit(
            ctx,
            "cli.process.complete",
            status="success",
            session_id=session_id,
            output_dir=str(output_dir) if output_dir else None,
            stats=(result or {}).get("statistics", {}),
        )

    except Exception as e:
        console.print(f"\n[bold red]✗ Processing failed: {e}[/bold red]")
        console.print(f"[dim]Inspect log for details: {get_log_file_path()}[/dim]")
        _audit(
            ctx,
            "cli.process.error",
            status="error",
            session_id=session_id,
            error=str(e),
        )
        raise click.Abort()


@cli.command()
@click.argument('session_id')
@click.argument('speaker_id')
@click.argument('person_name')
@click.pass_context
def map_speaker(ctx, session_id, speaker_id, person_name):
    """
    Map a speaker ID to a person name.

    Example: python cli.py map-speaker session1 SPEAKER_00 "Alice"
    """
    from src.diarizer import SpeakerProfileManager

    manager = SpeakerProfileManager()
    manager.map_speaker(session_id, speaker_id, person_name)

    console.print(f"[green]✓ Mapped {speaker_id} → {person_name} for session {session_id}[/green]")
    _audit(
        ctx,
        "cli.speakers.map",
        status="success",
        session_id=session_id,
        speaker_id=speaker_id,
        person_name=person_name,
    )


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
@click.pass_context
def export_party(ctx, party_id, output_file):
    """
    Export a party configuration to a JSON file.

    Example: python cli.py export-party default my_party.json
    """
    from src.party_config import PartyConfigManager

    manager = PartyConfigManager()

    try:
        manager.export_party(party_id, Path(output_file))
        console.print(f"[green]SUCCESS: Exported party '{party_id}' to {output_file}[/green]")
        _audit(
            ctx,
            "cli.party.export",
            status="success",
            party_id=party_id,
            output=str(Path(output_file).resolve()),
        )
    except ValueError as e:
        console.print(f"[red]ERROR: {e}[/red]")
        _audit(
            ctx,
            "cli.party.export",
            status="error",
            party_id=party_id,
            output=str(Path(output_file).resolve()),
            error=str(e),
        )
        raise click.Abort()


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--party-id', help='Override party ID from file')
@click.pass_context
def import_party(ctx, input_file, party_id):
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
        _audit(
            ctx,
            "cli.party.import",
            status="success",
            imported_id=imported_id,
            input=str(Path(input_file).resolve()),
        )
    except Exception as e:
        console.print(f"[red]ERROR: Error importing party: {e}[/red]")
        _audit(
            ctx,
            "cli.party.import",
            status="error",
            input=str(Path(input_file).resolve()),
            override_party_id=party_id,
            error=str(e),
        )
        raise click.Abort()


@cli.command()
@click.argument('output_file', type=click.Path())
@click.pass_context
def export_all_parties(ctx, output_file):
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
        _audit(
            ctx,
            "cli.party.export_all",
            status="success",
            output=str(Path(output_file).resolve()),
            count=party_count,
        )
    except Exception as e:
        console.print(f"[red]ERROR: {e}[/red]")
        _audit(
            ctx,
            "cli.party.export_all",
            status="error",
            output=str(Path(output_file).resolve()),
            error=str(e),
        )
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
@click.pass_context
def export_character(ctx, character_name, output_file):
    """Export a character profile to JSON file"""
    from src.character_profile import CharacterProfileManager

    manager = CharacterProfileManager()

    try:
        manager.export_profile(character_name, Path(output_file))
        console.print(f"[green]SUCCESS: Exported character '{character_name}' to {output_file}[/green]")
        _audit(
            ctx,
            "cli.character.export",
            status="success",
            character=character_name,
            output=str(Path(output_file).resolve()),
        )
    except ValueError as e:
        console.print(f"[red]ERROR: {e}[/red]")
        _audit(
            ctx,
            "cli.character.export",
            status="error",
            character=character_name,
            output=str(Path(output_file).resolve()),
            error=str(e),
        )
        raise click.Abort()


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--character-name', help='Override character name from file')
@click.pass_context
def import_character(ctx, input_file, character_name):
    """Import a character profile from JSON file"""
    from src.character_profile import CharacterProfileManager

    manager = CharacterProfileManager()

    try:
        imported_name = manager.import_profile(Path(input_file), character_name)
        console.print(f"[green]SUCCESS: Imported character '{imported_name}'[/green]")
        _audit(
            ctx,
            "cli.character.import",
            status="success",
            input=str(Path(input_file).resolve()),
            imported_name=imported_name,
        )
    except Exception as e:
        console.print(f"[red]ERROR: {e}[/red]")
        _audit(
            ctx,
            "cli.character.import",
            status="error",
            input=str(Path(input_file).resolve()),
            override_name=character_name,
            error=str(e),
        )
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

@click.group()
def sessions():
    """Manage and audit processed sessions."""
    pass


@sessions.command()
@click.option('--output', '-o', type=click.Path(), help='Save report to markdown file')
@click.pass_context
def audit(ctx, output):
    """Audit all processed sessions for issues."""
    from src.session_manager import SessionManager

    console.print("[bold]Auditing sessions...[/bold]\n")
    manager = SessionManager()
    report = manager.audit_sessions()

    totals = {
        "total": report.total_sessions,
        "empty": len(report.empty_sessions),
        "incomplete": len(report.incomplete_sessions),
        "stale": len(report.stale_checkpoints),
        "potential_cleanup_mb": report.potential_cleanup_mb,
    }

    console.print(f"[bold]Total Sessions:[/bold] {totals['total']}")
    console.print(f"[bold]Valid Sessions:[/bold] {len(report.valid_sessions)} ({report.total_size_mb - report.empty_size_mb - report.incomplete_size_mb:.2f} MB)")
    console.print(f"[bold]Empty Sessions:[/bold] {totals['empty']} ({report.empty_size_mb:.2f} MB)")
    console.print(f"[bold]Incomplete Sessions:[/bold] {totals['incomplete']} ({report.incomplete_size_mb:.2f} MB)")
    console.print(f"[bold]Stale Checkpoints:[/bold] {totals['stale']} ({report.stale_checkpoint_size_mb:.2f} MB)")
    console.print(f"[bold cyan]Potential Cleanup:[/bold cyan] {report.potential_cleanup_mb:.2f} MB\n")

    if not (report.empty_sessions or report.incomplete_sessions or report.stale_checkpoints):
        console.print("[bold green][OK] All sessions are in good condition.[/bold green]")
    else:
        if report.empty_sessions:
            table = Table(title="Empty Sessions")
            table.add_column("Session ID", style="cyan")
            table.add_column("Size", style="yellow")
            table.add_column("Created", style="dim")
            for session in report.empty_sessions:
                table.add_row(
                    session.session_id,
                    f"{session.size_mb:.2f} MB",
                    session.created_time.strftime('%Y-%m-%d')
                )
            console.print(table)
            console.print()

        if report.incomplete_sessions:
            table = Table(title="Incomplete Sessions")
            table.add_column("Session ID", style="cyan")
            table.add_column("Size", style="yellow")
            table.add_column("Missing Components", style="red")
            for session in report.incomplete_sessions:
                missing = []
                if not session.has_transcript:
                    missing.append("transcript")
                if not session.has_diarized_transcript:
                    missing.append("diarized")
                if not session.has_classified_transcript:
                    missing.append("classified")
                table.add_row(
                    session.session_id,
                    f"{session.size_mb:.2f} MB",
                    ", ".join(missing)
                )
            console.print(table)
            console.print()

        if report.stale_checkpoints:
            table = Table(title="Stale Checkpoints (>7 days)")
            table.add_column("Checkpoint ID", style="cyan")
            table.add_column("Size", style="yellow")
            for checkpoint_name in report.stale_checkpoints:
                size_mb = manager._get_directory_size(manager.checkpoint_dir / checkpoint_name) / (1024 * 1024)
                table.add_row(checkpoint_name, f"{size_mb:.2f} MB")
            console.print(table)

    if output:
        markdown_report = manager.generate_audit_report_markdown(report)
        Path(output).write_text(markdown_report, encoding='utf-8')
        console.print(f"\n[bold green][OK] Report saved to:[/bold green] {output}")
        report_path = str(Path(output).resolve())
    else:
        report_path = None

    _audit(
        ctx,
        "cli.sessions.audit",
        status="success",
        report_path=report_path,
        totals=totals,
    )


@sessions.command()
@click.option("--empty/--no-empty", default=True, help="Delete empty session directories (default: yes)")
@click.option("--incomplete/--no-incomplete", default=False, help="Delete incomplete sessions (default: no)")
@click.option("--stale-checkpoints/--no-stale-checkpoints", default=True, help="Delete stale checkpoints (default: yes)")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without actually deleting anything.")
@click.option("--force", is_flag=True, help="Delete without prompting (non-interactive mode).")
@click.option('--output', '-o', type=click.Path(), help='Save cleanup report to markdown file')
@click.pass_context
def cleanup(ctx, empty, incomplete, stale_checkpoints, dry_run, force, output):
    """Clean up empty, incomplete, and stale sessions.

    By default, this will:
    - Delete empty session directories
    - Delete stale checkpoints (>7 days old)
    - Keep incomplete sessions (use --incomplete to delete them)
    - Prompt before deleting (use --force to skip prompts)
    """
    from src.session_manager import SessionManager

    if dry_run:
        console.print("[bold yellow]DRY RUN MODE - No files will be deleted[/bold yellow]\n")

    console.print("[bold]Running cleanup...[/bold]\n")
    actor = ctx.obj.get("audit_actor") if ctx.obj else None
    manager = SessionManager(audit_actor=actor)

    # Run cleanup with specified options
    report = manager.cleanup(
        delete_empty=empty,
        delete_incomplete=incomplete,
        delete_stale_checkpoints=stale_checkpoints,
        dry_run=dry_run,
        interactive=not force
    )

    # Print summary
    console.print(f"\n[bold]Cleanup Summary:[/bold]")
    console.print(f"  Empty sessions deleted: {report.deleted_empty}")
    console.print(f"  Incomplete sessions deleted: {report.deleted_incomplete}")
    console.print(f"  Stale checkpoints deleted: {report.deleted_checkpoints}")
    console.print(f"  [bold green]Total space freed: {report.total_freed_mb:.2f} MB[/bold green]")

    if report.skipped_sessions:
        console.print(f"\n[yellow]Skipped sessions: {len(report.skipped_sessions)}[/yellow]")

    if report.errors:
        console.print(f"\n[bold red]Errors encountered: {len(report.errors)}[/bold red]")
        for error in report.errors:
            console.print(f"  - {error}")

    # Save markdown report if requested
    if output:
        markdown_report = manager.generate_cleanup_report_markdown(report)
        Path(output).write_text(markdown_report, encoding='utf-8')
        console.print(f"\n[bold green][OK] Report saved to:[/bold green] {output}")
        report_path = str(Path(output).resolve())
    else:
        report_path = None

    if dry_run:
        console.print("\n[bold yellow]This was a dry run. Run without --dry-run to delete files.[/bold yellow]")
    else:
        console.print("\n[bold green][OK] Cleanup complete![/bold green]")

    _audit(
        ctx,
        "cli.sessions.cleanup",
        status="success",
        dry_run=dry_run,
        options={
            "delete_empty": empty,
            "delete_incomplete": incomplete,
            "delete_stale_checkpoints": stale_checkpoints,
            "forced": force,
        },
        results={
            "deleted_empty": report.deleted_empty,
            "deleted_incomplete": report.deleted_incomplete,
            "deleted_checkpoints": report.deleted_checkpoints,
            "freed_mb": report.total_freed_mb,
            "errors": len(report.errors),
        },
        report_path=report_path,
    )

cli.add_command(sessions)


@click.group()
def campaigns():
    """Manage campaigns and migrate existing data."""
    pass


@campaigns.command('migrate-sessions')
@click.argument('campaign_id')
@click.option('--dry-run', is_flag=True, help='Preview changes without modifying files')
@click.option('--filter', '-f', help='Filter sessions by glob pattern (e.g., "Session_*")')
@click.option('--output', '-o', type=click.Path(), help='Save report to markdown file')
def migrate_sessions_cmd(campaign_id, dry_run, filter, output):
    """Add campaign_id to existing session metadata files.

    Example:
        python cli.py campaigns migrate-sessions broken_seekers
        python cli.py campaigns migrate-sessions broken_seekers --filter "Session_*"
        python cli.py campaigns migrate-sessions broken_seekers --dry-run
    """
    from src.campaign_migration import CampaignMigration

    console.print(f"\n[bold]{'[DRY RUN] ' if dry_run else ''}Migrating sessions to campaign: {campaign_id}[/bold]\n")

    migration = CampaignMigration()
    report = migration.migrate_session_metadata(
        campaign_id=campaign_id,
        dry_run=dry_run,
        session_filter=filter
    )

    # Display results
    console.print(f"[bold green]✓ Sessions migrated:[/bold green] {report.sessions_migrated}")
    console.print(f"[bold yellow]⊘ Sessions skipped:[/bold yellow] {report.sessions_skipped}")

    if report.errors:
        console.print(f"\n[bold red]✗ Errors ({len(report.errors)}):[/bold red]")
        for error in report.errors:
            console.print(f"  - {error}")

    if output:
        markdown_report = migration.generate_migration_report_markdown(sessions_report=report)
        Path(output).write_text(markdown_report, encoding='utf-8')
        console.print(f"\n[bold green]✓ Report saved to:[/bold green] {output}")

    if dry_run and report.sessions_migrated > 0:
        console.print(f"\n[bold yellow]This was a dry run. Run without --dry-run to apply changes.[/bold yellow]")


@campaigns.command('migrate-profiles')
@click.argument('campaign_id')
@click.option('--dry-run', is_flag=True, help='Preview changes without saving')
@click.option('--characters', '-c', help='Comma-separated list of character names to migrate')
@click.option('--output', '-o', type=click.Path(), help='Save report to markdown file')
def migrate_profiles_cmd(campaign_id, dry_run, characters, output):
    """Assign campaign_id to character profiles.

    Example:
        python cli.py campaigns migrate-profiles broken_seekers
        python cli.py campaigns migrate-profiles broken_seekers --characters "Sha'ek,Pipira"
        python cli.py campaigns migrate-profiles broken_seekers --dry-run
    """
    from src.campaign_migration import CampaignMigration

    character_filter = characters.split(',') if characters else None

    console.print(f"\n[bold]{'[DRY RUN] ' if dry_run else ''}Migrating character profiles to campaign: {campaign_id}[/bold]\n")

    migration = CampaignMigration()
    report = migration.migrate_character_profiles(
        campaign_id=campaign_id,
        dry_run=dry_run,
        character_filter=character_filter
    )

    # Display results
    console.print(f"[bold green]✓ Profiles migrated:[/bold green] {report.profiles_migrated}")
    console.print(f"[bold yellow]⊘ Profiles skipped:[/bold yellow] {report.profiles_skipped}")

    if report.errors:
        console.print(f"\n[bold red]✗ Errors ({len(report.errors)}):[/bold red]")
        for error in report.errors:
            console.print(f"  - {error}")

    if output:
        markdown_report = migration.generate_migration_report_markdown(profiles_report=report)
        Path(output).write_text(markdown_report, encoding='utf-8')
        console.print(f"\n[bold green]✓ Report saved to:[/bold green] {output}")

    if dry_run and report.profiles_migrated > 0:
        console.print(f"\n[bold yellow]This was a dry run. Run without --dry-run to save changes.[/bold yellow]")


@campaigns.command('migrate-narratives')
@click.argument('campaign_id')
@click.option('--dry-run', is_flag=True, help='Preview changes without modifying files')
@click.option('--output', '-o', type=click.Path(), help='Save report to markdown file')
def migrate_narratives_cmd(campaign_id, dry_run, output):
    """Add YAML frontmatter with campaign metadata to narrative files.

    Example:
        python cli.py campaigns migrate-narratives broken_seekers
        python cli.py campaigns migrate-narratives broken_seekers --dry-run
    """
    from src.campaign_migration import CampaignMigration

    console.print(f"\n[bold]{'[DRY RUN] ' if dry_run else ''}Adding frontmatter to narratives for campaign: {campaign_id}[/bold]\n")

    migration = CampaignMigration()
    report = migration.migrate_narrative_frontmatter(
        campaign_id=campaign_id,
        dry_run=dry_run
    )

    # Display results
    console.print(f"[bold green]✓ Narratives migrated:[/bold green] {report.narratives_migrated}")
    console.print(f"[bold yellow]⊘ Narratives skipped:[/bold yellow] {report.narratives_skipped}")

    if report.errors:
        console.print(f"\n[bold red]✗ Errors ({len(report.errors)}):[/bold red]")
        for error in report.errors:
            console.print(f"  - {error}")

    if output:
        markdown_report = migration.generate_migration_report_markdown(narratives_report=report)
        Path(output).write_text(markdown_report, encoding='utf-8')
        console.print(f"\n[bold green]✓ Report saved to:[/bold green] {output}")

    if dry_run and report.narratives_migrated > 0:
        console.print(f"\n[bold yellow]This was a dry run. Run without --dry-run to apply changes.[/bold yellow]")


cli.add_command(campaigns)


@click.group()
def artifacts():
    """Browse and download session artifacts."""
    pass


@artifacts.command('list')
@click.option('--limit', '-n', type=int, default=None, help='Maximum number of sessions to show')
@click.option('--json', 'output_json', is_flag=True, help='Output in JSON format')
@click.pass_context
def artifacts_list(ctx, limit, output_json):
    """List all processed sessions.

    Shows session directories sorted by modification time (most recent first).
    Displays name, file count, size, and modification date.

    Examples:
        python cli.py artifacts list
        python cli.py artifacts list --limit 10
        python cli.py artifacts list --json
    """
    from src.api.session_artifacts import list_sessions_api
    import json

    response = list_sessions_api()

    if response['status'] != 'success':
        console.print(f"[red]Error: {response['error']}[/red]")
        _audit(ctx, "cli.artifacts.list", status="error", error=response['error'])
        raise click.Abort()

    sessions = response['data']['sessions']

    if limit:
        sessions = sessions[:limit]

    if output_json:
        console.print(json.dumps(response, indent=2))
    else:
        if not sessions:
            console.print("[yellow]No sessions found.[/yellow]")
            return

        table = Table(title=f"Processed Sessions ({len(sessions)} total)")
        table.add_column("Session", style="cyan")
        table.add_column("Files", style="green", justify="right")
        table.add_column("Size", style="yellow", justify="right")
        table.add_column("Modified", style="dim")

        for session in sessions:
            # Format size
            size_bytes = session['total_size_bytes']
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

            # Format modified time
            from datetime import datetime
            modified = datetime.fromisoformat(session['modified'])
            modified_str = modified.strftime('%Y-%m-%d %H:%M')

            table.add_row(
                session['name'],
                str(session['file_count']),
                size_str,
                modified_str
            )

        console.print(table)

    _audit(ctx, "cli.artifacts.list", status="success", count=len(sessions))


@artifacts.command('tree')
@click.argument('session_path')
@click.option('--json', 'output_json', is_flag=True, help='Output in JSON format')
@click.pass_context
def artifacts_tree(ctx, session_path, output_json):
    """Show directory tree for a session.

    Lists all files and subdirectories in a session directory.

    Examples:
        python cli.py artifacts tree 20251115_184757_test_s6_nov15_1847pm
        python cli.py artifacts tree 20251115_184757_test_s6_nov15_1847pm --json
    """
    from src.api.session_artifacts import get_directory_tree_api
    import json

    response = get_directory_tree_api(session_path)

    if response['status'] != 'success':
        console.print(f"[red]Error: {response['error']}[/red]")
        _audit(ctx, "cli.artifacts.tree", status="error", error=response['error'], session_path=session_path)
        raise click.Abort()

    if output_json:
        console.print(json.dumps(response, indent=2))
    else:
        items = response['data']['items']

        if not items:
            console.print("[yellow]Directory is empty.[/yellow]")
            return

        table = Table(title=f"Contents of {session_path}")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Size", style="yellow", justify="right")
        table.add_column("Modified", style="dim")

        for item in items:
            # Format size
            size_bytes = item['size_bytes']
            if item['is_directory']:
                size_str = "<DIR>"
            elif size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

            # Format modified time
            from datetime import datetime
            modified = datetime.fromisoformat(item['modified'])
            modified_str = modified.strftime('%Y-%m-%d %H:%M')

            # Style name based on type
            name = item['name']
            if item['is_directory']:
                name = f"[bold]{name}/[/bold]"

            table.add_row(
                name,
                item['artifact_type'],
                size_str,
                modified_str
            )

        console.print(table)

    _audit(ctx, "cli.artifacts.tree", status="success", session_path=session_path, item_count=len(response['data']['items']))


@artifacts.command('download')
@click.argument('session_path')
@click.option('--file', '-f', help='Specific file to download (relative path within session)')
@click.option('--output', '-o', type=click.Path(), help='Output path for download')
@click.pass_context
def artifacts_download(ctx, session_path, file, output):
    """Download a session or specific file.

    Downloads either an entire session as a zip file or a specific file within the session.

    Examples:
        # Download entire session as zip
        python cli.py artifacts download 20251115_184757_test_s6_nov15_1847pm

        # Download specific file
        python cli.py artifacts download 20251115_184757_test_s6_nov15_1847pm --file test_s6_nov15_1847pm_full.txt

        # Download to specific location
        python cli.py artifacts download 20251115_184757_test_s6_nov15_1847pm --output ./my_session.zip
    """
    from src.api.session_artifacts import download_session_api, download_file_api
    import shutil

    if file:
        # Download specific file
        file_path = f"{session_path}/{file}"
        result = download_file_api(file_path)

        if result is None:
            console.print(f"[red]Error: File not found: {file_path}[/red]")
            _audit(ctx, "cli.artifacts.download", status="error", session_path=session_path, file=file, error="File not found")
            raise click.Abort()

        source_path, filename = result

        if output:
            dest_path = Path(output)
        else:
            dest_path = Path.cwd() / filename

        try:
            shutil.copy2(source_path, dest_path)
            console.print(f"[green]File downloaded:[/green] {dest_path}")
            _audit(ctx, "cli.artifacts.download", status="success", session_path=session_path, file=file, output=str(dest_path))
        except Exception as e:
            console.print(f"[red]Error copying file: {e}[/red]")
            _audit(ctx, "cli.artifacts.download", status="error", session_path=session_path, file=file, error=str(e))
            raise click.Abort()
    else:
        # Download entire session as zip
        result = download_session_api(session_path)

        if result is None:
            console.print(f"[red]Error: Session not found: {session_path}[/red]")
            _audit(ctx, "cli.artifacts.download", status="error", session_path=session_path, error="Session not found")
            raise click.Abort()

        source_path, filename = result

        if output:
            dest_path = Path(output)
        else:
            dest_path = Path.cwd() / filename

        try:
            shutil.move(str(source_path), str(dest_path))
            console.print(f"[green]Session downloaded:[/green] {dest_path}")
            _audit(ctx, "cli.artifacts.download", status="success", session_path=session_path, output=str(dest_path))
        except Exception as e:
            console.print(f"[red]Error moving file: {e}[/red]")
            _audit(ctx, "cli.artifacts.download", status="error", session_path=session_path, error=str(e))
            raise click.Abort()


cli.add_command(artifacts)


@cli.command()
@click.option(
    '--input-dir',
    '-d',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help='Directory containing audio files to process'
)
@click.option(
    '--files',
    '-f',
    multiple=True,
    type=click.Path(exists=True),
    help='Specific audio files to process (can be used multiple times)'
)
@click.option(
    '--output-dir',
    '-o',
    help='Base output directory for processed sessions',
    type=click.Path(),
    default=None
)
@click.option(
    '--party',
    help='Party configuration ID to use for all sessions',
    default=None
)
@click.option(
    '--resume/--no-resume',
    default=True,
    help='Resume from checkpoints if they exist (default: enabled)'
)
@click.option(
    '--skip-diarization',
    is_flag=True,
    help='Skip speaker diarization for all sessions'
)
@click.option(
    '--skip-classification',
    is_flag=True,
    help='Skip IC/OOC classification for all sessions'
)
@click.option(
    '--skip-snippets',
    is_flag=True,
    help='Skip audio snippet export for all sessions'
)
@click.option(
    '--skip-knowledge',
    is_flag=True,
    help='Skip campaign knowledge extraction for all sessions'
)
@click.option(
    '--num-speakers',
    '-n',
    type=int,
    default=4,
    help='Expected number of speakers for all sessions (default: 4)'
)
def batch(
    input_dir,
    files,
    output_dir,
    party,
    resume,
    skip_diarization,
    skip_classification,
    skip_snippets,
    skip_knowledge,
    num_speakers
):
    """
    Process multiple D&D session recordings in batch mode.

    Can process all audio files in a directory or specific files.
    Supports automatic checkpoint resumption and generates a summary report.

    Examples:

        # Process all audio files in a directory
        python cli.py batch --input-dir ./recordings

        # Process specific files
        python cli.py batch -f session1.m4a -f session2.mp3

        # With custom options
        python cli.py batch -d ./recordings --party default --skip-knowledge
    """
    from src.batch_processor import BatchProcessor

    # Validate that at least one input source is provided
    if not input_dir and not files:
        console.print("[red]✗ Error: Must provide either --input-dir or --files[/red]")
        console.print("[dim]Use --help for usage information[/dim]")
        raise click.Abort()

    # Collect files to process
    audio_files = []

    if input_dir:
        # Scan directory for audio files
        input_path = Path(input_dir)
        audio_extensions = {'.m4a', '.mp3', '.wav', '.flac', '.ogg', '.aac'}
        audio_files.extend(
            p for p in input_path.glob("*") if p.is_file() and p.suffix.lower() in audio_extensions
        )

    if files:
        # Add explicitly specified files
        audio_files.extend([Path(f) for f in files])

    # Deduplicate and sort all files
    audio_files = sorted(set(audio_files))

    if not audio_files:
        console.print("[red]✗ No audio files found to process.[/red]")
        if input_dir:
            console.print(f"[dim]Checked directory: {input_dir}[/dim]")
            console.print("[dim]Supported formats: .m4a, .mp3, .wav, .flac, .ogg, .aac[/dim]")
        raise click.Abort()

    # Show files to be processed
    console.print(f"\n[bold]Found {len(audio_files)} file(s) to process:[/bold]")
    for idx, file in enumerate(audio_files, 1):
        console.print(f"  {idx}. {file.name}")
    console.print()

    # Create batch processor
    processor = BatchProcessor(
        party_id=party,
        num_speakers=num_speakers,
        resume_enabled=resume,
        output_dir=output_dir
    )

    # Process batch
    try:
        report = processor.process_batch(
            files=audio_files,
            skip_diarization=skip_diarization,
            skip_classification=skip_classification,
            skip_snippets=skip_snippets,
            skip_knowledge=skip_knowledge
        )

        # Display summary
        console.print("\n[bold green]✓ Batch processing completed![/bold green]")
        console.print(f"\n{report.summary_markdown()}")

        # Save report
        if output_dir:
            report_path = Path(output_dir) / "batch_report.md"
        else:
            report_path = Config.OUTPUT_DIR / "batch_report.md"

        report.save(report_path)
        console.print(f"\n[dim]Full report saved to: {report_path}[/dim]")
        console.print(f"[dim]Verbose log: {get_log_file_path()}[/dim]")

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Batch processing interrupted by user[/yellow]")
        console.print("[dim]Progress has been checkpointed. Use --resume to continue.[/dim]")
        raise click.Abort()
    except Exception as e:
        console.print(f"\n[bold red]✗ Batch processing failed: {e}[/bold red]")
        console.print(f"[dim]Inspect log for details: {get_log_file_path()}[/dim]")
        raise click.Abort()


@cli.command("generate-story")
@click.argument("session_ids", nargs=-1)
@click.option(
    "--all",
    "process_all",
    is_flag=True,
    help="Generate narratives for all available sessions.",
)
@click.option(
    "--characters",
    "-c",
    multiple=True,
    help="Character perspectives to generate (repeatable). Defaults to all characters.",
)
@click.option(
    "--skip-narrator",
    is_flag=True,
    help="Skip generating the narrator summary.",
)
@click.option(
    "--temperature",
    type=click.FloatRange(0.0, 1.0),
    default=0.5,
    show_default=True,
    help="Sampling temperature passed to the story generator.",
)
@click.option(
    "--context-file",
    type=click.Path(exists=True, dir_okay=False),
    help="Optional text file with notebook context to include in prompts.",
)
def generate_story(session_ids, process_all, characters, skip_narrator, temperature, context_file):
    """Generate story notebook narratives from processed sessions."""
    manager = StoryNotebookManager()

    if process_all:
        target_sessions = manager.list_sessions(limit=None)
    else:
        target_sessions = list(session_ids)

    if not target_sessions:
        raise click.UsageError("Provide at least one SESSION_ID or use --all.")

    notebook_context = load_notebook_context_file(Path(context_file)) if context_file else ""

    for session_id in target_sessions:
        try:
            session = manager.load_session(session_id)
        except FileNotFoundError:
            console.print(f"[yellow]Skipping {session_id}: processed session data not found.[/yellow]")
            continue

        console.print(f"\n[bold cyan]Session:[/bold cyan] {session.session_id}")
        table = Table(title=f"Narratives for {session.session_id}")
        table.add_column("Perspective", style="cyan")
        table.add_column("Saved Path", style="green")

        generated = False

        if not skip_narrator:
            _, path = manager.generate_narrator(
                session,
                notebook_context=notebook_context,
                temperature=temperature,
            )
            if path:
                table.add_row("Narrator", str(path))
                generated = True

        requested_characters = list(characters) if characters else session.character_names
        if characters:
            missing = [name for name in characters if name not in session.character_names]
            if missing:
                console.print(f"[yellow]Skipping unknown characters for {session.session_id}: {', '.join(missing)}[/yellow]")
            requested_characters = [name for name in characters if name in session.character_names]

        for character_name in requested_characters:
            _, path = manager.generate_character(
                session,
                character_name=character_name,
                notebook_context=notebook_context,
                temperature=temperature,
            )
            if path:
                table.add_row(character_name, str(path))
                generated = True

        if generated and table.row_count:
            console.print(table)
        else:
            console.print("[yellow]No narratives generated for this session.[/yellow]")


@cli.command()
@click.option(
    '--all',
    'ingest_all',
    is_flag=True,
    help='Ingest all sessions and knowledge bases'
)
@click.option(
    '--session',
    help='Ingest a specific session by ID'
)
@click.option(
    '--rebuild',
    is_flag=True,
    help='Rebuild entire index (clear + ingest all)'
)
@click.option(
    '--output-dir',
    type=click.Path(exists=True),
    default=None,
    help='Output directory containing sessions (default: ./output)'
)
@click.option(
    '--knowledge-dir',
    type=click.Path(exists=True),
    default=None,
    help='Directory containing knowledge base files (default: ./models)'
)
def ingest(ingest_all, session, rebuild, output_dir, knowledge_dir):
    """Ingest session data into vector database for semantic search"""

    try:
        from src.langchain.embeddings import EmbeddingService
        from src.langchain.vector_store import CampaignVectorStore
        from src.langchain.data_ingestion import DataIngestor
    except ImportError as e:
        console.print(f"[red]Error:[/red] LangChain dependencies not installed")
        console.print(f"Run: pip install langchain langchain-community chromadb sentence-transformers")
        console.print(f"Details: {e}")
        return

    # Set default directories
    if output_dir is None:
        output_dir = Config.OUTPUT_DIR

    if knowledge_dir is None:
        knowledge_dir = Config.MODELS_DIR

    output_dir = Path(output_dir)
    knowledge_dir = Path(knowledge_dir)

    console.print("[cyan]Initializing vector store...[/cyan]")

    try:
        # Initialize embedding service and vector store
        embedding_service = EmbeddingService()
        vector_store = CampaignVectorStore(
            persist_dir=Config.PROJECT_ROOT / "vector_db",
            embedding_service=embedding_service
        )

        ingestor = DataIngestor(vector_store)

        if rebuild:
            console.print("[yellow]Rebuilding entire index (this will clear existing data)...[/yellow]")
            stats = ingestor.ingest_all(output_dir, knowledge_dir, clear_existing=True)

            console.print("\n[bold green]Rebuild Complete![/bold green]")
            table = Table(title="Ingestion Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Count", style="green")

            table.add_row("Sessions Ingested", str(stats["sessions_ingested"]))
            table.add_row("Sessions Failed", str(stats["sessions_failed"]))
            table.add_row("Total Segments", str(stats["total_segments"]))
            table.add_row("Knowledge Bases Ingested", str(stats["knowledge_bases_ingested"]))
            table.add_row("Knowledge Bases Failed", str(stats["knowledge_bases_failed"]))
            table.add_row("Total Documents", str(stats["total_documents"]))

            console.print(table)

        elif ingest_all:
            console.print("[cyan]Ingesting all sessions and knowledge bases...[/cyan]")
            stats = ingestor.ingest_all(output_dir, knowledge_dir, clear_existing=False)

            console.print("\n[bold green]Ingestion Complete![/bold green]")
            table = Table(title="Ingestion Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Count", style="green")

            table.add_row("Sessions Ingested", str(stats["sessions_ingested"]))
            table.add_row("Sessions Failed", str(stats["sessions_failed"]))
            table.add_row("Total Segments", str(stats["total_segments"]))
            table.add_row("Knowledge Bases Ingested", str(stats["knowledge_bases_ingested"]))
            table.add_row("Knowledge Bases Failed", str(stats["knowledge_bases_failed"]))
            table.add_row("Total Documents", str(stats["total_documents"]))

            console.print(table)

        elif session:
            console.print(f"[cyan]Ingesting session: {session}[/cyan]")
            session_dir = output_dir / session

            result = ingestor.ingest_session(session_dir)

            if result.get("success"):
                console.print(f"[green]Successfully ingested {result['segments_count']} segments from {session}[/green]")
            else:
                console.print(f"[red]Error:[/red] {result.get('error', 'Unknown error')}")

        else:
            console.print("[yellow]Please specify --all, --session, or --rebuild[/yellow]")
            console.print("\nExamples:")
            console.print("  python cli.py ingest --all")
            console.print("  python cli.py ingest --session session_005")
            console.print("  python cli.py ingest --rebuild")

        # Show vector store stats
        stats = vector_store.get_stats()
        console.print(f"\n[cyan]Vector Store Stats:[/cyan]")
        console.print(f"  Transcript Segments: {stats['transcript_segments']}")
        console.print(f"  Knowledge Documents: {stats['knowledge_documents']}")
        console.print(f"  Total: {stats['total_documents']}")
        console.print(f"  Persist Dir: {stats['persist_dir']}")

    except Exception as e:
        console.print(f"[red]Error during ingestion:[/red] {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    cli()
