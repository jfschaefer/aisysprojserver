from collections import defaultdict
from pathlib import Path

import jinja2
from flask import Blueprint, url_for
from flask_caching import Cache
from werkzeug.exceptions import NotFound, BadRequest

from aisysprojserver import __version__
from aisysprojserver.active_env import ActiveEnvironment, get_all_active_envs
from aisysprojserver.agent_account import AgentAccount
from aisysprojserver.agent_data import AgentData
from aisysprojserver.plugins import PluginManager
from aisysprojserver.run import Run

AISYSPROJ_TEMPLATES: Path = Path(__file__).parent / 'templates'
TEMPLATE_STANDARD_KWARGS: dict = {'url_for': url_for, 'format': format}

cache = Cache()
bp = Blueprint('website', __name__)

_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(AISYSPROJ_TEMPLATES),
    autoescape=jinja2.select_autoescape()
)


@bp.route('/')
@cache.cached(timeout=10)
def frontpage():
    envs_list: list[ActiveEnvironment] = get_all_active_envs()
    envs: dict[str, list[ActiveEnvironment]] = defaultdict(list)
    for env in envs_list:
        envs[env.display_group].append(env)
    for v in envs.values():
        v.sort(key=lambda ae: ae.display_name)

    urls: dict = {
        env.identifier: url_for('website.env_page', env=env.identifier)
        for env in envs_list
    }

    env_groups: list[str] = list(sorted(envs.keys(), reverse=True))

    return _jinja_env.get_template('frontpage.html').render(envs=envs, urls=urls, env_groups=env_groups,
                                                            version=__version__, **TEMPLATE_STANDARD_KWARGS)


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
    return _jinja_env.get_template('plugins_page.html').render(plugins=plugins, version=__version__,
                                                               **TEMPLATE_STANDARD_KWARGS)
