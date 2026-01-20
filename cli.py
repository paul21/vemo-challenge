import os
import click
from flask.cli import with_appcontext
from flask import current_app
from app import db

@click.command()
@with_appcontext
def init_db():
    """Initialize the database."""
    db.create_all()
    click.echo('Initialized the database.')

def init_app(app):
    app.cli.add_command(init_db)
