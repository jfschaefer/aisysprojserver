""" The environment settings tells the server how to work with the environment.

Note that only the relevant subset of settings is actually used.
"""


class EnvSettings:
    # ************************
    # * SETTINGS FOR RATINGS *
    # ************************

    # Rating for new agents
    INITIAL_RATING: float = 0.0

    # Strategy for computing the rating of an agent.
    # Possible values:
    #     "average": Average of ``MIN_RUNS_FOR_FULLY_EVALUATED`` runs
    RATING_STRATEGY: str = 'average'

    # Number of runs required to accept the rating
    MIN_RUNS_FOR_FULLY_EVALUATED: int = 50

    # What kind of rating agents strive for.
    # Possible values:
    #     "max": Maximize the rating
    #     "min": Minimize the rating
    RATING_OBJECTIVE: str = 'max'


    # ********************************
    # * SETTINGS FOR ACTION REQUESTS *
    # ********************************

    # (maximum) number of action requests sent per response
    NUMBER_OF_ACTION_REQUESTS: int = 5
