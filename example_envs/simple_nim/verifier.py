import itertools
import json
from pathlib import Path

from aisysprojserver import verify


class Verifier(verify.Verifier):
    def verify(self, data: bytes, data_path: Path) -> dict:
        """ asserts that the data is a valid sequence game (starting with 10) """
        sequence = json.loads(data)

        if not isinstance(sequence, list) and len(sequence) >= 1 and all(isinstance(item, int) for item in sequence):
            return {'result': 'failure'}

        if sequence[0] != 10:
            return {'result': 'invalid start'}
        if sequence[-1] != 0:
            return {'result': 'invalid end'}

        if not all(a - b in {1, 2, 3} for a, b in itertools.pairwise(sequence)):
            return {'result': 'invalid difference'}

        return {'result': 'success'}


VERIFIER = Verifier()
