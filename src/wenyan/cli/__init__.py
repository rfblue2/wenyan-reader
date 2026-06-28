import typer

app = typer.Typer(no_args_is_help=True)
preprocess_app = typer.Typer(no_args_is_help=True)
app.add_typer(preprocess_app, name="preprocess")

from wenyan.cli import preprocess as _preprocess  # noqa: E402, F401
