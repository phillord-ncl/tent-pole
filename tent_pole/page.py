import click

@click.group()
def page():
    pass

@page.command()
def create():
    pass

@page.command()
def update():
    pass

@page.command()
def create_update():
    pass
