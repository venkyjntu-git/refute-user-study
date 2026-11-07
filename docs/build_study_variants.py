"""
Generate docs/study_variants.tex — the eight study variants and the database
fields of a problem — from the live task definitions, so the document can
never drift from what the app actually serves.

    cd docs
    python build_study_variants.py         # writes study_variants.tex
    xelatex study_variants.tex && xelatex study_variants.tex

XeLaTeX (not pdflatex) is required for the code-mixed appendix: the Indic
scripts are set in Nirmala UI (ships with Windows 10+); change INDIC_FONT
below to e.g. "Noto Sans" families elsewhere.

Every output quoted in the document is computed here by running the
reference solution and the buggy programs on the quoted inputs.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "backend"))

from assignment import CONDITIONS          # noqa: E402
from code_mixed import CODE_MIXED          # noqa: E402
from seed_study import STUDY_PROBLEMS, STEP3_MAX_ATTEMPTS, rename_identifiers  # noqa: E402

INDIC_FONT = "Nirmala UI"
LANGS = [("te", "Telugu", "Telugu"), ("ta", "Tamil", "Tamil"), ("hi", "Hindi", "Devanagari"),
         ("gu", "Gujarati", "Gujarati"), ("de", "German", None)]
FORM_NAME = {"direct": "Direct", "contextualized": "Contextualized"}
BUG_NAME = {"buggy1": "Buggy1", "buggy2": "Buggy2"}
BUG_KIND = {"buggy1": "context-independent", "buggy2": "context-sensitive"}
PROBLEM_NAME = {"P1": "Threshold (heart-rate monitor)", "P2": "Warmest Night (Leh)"}


# ---------------------------------------------------------------------------
# running the programs
# ---------------------------------------------------------------------------

def run(code: str, call: str):
    ns = {}
    exec(code, ns)                      # trusted: the study's own programs
    return eval(call, ns)


def show(value) -> str:
    return repr(value)


# ---------------------------------------------------------------------------
# LaTeX helpers
# ---------------------------------------------------------------------------

_ESC = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
        "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def esc(s: str) -> str:
    return "".join(_ESC.get(ch, ch) for ch in s)


def prose(s: str) -> str:
    """Escape text and turn `code` spans into \\texttt."""
    parts = re.split(r"`([^`]*)`", s)
    return "".join(esc(p) if i % 2 == 0 else r"\texttt{" + esc(p) + "}" for i, p in enumerate(parts))


def code_tt(s: str) -> str:
    return r"\texttt{" + esc(s) + "}"


def listing(code: str, title: str, mark_lines=()) -> str:
    lines = code.rstrip("\n").split("\n")
    if mark_lines:
        width = max(len(l) for l in lines)
        lines = [l.ljust(width) + "   # <- bug" if i + 1 in mark_lines else l
                 for i, l in enumerate(lines)]
    body = "\n".join(lines)
    return f"\\begin{{lstlisting}}[title={{\\small {title}}}]\n{body}\n\\end{{lstlisting}}\n"


# ---------------------------------------------------------------------------
# hand-written explanations
# ---------------------------------------------------------------------------

BUG_EXPLANATION = {
    ("P1", "buggy1"): (
        "The \\texttt{else} branch returns \\texttt{False} as soon as the first pair is "
        "within \\texttt{T}, so the loop never looks past the first pair. A counter-example "
        "needs an unremarkable first pair followed by a large change."
    ),
    ("P1", "buggy2"): (
        "\\texttt{prev = 0} compares the first reading with a value that was never "
        "recorded. The program fails only when the first reading itself exceeds "
        "\\texttt{T} while no real consecutive pair does."
    ),
    ("P2", "buggy1"): (
        "Because it uses \\texttt{>=}, it moves to every later value equal to the best so "
        "far, so when the largest value occurs more than once it returns the last "
        "position instead of the first. A counter-example needs a tie at the maximum."
    ),
    ("P2", "buggy2"): (
        "\\texttt{best = 0} means a value replaces it only if it is above zero. When every "
        "value is at or below zero, \\texttt{best} never changes and the program returns 1."
    ),
}

FORM_NOTE = {
    ("P1", "buggy1", "direct"): (
        "The requirement the bug violates (\\emph{some} pair, \\emph{ever} changes) is stated "
        "in this form exactly as in the contextualized one."
    ),
    ("P1", "buggy1", "contextualized"): (
        "Nothing about heart rates makes a failing input more or less likely to occur to a "
        "student, and the violated requirement is stated as in the direct form. The "
        "setting only adds reading load."
    ),
    ("P1", "buggy2", "direct"): (
        "Here 0 looks like a natural starting value, and the program is correct on the "
        "small inputs a student is likely to try: on \\texttt{[1, 2, 3]} with $T=5$ it "
        "correctly returns \\texttt{False}."
    ),
    ("P1", "buggy2", "contextualized"): (
        "\\texttt{prev = 0} now reads as a heart rate of 0~bpm before the first reading, a "
        "value that makes no sense for a monitored patient. And any realistic recording "
        "exposes the bug, because a plausible heart rate is far larger than a plausible "
        "threshold."
    ),
    ("P2", "buggy1", "direct"): (
        "The tie rule (smallest position) is stated explicitly, exactly as in the "
        "contextualized form."
    ),
    ("P2", "buggy1", "contextualized"): (
        "The tie rule (earliest date) is stated explicitly, as in the direct form. The "
        "setting may still matter: temperatures to one decimal place make exact ties "
        "seem less likely to a student imagining realistic data."
    ),
    ("P2", "buggy2", "direct"): (
        "With only ``numbers'' to go on, 0 is a natural-looking starting value, and the "
        "program is correct on the positive lists a student is likely to try: on "
        "\\texttt{[3.0, 7.5, 5.0]} it correctly returns 2."
    ),
    ("P2", "buggy2", "contextualized"): (
        "Every realistic January record from Leh is below zero, so any record whose "
        "warmest night is not 1~January exposes the bug. And \\texttt{best = 0} now says "
        "the warmest night so far was 0\\,\\textdegree C, warmer than any night in the "
        "record, a value that can never be beaten."
    ),
}

EXPECTATION = {
    "buggy1": {
        "direct": "Baseline for this bug.",
        "contextualized": "No gain over Direct; possibly lower for less fluent readers. Longer time (more to read).",
    },
    "buggy2": {
        "direct": "Baseline for this bug.",
        "contextualized": "Higher correctness than Direct; longer reading but a shorter search for an input.",
    },
}

VALIDITY_NOTE = {
    "direct": "Inputs must satisfy the specification's own preconditions.",
    "contextualized": ("Inputs must also be \\emph{plausible in the setting}; students are told so, "
                       "and an implausible Step~3 input is rejected with the message below and "
                       "uses up an attempt."),
}


# ---------------------------------------------------------------------------
# document sections
# ---------------------------------------------------------------------------

def overview_table() -> str:
    rows = []
    for p in STUDY_PROBLEMS:
        for bug in ("buggy1", "buggy2"):
            for form in ("direct", "contextualized"):
                key = f"{p['key']}\\_{FORM_NAME[form]}\\_{bug}"
                ce = p["bugs"][bug]["counterexamples"][0]
                rows.append(f"\\texttt{{{key}}} & {FORM_NAME[form]} & {BUG_NAME[bug]} ({BUG_KIND[bug]}) "
                            f"& {code_tt(ce)} \\\\")
    return (
        "\\begin{table}[H]\\centering\\small\n"
        "\\caption{The eight variants, with one counter-example for each bug.}\n"
        "\\label{tab:variants}\n"
        "\\begin{tabularx}{\\textwidth}{@{}l l l X@{}}\\toprule\n"
        "\\textbf{Variant} & \\textbf{Form} & \\textbf{Bug} & \\textbf{Counter-example} \\\\\\midrule\n"
        + "\n".join(rows) +
        "\n\\bottomrule\\end{tabularx}\\end{table}\n"
    )


def condition_table() -> str:
    rows = []
    for i, (f1, b1, f2, b2, order) in enumerate(CONDITIONS):
        rows.append(f"{i} & {FORM_NAME[f1]} & {BUG_NAME[b1]} & {FORM_NAME[f2]} & {BUG_NAME[b2]} "
                    f"& {order[0]} then {order[1]} \\\\")
    return (
        "\\begin{table}[H]\\centering\\small\n"
        "\\caption{Condition rows. Participants at each institute are dealt these rows in "
        "shuffled blocks of eight.}\n\\label{tab:conditions}\n"
        "\\begin{tabular}{@{}r l l l l l@{}}\\toprule\n"
        "\\textbf{Row} & \\textbf{P1 form} & \\textbf{P1 bug} & \\textbf{P2 form} & "
        "\\textbf{P2 bug} & \\textbf{Order} \\\\\\midrule\n"
        + "\n".join(rows) +
        "\n\\bottomrule\\end{tabular}\\end{table}\n"
    )


def io_table(code: str, calls, caption_cols=("Input", "Output")) -> str:
    rows = "\n".join(f"{code_tt(c)} & {code_tt(show(run(code, c)))} \\\\" for c in calls)
    return ("\\begin{tabular}{@{}l l@{}}\\toprule\n"
            f"\\textbf{{{caption_cols[0]}}} & \\textbf{{{caption_cols[1]}}} \\\\\\midrule\n"
            f"{rows}\n\\bottomrule\\end{{tabular}}\n")


def problem_section(p: dict) -> str:
    k = p["key"]
    ref = p["correct_code"]
    out = [f"\\section{{Problem {k}: {PROBLEM_NAME[k]}}}\\label{{sec:{k.lower()}}}\n"]

    out.append("\\subsection{Shared by all four variants}\n")
    out.append(
        "The function signature, the reference solution, and the inputs used in Steps~1 and~2 "
        "are identical in all four variants of this problem. The Step~2 inputs are the same for "
        "both buggy programs, and neither program fails on any of them.\n\n"
    )
    out.append(f"\\paragraph{{Signature.}} {code_tt(p['function_signature'])}\n\n")
    for form, spec in p["forms"].items():
        if spec.get("rename"):
            renamed = ", ".join(f"{code_tt(a)} as {code_tt(b)}" for a, b in spec["rename"].items())
            out.append(f"The {FORM_NAME[form]} form names {renamed}, in the signature, all "
                       "programs and all inputs; nothing else changes.\n\n")
    out.append(listing(ref, "Reference solution (never shown to students)"))
    out.append("\\paragraph{Step 2 tracing inputs.} The control-flow question (how many times each "
               "line runs) uses the first input; the data-flow question (variable values) uses the "
               "second. Reference outputs:\n\n\\smallskip\\noindent")
    out.append(io_table(ref, p["trace_sample_inputs"] + p["trace_data_flow_inputs"]))
    out.append("\n\\paragraph{Step 1 worked examples.} Revealed, with their correct outputs, only "
               "to a student who asks for help after a wrong Step~1 attempt; the student may not "
               "then reuse them as their own pairs:\n\n\\smallskip\\noindent")
    out.append(io_table(ref, p["io_example_inputs"]))
    out.append("\n")

    for bug in ("buggy1", "buggy2"):
        b = p["bugs"][bug]
        for form in ("direct", "contextualized"):
            spec = p["forms"][form]
            name = f"{k}\\_{FORM_NAME[form]}\\_{bug}"
            ce = b["counterexamples"][0]
            out.append(f"\\subsection{{Variant \\texttt{{{name}}}}}\n")
            out.append(f"\\textbf{{Form:}} {FORM_NAME[form]}. \\quad "
                       f"\\textbf{{Bug:}} {BUG_NAME[bug]}, {BUG_KIND[bug]}.\n\n")
            words = len(re.sub(r"`", "", spec["description"]).split())
            out.append(f"\\paragraph{{Specification shown to the student ({words} words).}}\n"
                       f"\\begin{{quote}}\\small {prose(spec['description'])}\\end{{quote}}\n")
            out.append(listing(rename_identifiers(b["code"], spec.get("rename", {})),
                               "Program shown in Steps 2 and 3", b["buggy_line_numbers"]))
            out.append(f"\\paragraph{{The bug.}} {BUG_EXPLANATION[(k, bug)]}\n\n")
            out.append(f"\\paragraph{{Why the form matters.}} {FORM_NOTE[(k, bug, form)]}\n\n")
            out.append(
                f"\\paragraph{{Counter-example.}} {code_tt(ce)}: the task requires "
                f"{code_tt(show(run(ref, ce)))}, the program returns "
                f"{code_tt(show(run(b['code'], ce)))}.\n\n"
            )
            out.append(f"\\paragraph{{Valid Step 3 inputs.}} {VALIDITY_NOTE[form]}\n")
            out.append(listing(spec["input_validator"], "Validity check (server-side)"))
            out.append(f"\\paragraph{{Expected effect.}} {EXPECTATION[bug][form]}\n\n")
    return "".join(out)


DB_FIELDS = [
    # (field, type, seen by student, meaning)
    ("Identity", None, None, None),
    ("id", "integer", "Yes (opaque)", "Database key, assigned on insert."),
    ("title", "text", "Never", "Unique name; for study tasks equal to the variant key. Re-seeding matches existing rows by title, so it never duplicates. Study sessions send the browser a neutral ``Problem 1'' or ``Problem 2'' instead."),
    ("language", "text", "No", "Programming language; always \\texttt{python}."),
    ("Study design", None, None, None),
    ("variant\\_key", "text", "Never", "Which of the eight variants this row is, e.g.\\ \\texttt{P2\\_Contextualized\\_buggy2}. Used by the assignment; null for practice tasks."),
    ("problem\\_key", "text", "Never", "\\texttt{P1} or \\texttt{P2}."),
    ("form", "text", "Yes (Step 3)", "\\texttt{direct} or \\texttt{contextualized}. Sent to the browser only to decide whether to show the ``input must be realistic'' notice."),
    ("bug\\_kind", "text", "Never", "\\texttt{buggy1} (context-independent) or \\texttt{buggy2} (context-sensitive). Analysis only."),
    ("Specification", None, None, None),
    ("description", "text", "Steps 1, 3", "The English specification (the form's text)."),
    ("description\\_mixed", "JSON", "Steps 1, 3", "Code-mixed versions keyed by native-language code (\\texttt{te}, \\texttt{ta}, \\texttt{hi}, \\texttt{gu}, \\texttt{de}). A student receives only their own language; with no entry, no toggle is shown."),
    ("function\\_signature", "text", "Steps 1, 3", "First line of the function. The function name is fixed in the answer boxes, so students type only the arguments."),
    ("Programs", None, None, None),
    ("correct\\_code", "text", "Never", "Reference solution. Step~1 pairs and Step~3 required outputs are checked against it."),
    ("buggy\\_code", "text", "Steps 2, 3", "The faulty program for this variant."),
    ("buggy\\_line\\_numbers", "JSON list", "Never", "Line(s) carrying the bug. Lets the analysis ask whether the student traced the faulty line correctly."),
    ("Step 1", None, None, None),
    ("io\\_example\\_inputs", "JSON list", "After a wrong attempt", "Two calls whose correct outputs are revealed to a student who asks for help; then barred as the student's own pairs."),
    ("Step 2", None, None, None),
    ("trace\\_sample\\_inputs", "JSON list", "Step 2", "Call(s) for the control-flow question (how many times each line runs). Never a counter-example."),
    ("trace\\_data\\_flow\\_inputs", "JSON list", "Step 2", "Different call(s) for the data-flow question (variable values, with the execution order given)."),
    ("trace\\_prefill\\_steps", "integer", "Step 2", "Rows filled in as a worked example (1)."),
    ("trace\\_omit\\_unchanged\\_vars", "boolean", "No", "Whether to drop never-changing variables from the value table (off)."),
    ("mutation\\_line\\_number, mutation\\_new\\_line\\_text, mutation\\_prompt", "int, text, text", "---", "Optional reflection question from the practice tasks. Empty for all study variants."),
    ("Step 3", None, None, None),
    ("input\\_validator", "text (Python)", "Its messages", "Defines \\texttt{valid(...)} with the task's parameters; returns \\texttt{None} for a valid input or the message shown to the student. The contextualized version adds plausibility ranges."),
    ("step3\\_max\\_attempts", "integer", "Yes", f"Attempt limit ({STEP3_MAX_ATTEMPTS}). Set for study tasks only; it also switches Step~3 to the study format (input, required output, program output)."),
]


def db_section(example: dict) -> str:
    rows = []
    for field, typ, seen, meaning in DB_FIELDS:
        if typ is None:
            rows.append(f"\\midrule\\multicolumn{{4}}{{@{{}}l}}{{\\textit{{{field}}}}} \\\\\\addlinespace[2pt]")
        else:
            # Long names like trace_omit_unchanged_vars may break after "_".
            breakable = field.replace("\\_", "\\_\\allowbreak{}")
            rows.append(f"\\texttt{{{breakable}}} & {typ} & {seen} & {meaning} \\\\")
    task_table = (
        "{\\small\n\\begin{longtable}{@{}>{\\raggedright\\arraybackslash}p{3.6cm} "
        ">{\\raggedright\\arraybackslash}p{1.7cm} >{\\raggedright\\arraybackslash}p{2.0cm} "
        ">{\\raggedright\\arraybackslash}X@{}}\n"
    )
    # longtable does not support X columns; use a fixed width instead.
    task_table = task_table.replace("X@{}}", "p{7.3cm}@{}}")
    task_table += (
        "\\caption{Fields of one problem (\\texttt{tasks} table).}\\label{tab:fields}\\\\\n"
        "\\toprule\\textbf{Field} & \\textbf{Type} & \\textbf{Seen by student} & \\textbf{Meaning} \\\\\n"
        "\\endfirsthead\n"
        "\\toprule\\textbf{Field} & \\textbf{Type} & \\textbf{Seen by student} & \\textbf{Meaning} \\\\\n"
        "\\endhead\n\\bottomrule\\endfoot\n"
        + "\n".join(rows) +
        "\n\\end{longtable}\n}\n"
    )

    ex = example
    ex_rows = [
        ("title / variant\\_key", ex["variant_key"]),
        ("problem\\_key", ex["problem_key"]),
        ("form", ex["form"]),
        ("bug\\_kind", ex["bug_kind"]),
        ("function\\_signature", ex["function_signature"]),
        ("buggy\\_line\\_numbers", str(ex["buggy_line_numbers"])),
        ("trace\\_sample\\_inputs", str(ex["trace_sample_inputs"])),
        ("trace\\_data\\_flow\\_inputs", str(ex["trace_data_flow_inputs"])),
        ("io\\_example\\_inputs", str(ex["io_example_inputs"])),
        ("description\\_mixed", "{" + ", ".join(f"{k}: ..." for k in ex["description_mixed"]) + "}"),
        ("step3\\_max\\_attempts", str(ex["step3_max_attempts"])),
        ("mutation\\_*", "null"),
    ]
    example_table = (
        "\\begin{table}[H]\\centering\\small\n"
        f"\\caption{{The stored values of \\texttt{{{esc(ex['variant_key'])}}} (long text fields omitted).}}\n"
        "\\label{tab:example}\n\\begin{tabularx}{\\textwidth}{@{}l X@{}}\\toprule\n"
        "\\textbf{Field} & \\textbf{Value} \\\\\\midrule\n"
        + "\n".join(f"\\texttt{{{f}}} & {code_tt(v)} \\\\" for f, v in ex_rows) +
        "\n\\bottomrule\\end{tabularx}\\end{table}\n"
    )

    related = r"""
\subsection{Related tables}
A problem row is the fixed material. What students do is recorded in four
other tables:

\begin{description}[style=nextline, leftmargin=1.5em]
  \item[\texttt{participants}] One row per student: institute, student ID,
    the questionnaire answers (\texttt{native\_\allowbreak{}language},
    \texttt{schooling\_\allowbreak{}medium}, \texttt{english\_\allowbreak{}proficiency},
    \texttt{mother\_\allowbreak{}language\_\allowbreak{}proficiency},
    \texttt{programming\_\allowbreak{}proficiency},
    \texttt{programming\_\allowbreak{}courses}, \texttt{age}, \texttt{gender}; see
    Section~\ref{sec:questionnaire}), arrival \texttt{slot} at the institute, the
    \texttt{condition\_row} it was dealt, and \texttt{assigned\_task\_ids}
    (the two variants, in presentation order). Institute and student ID are
    unique together, so a returning student resumes rather than being
    re-assigned.
  \item[\texttt{study\_sessions}] One row per student $\times$ problem:
    \texttt{participant\_id}, \texttt{position} (1 or 2), \texttt{task\_id},
    and whether Steps 1--3 are completed.
  \item[\texttt{step\_events}] The timing and answer log: one row each time a
    step is shown and each time it is submitted, with a server timestamp,
    attempt number, correctness, and the full submission in
    \texttt{payload}. Step~1 payloads also record, for analysis only,
    whether each pair would already have refuted the program; Step~3
    payloads record the real outputs and each success condition separately.
  \item[\texttt{spec\_view\_events}] One row for each step's first view of the
    specification (always English) and one per switch between English and
    code-mixed, with a timestamp.
\end{description}
"""
    return ("\\section{Database fields of a problem}\\label{sec:db}\n"
            "Each variant is stored as one row of the \\texttt{tasks} table. "
            "Table~\\ref{tab:fields} explains every field and says whether, and when, a student "
            "sees it; Table~\\ref{tab:example} shows the values stored for one variant. "
            "Fields marked \\emph{Never} are not sent to the browser at all.\n\n"
            + task_table + example_table + related)


def code_mixed_appendix() -> str:
    out = ["\\appendix\n\\section{Code-mixed specifications}\\label{app:mixed}\n",
           "\\textbf{Draft.} These versions must be checked by a native speaker of each language "
           "against the English text before the pilot; an ambiguity introduced in translation "
           "would produce disputed counter-examples. Technical terms, identifiers and code stay "
           "in English; the surrounding prose is in the student's language, written in its own "
           "script (German: German prose with English technical terms).\n\n"]
    for p in STUDY_PROBLEMS:
        for form in ("direct", "contextualized"):
            out.append(f"\\subsection{{{p['key']}, {FORM_NAME[form]} form}}\n")
            for code, lang, script in LANGS:
                text = CODE_MIXED[p["key"]][form].get(code)
                if not text:
                    continue
                font = f"\\{code}font " if script else ""
                out.append(f"\\paragraph{{{lang}.}}\n{{{font}{prose(text)}}}\n\n")
    return "".join(out)


PREAMBLE = r"""%% Generated by docs/build_study_variants.py from backend/seed_study.py and
%% backend/code_mixed.py. Edit those, then regenerate — do not edit by hand.
%% Compile with XeLaTeX (twice): xelatex study_variants.tex
\documentclass[11pt,a4paper]{article}

\usepackage[margin=2.3cm]{geometry}
\usepackage{fontspec}
\usepackage{xcolor}
\usepackage{listings}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{array}
\usepackage{enumitem}
\usepackage{textcomp}
\usepackage{float}
\usepackage[hidelinks]{hyperref}

\setmainfont{Latin Modern Roman}
\setmonofont{Latin Modern Mono}[Scale=0.95]
\newfontfamily\tefont{__INDIC__}[Script=Telugu]
\newfontfamily\tafont{__INDIC__}[Script=Tamil]
\newfontfamily\hifont{__INDIC__}[Script=Devanagari]
\newfontfamily\gufont{__INDIC__}[Script=Gujarati]

\setlength{\emergencystretch}{3em}
\setlength{\parindent}{0pt}
\setlength{\parskip}{4pt}

\definecolor{codebg}{RGB}{247,247,247}
\definecolor{codeframe}{RGB}{210,210,210}
\definecolor{kw}{RGB}{0,70,140}
\lstset{
  language=Python,
  basicstyle=\ttfamily\small,
  keywordstyle=\color{kw}\bfseries,
  numbers=left,
  numberstyle=\tiny\color{gray},
  numbersep=6pt,
  backgroundcolor=\color{codebg},
  frame=single,
  rulecolor=\color{codeframe},
  xleftmargin=1.5em,
  framexleftmargin=1.2em,
  showstringspaces=false,
  columns=fullflexible,
  keepspaces=true,
  breaklines=true,
  aboveskip=6pt,
  belowskip=6pt,
}

\title{Same Code, Different Contexts:\\The Eight Study Variants}
\author{COMPUTE 2026 Working Group on Refute Problem Difficulty}
\date{\today}

\begin{document}
\maketitle

\begin{abstract}
This document lists the eight Refute Problem variants used in the study: two
problems, each written in a direct and a contextualized form and paired with
a context-independent and a context-sensitive bug. For every variant it gives
the specification the student reads, the program they are asked to refute,
why the form of the specification may matter for that bug, a checked
counter-example, and the rule a Step~3 input must satisfy. It closes by
explaining how a problem is stored in the study application's database. All
programs, inputs and outputs are taken from, and computed by, the
application itself.
\end{abstract}

\tableofcontents
\newpage
"""

INTRO = r"""
\section{Design in brief}

Each problem has one reference solution and is written in two forms. The
\emph{direct} form states the computation in computational terms; the
\emph{contextualized} form places the same computation in a real-world
setting. Both forms are fully specified and are solved by the same reference
solution. Each problem is paired with two buggy programs: a
\emph{context-independent} bug (Buggy1), whose failing inputs are no easier to
think of in the setting, and a \emph{context-sensitive} bug (Buggy2), which the
setting may help students find, either by suggesting realistic inputs that
expose it or by giving the faulty code a meaning that looks wrong.
Crossing form with bug gives the eight variants of Table~\ref{tab:variants}.

Each student attempts both problems, one in each form, and sees one of each
problem's two buggy programs. Which form, which program, and which problem
comes first are counterbalanced (Table~\ref{tab:conditions}): any four
consecutive rows show every form--bug combination of each problem once, and
all eight also balance the order.

Within a problem the student works through three steps, with no feedback
between them:
\begin{description}[style=nextline, leftmargin=1.5em]
  \item[Step 1: the task.] The student reads the specification (switching to a
    code-mixed version if they wish) and gives three input--output pairs.
    No code is shown. The pairs must all be correct to continue.
  \item[Step 2: the code.] The student sees the buggy program, without the
    specification, and traces it on inputs we supply. None of these inputs is
    a counter-example.
  \item[Step 3: refutation.] The student sees the specification and the program
    together, with their own Step~1 pairs and Step~2 traces, and gives an input
    on which the program fails, the output the task requires for it, and the
    output the program returns. They have at most three attempts.
\end{description}

\subsection{Participant questionnaire}\label{sec:questionnaire}
Before the first problem, every student answers the following on the start
page. All items are required; the stored value is given in brackets where it
differs from what the student sees.
\begin{enumerate}[leftmargin=2em, itemsep=1pt]
  \item Institute (chosen from a list) and participant / student ID.
  \item Your native language: Telugu, Tamil, Hindi, Gujarati or German
    [\texttt{te}, \texttt{ta}, \texttt{hi}, \texttt{gu}, \texttt{de}]. This
    also chooses the code-mixed version of the specification.
  \item Medium of instruction at school: English / My native language /
    Partly English, partly my native language / Other.
  \item Proficiency in English (1 = novice, 5 = expert).
  \item Proficiency in your mother language (1 = novice, 5 = expert).
  \item Proficiency in computer programming (1 = novice, 5 = expert).
  \item How many computer programming courses have you taken? (a whole
    number, 0--50)
  \item Age (years, 10--100).
  \item Gender: Female / Male / Other / Prefer not to say
    [\texttt{NoResponse}].
\end{enumerate}
A student who returns with the same institute and ID resumes their earlier
session; their first answers are kept.
"""


def main():
    example = None
    for p in STUDY_PROBLEMS:
        from seed_study import make_variants
        for v in make_variants(p):
            if v["variant_key"] == "P2_Contextualized_buggy2":
                example = v
    doc = (PREAMBLE.replace("__INDIC__", INDIC_FONT)
           + INTRO + overview_table() + condition_table() + "\\clearpage\n"
           + "".join(problem_section(p) + "\\clearpage\n" for p in STUDY_PROBLEMS)
           + db_section(example)
           + "\\clearpage\n" + code_mixed_appendix()
           + "\n\\end{document}\n")
    path = os.path.join(HERE, "study_variants.tex")
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    print("wrote", path)


if __name__ == "__main__":
    main()
