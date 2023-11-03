Terminology: Agents and Environments
====================================

Unfortunately, the terminology definitions are a bit circular, but you should get the idea.
It is inspired by the idea of intelligent agents in AI.
As an example, we will assume that the task for the students is to implement
code for playing chess.

* An **agent** an entity that perceives its environment through sensors and performs actions.
  In the example, the agent would the implemented by the student's code.
* An **action** is something the agent does.
  In the example, it would be a move in the game of chess.
* An **environment** is the world in which the agent operates.
  In the example, it would be the chess board, but also the opponent.
  It could make sense to have multiple environments, each with a different opponent strength.
* A **state** is the current situation of the environment.
  In the example, it would be the current position of the pieces on the board.
* A **run** is one execution of the agent in the environment, often involving multiple actions.
  In the example, it would be one game of chess.
* The **outcome** is the result of a run that describes the performance of the agent.
  In the example, it would be the result of the game, i.e., win, loss, or draw.
  Typically, we would use a numerical value to describe the outcome, e.g., 1 for a win, 0 for a loss,
  and 0.5 for a draw.
* The **rating** of an agent describes its performance over many runs.
  It is computed from the outcomes.
  In the example, it would be the average outcome over many games.
* An **action request** is a request from the environment to the agent to perform an action.
  In the example, it would be a request to make a move.
  The request usually contains further information about the current state of the environment.
* An **agent configuration** is a JSON object/file that contains the credentials of an agent,
  i.e. its user name, its password (set by the server), its environment, and the server URL.
