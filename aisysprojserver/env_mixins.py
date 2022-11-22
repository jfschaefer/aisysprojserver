import jinja2

from aisysprojserver.env_interface import EnvData, AgentDataSummary
from aisysprojserver.env_settings import EnvSettings
from aisysprojserver.website import AISYSPROJ_TEMPLATES, TEMPLATE_STANDARD_KWARGS

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(AISYSPROJ_TEMPLATES),
    autoescape=jinja2.select_autoescape(),
    trim_blocks=True
)


class SimpleViewEnv:
    settings: EnvSettings

    def view_env(self, env_data: EnvData) -> str:
        evaluated_agents = [agent_data for agent_data in env_data.agents if agent_data.fully_evaluated]
        unevaluated_agents = [agent_data for agent_data in env_data.agents if not agent_data.fully_evaluated]
        match self.settings.RATING_OBJECTIVE:
            case 'max':
                key_fun = lambda agent_data: -agent_data.agent_rating
            case 'min':
                key_fun = lambda agent_data: agent_data.agent_rating
            case other:
                raise NotImplementedError(f'Unsupported rating object {other}')
        evaluated_agents.sort(key=key_fun)
        unevaluated_agents.sort(key=lambda ad: ad.agent_name)

        return jinja_environment.get_template('simple_env_view.html').render(
            env=self, env_data=env_data,
            evaluated_agents=evaluated_agents,
            unevaluated_agents=unevaluated_agents,
            **TEMPLATE_STANDARD_KWARGS
        )


class SimpleViewAgent:
    settings: EnvSettings

    def view_agent(self, agent_data: AgentDataSummary) -> str:
        return jinja_environment.get_template('simple_agent_view.html').render(
            env=self,
            agent_data=agent_data,
            **TEMPLATE_STANDARD_KWARGS
        )
