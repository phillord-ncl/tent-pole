import click

from . import file
from . import page

@click.group()
def main():
    pass

main.add_command(page.page)
