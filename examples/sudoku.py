from resolvelib import BaseReporter, Resolver, AbstractProvider


class Requirement:
    def __init__(self, row, column, invalid):
        self.row = row
        self.column = column
        self.invalid = invalid
        self.identifier = (self.row, self.column)


class ClueRequirement:
    def __init__(self, row, column, assigned=None):
        self.row = row
        self.column = column
        self.assigned = assigned


class Candidate:
    def __init__(self, row, column, value):
        self.row = row
        self.column = column
        self.value = value
        self._dependencies = None

    def _get_dependencies(self):
        same_column = [
            Requirement(i, self.column, self.value) for i in range(9) if i != self.row
        ]
        same_row = [
            Requirement(self.row, i, self.value) for i in range(9) if i != self.column
        ]
        row_start = self.row - self.row % 3
        column_start = self.column - self.column % 3
        same_box = [
            Requirement(row_start + i, column_start + j, self.value)
            for i in range(3)
            for j in range(3)
            if (row_start + i) != self.row and (column_start + j) != self.column
        ]
        return same_column + same_row + same_box

    @property
    def dependencies(self):
        if self._dependencies is None:
            self._dependencies = list(self._get_dependencies())
        return self._dependencies


class SudokuProvider(AbstractProvider):
    def identify(self, requirement_or_candidate):
        return (requirement_or_candidate.row, requirement_or_candidate.column)

    def get_preference(
        self, identifier, resolutions, candidates, information, backtrack_causes
    ):
        # prefer indentifiers from the puzzle's clues
        for ri in information[identifier]:
            if isinstance(ri, ClueRequirement):
                return 0
        return 1

    def find_matches(self, identifier, requirements, incompatibilities):
        row, column = identifier
        invalid_values = set()
        for req in requirements[identifier]:
            if isinstance(req, ClueRequirement):
                return [Candidate(row, column, req.assigned)]
            invalid_values.add(req.invalid)
        for incomp in incompatibilities[identifier]:
            invalid_values.add(incomp.value)
        candidates = [
            Candidate(row, column, value)
            for value in range(1, 10)
            if value not in invalid_values
        ]
        return candidates

    def is_satisfied_by(self, requirement, candidate):
        if isinstance(requirement, ClueRequirement):
            return requirement.assigned == candidate.value
        elif requirement.invalid:
            return requirement.invalid != candidate.value
        else:
            return True

    def get_dependencies(self, candidate):
        return candidate.dependencies


def main():
    provider = SudokuProvider()
    reporter = BaseReporter()
    resolver = Resolver(provider, reporter)
    clues = [
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9],
    ]
    print("Clues:")
    for i in range(9):
        print(" ".join(str(clues[i][j]) for j in range(9)))
    requirements = [
        ClueRequirement(i, j, clues[i][j])
        for i in range(9)
        for j in range(9)
        if clues[i][j] != 0
    ]
    solution = resolver.resolve(requirements, max_rounds=500)
    print("Solution:")
    for i in range(9):
        print(" ".join(str(solution.mapping[(i, j)].value) for j in range(9)))


if __name__ == "__main__":
    main()
