"""
The two problems of the COMPUTE 2026 WG study, each expanded into its four
variants (2 forms of the specification x 2 kinds of bug), giving the eight
study Task rows:

    P1_Direct_buggy1  P1_Contextualized_buggy1  P1_Direct_buggy2  P1_Contextualized_buggy2
    P2_Direct_buggy1  P2_Contextualized_buggy1  P2_Direct_buggy2  P2_Contextualized_buggy2

Within a problem, everything except the description (and its validator) is
identical across forms: same function name, same reference solution, same
buggy programs, and the same Step 2 inputs for both bugs. That is what lets
any difference between forms be attributed to the specification.

Authoring rules, checked by check_study_tasks.py:
- No Step 2 input and no Step 1 example input is a counter-example for
  either buggy program (Step 2 measures tracing, not bug-finding, and an
  example's revealed output must not hand over a counter-example).
- The paper's counter-examples are counter-examples, and the contextualized
  validator accepts them.

Code-mixed text lives in code_mixed.py, keyed by native language code
(see the NATIVE_LANGUAGES list in frontend/src/components/StudyIntro.jsx).
A language with no entry simply gets no code-mixed toggle.
"""
from assignment import variant_key
from code_mixed import CODE_MIXED

STEP3_MAX_ATTEMPTS = 3

# ---------------------------------------------------------------------------
# P1: threshold (heart-rate monitor)
# ---------------------------------------------------------------------------

P1 = dict(
    key="P1",
    function_signature="def has_large_change(readings, T):",
    correct_code=(
        "def has_large_change(readings, T):\n"
        "    for i in range(len(readings) - 1):\n"
        "        if abs(readings[i+1] - readings[i]) > T:\n"
        "            return True\n"
        "    return False\n"
    ),
    forms=dict(
        direct=dict(
            description=(
                "Write a function `has_large_change(readings, T)` that takes a "
                "list of integer `readings` and a positive integer `T`. It "
                "returns `True` if the absolute difference between some pair of "
                "consecutive elements of `readings` is greater than `T`, and "
                "`False` otherwise. The list may be empty or contain a single "
                "element."
            ),
            description_mixed=CODE_MIXED["P1"]["direct"],
            input_validator=(
                "def valid(readings, T):\n"
                "    if not isinstance(readings, list) or not all(type(r) is int for r in readings):\n"
                "        return 'readings must be a list of whole numbers.'\n"
                "    if type(T) is not int or T <= 0:\n"
                "        return 'T must be a positive whole number.'\n"
                "    return None\n"
            ),
        ),
        contextualized=dict(
            description=(
                "A hospital's patient monitor records a patient's heart rate, in "
                "beats per minute (bpm), once every second. A healthy heart rate "
                "changes only slightly from one second to the next. The "
                "hospital's clinical guidelines say that a nurse must review a "
                "recording if the heart rate ever changes by more than `T` bpm "
                "between two consecutive readings: a sudden drop can mean the "
                "heart is failing, and a sudden rise can mean the patient is in "
                "distress. A recording may be empty or contain a single reading, "
                "for example if the monitor was just attached. Write a function "
                "`has_large_change(readings, T)` that takes the list of readings "
                "(whole numbers) and the threshold `T` (a positive whole number), "
                "and returns `True` if the recording needs review, and `False` "
                "otherwise."
            ),
            description_mixed=CODE_MIXED["P1"]["contextualized"],
            # Plausibility ranges are a WG content decision — confirm before
            # the pilot.
            input_validator=(
                "def valid(readings, T):\n"
                "    if not isinstance(readings, list) or not all(type(r) is int for r in readings):\n"
                "        return 'readings must be a list of whole numbers.'\n"
                "    if type(T) is not int or T <= 0:\n"
                "        return 'T must be a positive whole number.'\n"
                "    if any(r < 30 or r > 220 for r in readings) or T > 60:\n"
                "        return ('Your input must be a realistic recording: every heart rate '\n"
                "                'between 30 and 220 bpm, and T at most 60 bpm.')\n"
                "    return None\n"
            ),
        ),
    ),
    bugs=dict(
        # Context-independent: returns after checking only the first pair.
        buggy1=dict(
            code=(
                "def has_large_change(readings, T):\n"
                "    for i in range(len(readings) - 1):\n"
                "        if abs(readings[i+1] - readings[i]) > T:\n"
                "            return True\n"
                "        else:\n"
                "            return False\n"
                "    return False\n"
            ),
            buggy_line_numbers=[5, 6],
            counterexamples=["has_large_change([70, 72, 110], 15)"],
        ),
        # Context-sensitive: compares the first reading with 0.
        buggy2=dict(
            code=(
                "def has_large_change(readings, T):\n"
                "    prev = 0\n"
                "    for r in readings:\n"
                "        if abs(r - prev) > T:\n"
                "            return True\n"
                "        prev = r\n"
                "    return False\n"
            ),
            buggy_line_numbers=[2],
            counterexamples=["has_large_change([72, 74], 15)"],
        ),
    ),
    # Shared by both bugs and both forms; neither is a counter-example for
    # either bug (first pair small and first reading <= T; first pair large).
    trace_sample_inputs=["has_large_change([3, 5, 4], 5)"],
    trace_data_flow_inputs=["has_large_change([2, 10, 11], 5)"],
    # Plausible under the context, and not a counter-example for either bug
    # (the large change is in the first pair; the empty recording).
    io_example_inputs=["has_large_change([70, 95, 96], 15)", "has_large_change([], 10)"],
    # Legal under the direct form but not a heart-rate recording.
    implausible_examples=["has_large_change([-5, 20], 15)"],
)

# ---------------------------------------------------------------------------
# P2: warmest night (Leh, January)
# ---------------------------------------------------------------------------

P2 = dict(
    key="P2",
    function_signature="def warmest(temps):",
    correct_code=(
        "def warmest(temps):\n"
        "    best = temps[0]\n"
        "    best_day = 1\n"
        "    for i in range(len(temps)):\n"
        "        if temps[i] > best:\n"
        "            best = temps[i]\n"
        "            best_day = i + 1\n"
        "    return best_day\n"
    ),
    forms=dict(
        direct=dict(
            description=(
                "Write `warmest(temps)` that takes a non-empty list of numbers "
                "and returns the position of its largest value, counting "
                "positions from 1. If the largest value occurs more than once, "
                "return the smallest such position."
            ),
            description_mixed=CODE_MIXED["P2"]["direct"],
            input_validator=(
                "def valid(temps):\n"
                "    if not isinstance(temps, list) or len(temps) == 0:\n"
                "        return 'temps must be a non-empty list of numbers.'\n"
                "    if not all(type(t) in (int, float) for t in temps):\n"
                "        return 'temps must be a non-empty list of numbers.'\n"
                "    return None\n"
            ),
        ),
        contextualized=dict(
            description=(
                "A weather station in Leh, one of the coldest inhabited places in "
                "India, records the lowest temperature of each night in January, "
                "in degrees Celsius to one decimal place. The list has at least 1 "
                "entry, starts with the night of 1 January and has one entry per "
                "night, up to the most recent night recorded. The district "
                "administration wants to know which night was the warmest. Write "
                "`warmest(temps)` that takes the list and returns the date in "
                "January of the warmest night. If more than one night was equally "
                "warm, return the earliest date."
            ),
            description_mixed=CODE_MIXED["P2"]["contextualized"],
            # Plausibility ranges are a WG content decision — confirm before
            # the pilot.
            input_validator=(
                "def valid(temps):\n"
                "    if not isinstance(temps, list) or len(temps) == 0:\n"
                "        return 'temps must be a non-empty list of numbers.'\n"
                "    if not all(type(t) in (int, float) for t in temps):\n"
                "        return 'temps must be a non-empty list of numbers.'\n"
                "    if (len(temps) > 31 or any(t < -40 or t > 10 for t in temps)\n"
                "            or any(round(t, 1) != t for t in temps)):\n"
                "        return ('Your input must be a realistic record: at most 31 nights, '\n"
                "                'each temperature between -40.0 and 10.0 degrees Celsius, '\n"
                "                'to one decimal place.')\n"
                "    return None\n"
            ),
        ),
    ),
    bugs=dict(
        # Context-independent: returns the last of several equally warm nights.
        buggy1=dict(
            code=(
                "def warmest(temps):\n"
                "    best = temps[0]\n"
                "    best_day = 1\n"
                "    for i in range(len(temps)):\n"
                "        if temps[i] >= best:\n"
                "            best = temps[i]\n"
                "            best_day = i + 1\n"
                "    return best_day\n"
            ),
            buggy_line_numbers=[5],
            counterexamples=["warmest([-9.8, -12.0, -9.8])"],
        ),
        # Context-sensitive: starts the maximum at 0.
        buggy2=dict(
            code=(
                "def warmest(temps):\n"
                "    best = 0\n"
                "    best_day = 1\n"
                "    for i in range(len(temps)):\n"
                "        if temps[i] > best:\n"
                "            best = temps[i]\n"
                "            best_day = i + 1\n"
                "    return best_day\n"
            ),
            buggy_line_numbers=[2],
            counterexamples=["warmest([-14.2, -9.8])"],
        ),
    ),
    # Positive maximum, no ties: correct for both bugs.
    trace_sample_inputs=["warmest([2.5, 6.0, 4.0])"],
    trace_data_flow_inputs=["warmest([1.0, 3.5])"],
    # Plausible in Leh and not a counter-example for either bug (warmest
    # night is the first; or the maximum is above zero; no ties).
    io_example_inputs=["warmest([-2.0, -9.5, -11.0])", "warmest([1.5, -6.0, 3.0])"],
    implausible_examples=["warmest([3.0, 7.5, 5.0, 25.0])"],
)

STUDY_PROBLEMS = [P1, P2]


def make_variants(problem: dict) -> list:
    """Expand one problem into its four Task dicts (form x bug)."""
    variants = []
    for bug_kind, bug in problem["bugs"].items():
        for form, spec in problem["forms"].items():
            key = variant_key(problem["key"], form, bug_kind)
            variants.append(dict(
                title=key,
                language="python",
                variant_key=key,
                problem_key=problem["key"],
                form=form,
                bug_kind=bug_kind,
                description=spec["description"],
                description_mixed=spec["description_mixed"],
                input_validator=spec["input_validator"],
                step3_max_attempts=STEP3_MAX_ATTEMPTS,
                function_signature=problem["function_signature"],
                correct_code=problem["correct_code"],
                buggy_code=bug["code"],
                trace_sample_inputs=problem["trace_sample_inputs"],
                trace_data_flow_inputs=problem["trace_data_flow_inputs"],
                buggy_line_numbers=bug["buggy_line_numbers"],
                trace_prefill_steps=1,
                trace_omit_unchanged_vars=False,
                io_example_inputs=problem["io_example_inputs"],
                # The study design has no mutation-reflection probe.
                mutation_line_number=None,
                mutation_new_line_text=None,
                mutation_prompt=None,
            ))
    return variants


STUDY_TASKS = [v for p in STUDY_PROBLEMS for v in make_variants(p)]
