import functools
import json
from pathlib import Path

import click

from aisysprojserver_clienttools.admin import AdminClient


@click.group()
def admin_command():
    pass


def with_admin_client(f):
    @functools.wraps(f)
    @click.argument('authentication_file', type=click.Path(exists=True))
    def new_f(authentication_file, *args, **kwargs):
        # TODO: maybe special treatment for ``isinstance(authentication_file, AdminClient)``?
        return f(AdminClient.from_file(Path(authentication_file)), *args, **kwargs)
    return new_f


@admin_command.command()
@click.option('--overwrite/--no-overwrite', default=False,
              help='Overwrite user credentials if the account exists already')
@click.argument('username')
@click.argument('environment')
@with_admin_client
def new_user(admin_client: AdminClient, environment: str, username: str, overwrite: bool):
    print(json.dumps(admin_client.new_user(environment, username, overwrite)))


admin_command()
