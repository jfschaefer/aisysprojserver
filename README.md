**IMPORTANT:** The following is a sketch (the final implementation will be based on it, but likely differ in some aspects)

## Terminology
* **Agent**
* **Environment**
* **Run**
* **Performance**
* **Action**
* **Action request**
* **Percept**


## Environment API

Ideas:
* Different environment types (single player, multiplayer, verification, ...) with potentially different database tables, agent classes, ...
* Three different classes: agent model (sqlalchemy), agent (backend, has instance of agent model), agent data (passed to environment)


```python
class State:
    def to_string(self):
        ...
    
    @classmethod
    def from_string(cls):
        ...


class Environment:
    SETTING1: ...
    SETTING2: ...
    ...

    def act(self, action, run_data) -> ActionResult:
        ...
    def view_run(self, run_data):
        ...
    def view_agent(self, agent_data):
        ...
    def view_env(self, env_data):
        ...
```


## REST protocol sketch

Idea: keep it very simple to make it easy to implement agents in new languages (e.g. don't use parameters, headers, ...)


### User management

`POST` to `/makeagent/<env>/<agent>`:
```json
{
  "admin-auth": "authentication",
  "overwrite": true
}
```
Responds with partial agent config

`POST` to `/makeagent/<env>` (if we allow direct user sign-up):
Responds with partial agent config (generates agent name).


`PUT` to `/manage/block-agent`:
```json
{
"name": "agent-name",       // optional (otherwise a name will be assigned)
"admin-auth": "authentication",   // optional (if no direct user signup)
"pwd": "agent-password",    // alternative to using "admin-auth"
"env": "environment name"
}
```

### Actions
To server (`PUT` or `GET`) at `/act/{ENV}`:
```json
{
  "name": "agent-name",
  "pwd": "agent-password",
  "actions": [
    {"run":  "run-id", "action": ...},
    ...
  ],
  "config": {
    "single-request": false,
    ...
  }
}
```

From server:
```json
{
  "errors": [],
  "messages": [],
  "action-requests": [
    {"run":  "run-id", "percept": ...}
  ]
}
```

### Verification
`GET` to `/verify/{ENV}`, request content depends on `ENV`.

### Web interface
* `/`: All environments
* `/env/{ENV}`: Overview of environment
* `/agent/{ENV}/{AGENT}`: Overview of an agent
* `/run/{ENV}/{RUN}`: Overview of a run
