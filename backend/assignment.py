"""
Counterbalanced assignment of study task variants to participants.

Every participant attempts both problems (P1, P2), one in each form of the
specification, and sees one of each problem's two buggy programs. A row of
CONDITIONS fixes all of that plus the order of the two problems:

    row  P1 form  P1 bug   P2 form  P2 bug   order
     0   direct   buggy1   context  buggy1   P1, P2
     1   direct   buggy2   context  buggy2   P1, P2
     2   context  buggy1   direct   buggy2   P1, P2
     3   context  buggy2   direct   buggy1   P1, P2
    4-7  as 0-3                              P2, P1

Any 4 consecutive rows (0-3 or 4-7) show every form x bug combination of each
problem exactly once, and the 8 rows together balance the order as well.

Participants are assigned in permuted blocks of 8 per institute: the n-th
participant at an institute (slot n) takes row block_permutation(institute,
n // 8)[n % 8]. The permutation is seeded from the institute and block
number, so an assignment can always be reproduced from the slot alone.
"""
import hashlib
import random
from typing import Dict, List, Tuple

PROBLEMS = ("P1", "P2")

# (P1 form, P1 bug, P2 form, P2 bug, order)
CONDITIONS: List[Tuple[str, str, str, str, Tuple[str, str]]] = [
    ("direct", "buggy1", "contextualized", "buggy1", ("P1", "P2")),
    ("direct", "buggy2", "contextualized", "buggy2", ("P1", "P2")),
    ("contextualized", "buggy1", "direct", "buggy2", ("P1", "P2")),
    ("contextualized", "buggy2", "direct", "buggy1", ("P1", "P2")),
    ("direct", "buggy1", "contextualized", "buggy1", ("P2", "P1")),
    ("direct", "buggy2", "contextualized", "buggy2", ("P2", "P1")),
    ("contextualized", "buggy1", "direct", "buggy2", ("P2", "P1")),
    ("contextualized", "buggy2", "direct", "buggy1", ("P2", "P1")),
]
BLOCK_SIZE = len(CONDITIONS)


def block_permutation(institute: str, block: int) -> List[int]:
    seed = int(hashlib.sha256(f"{institute}|{block}".encode()).hexdigest(), 16)
    rows = list(range(BLOCK_SIZE))
    random.Random(seed).shuffle(rows)
    return rows


def condition_row_for_slot(institute: str, slot: int) -> int:
    return block_permutation(institute, slot // BLOCK_SIZE)[slot % BLOCK_SIZE]


def variant_key(problem: str, form: str, bug: str) -> str:
    """Matches the seeded Task.variant_key, e.g. "P1_Direct_buggy1"."""
    return f"{problem}_{form.capitalize()}_{bug}"


def variants_for_row(row: int) -> List[str]:
    """The two variant keys for a condition row, in presentation order."""
    p1_form, p1_bug, p2_form, p2_bug, order = CONDITIONS[row]
    by_problem: Dict[str, str] = {
        "P1": variant_key("P1", p1_form, p1_bug),
        "P2": variant_key("P2", p2_form, p2_bug),
    }
    return [by_problem[p] for p in order]
