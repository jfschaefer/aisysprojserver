from pathlib import Path

import jinja2
from flask import url_for
from flask_caching import Cache
from werkzeug.exceptions import NotFound, BadRequest

from aisysprojserver import __version__
from aisysprojserver.active_env import ActiveEnvironment
from aisysprojserver.agent_account import AgentAccount
from aisysprojserver.agent_data import AgentData
from aisysprojserver.group import Group
from aisysprojserver.plugins import PluginManager
from aisysprojserver.run import Run
from aisysprojserver.telemetry import MonitoredBlueprint

AISYSPROJ_TEMPLATES: Path = Path(__file__).parent / 'templates'
TEMPLATE_STANDARD_KWARGS: dict = {
    'url_for': url_for,
    'format': format,
    'SERVER_VERSION': __version__,
}

cache = Cache()
bp = MonitoredBlueprint('website', __name__)

_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(AISYSPROJ_TEMPLATES),
    autoescape=jinja2.select_autoescape()
)


@bp.route('/')
@cache.cached(timeout=10)
def frontpage():
    return group_page('main')


@bp.route('/group/<group>')
@cache.cached(timeout=10)
def group_page(group: str):
    group = Group(group)
    if not group.exists():
        raise NotFound()
    envs_list: list[ActiveEnvironment] = group.get_envs()
    envs_list.sort(key=lambda ae: ae.identifier)
    subgroup_list: list[Group] = group.get_subgroups()
    subgroup_list.sort(key=lambda g: g.identifier, reverse=True)

    return _jinja_env.get_template('group_page.html').render(
        title=group.display_name,
        description=group.description,
        # TODO: why do we need *.identifier[0] instead of just *.identifier?
        envs=[(url_for('website.env_page', env=env.identifier[0]), env.display_name) for env in envs_list],
        subgroups=[(url_for('website.group_page', group=g.identifier[0]), g.display_name) for g in subgroup_list],
        **TEMPLATE_STANDARD_KWARGS
    )


@bp.route('/env/<env>')
@cache.cached(timeout=10)
def env_page(env: str):
    active_env = ActiveEnvironment(env)
    if not active_env.exists():
        raise NotFound()
    return active_env.get_env_instance().view_env(active_env.get_env_data())


@bp.route('/agent/<env>/<agent>')
@cache.cached(timeout=5)
def agent_page(env: str, agent: str):
    active_env = ActiveEnvironment(env)
    if not active_env.exists():
        raise NotFound()
    agent_data = AgentData(f'{env}/{agent}')
    if not agent_data.exists():
        if AgentAccount(env, agent).exists():
            return _jinja_env.get_template('agent_without_runs.html').render(agent_identifier=agent,
                                                                             **TEMPLATE_STANDARD_KWARGS)
        raise NotFound()
    return active_env.get_env_instance().view_agent(agent_data.to_agent_data_summary())


@bp.route('/run/<env>/<runid>')
@cache.cached(timeout=3)
def run_page(env: str, runid: str):
    active_env = ActiveEnvironment(env)
    if not active_env.exists():
        raise NotFound()
    run = Run(runid)
    if not run.exists():
        raise NotFound()
    if run.env_str() != active_env.identifier:
        raise BadRequest(f'Run {runid} is not part of {env}')
    return active_env.get_env_instance().view_run(run.to_run_data())


@bp.route('/plugins')
@cache.cached(timeout=3)
def plugins_page():
    plugins = [(plugin.package_name, plugin.version) for plugin in PluginManager.plugins.values()]
    plugins.sort()
    return _jinja_env.get_template('plugins_page.html').render(plugins=plugins, **TEMPLATE_STANDARD_KWARGS)
