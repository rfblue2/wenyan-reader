import typer

app = typer.Typer(
    no_args_is_help=True,
    help="Local Classical Chinese reader tooling.",
)
preprocess_app = typer.Typer(
    no_args_is_help=True,
    help="Ingest sources, run preprocessing jobs, and inspect artifact progress.",
)
app.add_typer(preprocess_app, name="preprocess")

from wenyan.cli import preprocess as _preprocess  # noqa: E402, F401
