# README

The AISysProj server is used in the AI Systems Project at [FAU](https://www.fau.de).
It is currently hosted at [https://aisysproj.kwarc.info](https://aisysproj.kwarc.info).
If you are interested in using it for your own project, you are invited to reach out.

The main goal of the server is to allow students to evaluate their solution to a problem.
Imagine, their task is to implement an algorithm for playing chess.
The students can run their code on their own machine, interacting with the server via HTTP requests.
They send moves for their own player, and the server makes the opponent's moves and returns the updated state
of the board.

This setup has a lot of advantages:

1. The students can use any programming language.
2. The students get immediate feedback.
3. The students do not have to run an evaluation framework on their own machine to get feedback.
4. The students do not get access to the engine making the opponent's moves, which can prevent cheating.
5. The students can compare their performance to the performance of other students,
   which allows for a competitive element.

It turns out that many different tasks can fit into this framework.

# Documentation

The documentation is hosted at [Read the Docs](https://aisysprojserver.readthedocs.io/en/latest/index.html).
