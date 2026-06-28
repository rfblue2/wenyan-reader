import typer

app = typer.Typer(no_args_is_help=True)
preprocess_app = typer.Typer(no_args_is_help=True)
app.add_typer(preprocess_app, name="preprocess")
