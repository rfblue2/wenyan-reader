import typer

force_option = typer.Option(False, "--force", help="Rerun even when artifacts are current.")
dry_run_option = typer.Option(False, "--dry-run", help="Show what would run without writing.")
json_option = typer.Option(False, "--json", help="Emit machine-readable output.")

CHAPTER_REF_HELP = "Chapter UUID, number (e.g. 1), or title (e.g. 始計第一)"
PARAGRAPH_REF_HELP = (
    "Paragraph UUID or number (requires --chapter for numbers). "
    "With --segment: disambiguates segment ordinals. "
    "Without --segment: run all pending segments in the paragraph."
)
SEGMENT_REF_HELP = "Segment UUID or number (requires --paragraph for numbers)"
