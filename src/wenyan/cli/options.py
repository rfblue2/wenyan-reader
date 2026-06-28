import typer

force_option = typer.Option(False, "--force", help="Rerun even when artifacts are current.")
dry_run_option = typer.Option(False, "--dry-run", help="Show what would run without writing.")
json_option = typer.Option(False, "--json", help="Emit machine-readable output.")
