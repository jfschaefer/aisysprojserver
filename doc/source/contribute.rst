Contribute
==========


Of course, you are welcome to contribute to this project and you are always invited to reach out to discuss ideas, issues, or potential contributions.


Project Structure
-----------------

*TODO*


Processes
---------

Checks before committing
~~~~~~~~~~~~~~~~~~~~~~~~

Before committing, please make sure that the following checks are successful:

- `flake8` runs successfully
- `python3 -m unittest discover` runs successfully


Releases
~~~~~~~~

- Update the version number in `pyproject.toml`
- Update the version number in `aisysprojserver/__init__.py`
- Make a new release on docker hub:

.. code:: bash

    sudo docker build -t jfschaefer/gs:0.0.5 .
    sudo docker build -t jfschaefer/gs:latest .
    sudo docker push jfschaefer/gs:0.0.5
    sudo docker push jfschaefer/gs:latest

Instead of ``0.0.5``, use the new version number.
