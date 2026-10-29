import re

INJURY_REPLY = (
    "I can't advise on pain or injuries. Please check with a doctor or physiotherapist before training that area."
)
MEDICAL_REPLY = (
    "That's a medical question, so I'll leave it to a doctor or pharmacist. I can still log meals and plan workouts."
)
EATING_REPLY = (
    "I'm not the right help for that. Please talk to a doctor or another qualified professional you trust."
)
GENERAL_REPLY = "That's outside what I can help with. A doctor or other qualified professional is the right person to ask."

# Checked in order; disordered eating first so it is never answered as a plain medical question.
PATTERNS = [
    (
        EATING_REPLY,
        r"eating disorder|anorexi\w*|bulimi\w*|binge[ -]?eat\w*|binged|purg(e|ed|ing)|laxatives?"
        r"|making myself (sick|throw up)|throw(ing)? up after",
    ),
    (
        INJURY_REPLY,
        r"injur\w*|pain(s|ful)?|hurts?|hurting|sprain\w*|strain(ed)? (my|a)|fractur\w*|torn|tendon\w*"
        r"|broke (my|a)|dislocat\w*|swollen",
    ),
    (
        MEDICAL_REPLY,
        r"ill|illness|sick|fever|flu|covid|infection|medication\w*|medicine|meds|pills?|insulin|prescri\w*"
        r"|pregnan\w*|breastfeed\w*|diabet\w*|blood pressure|heart condition|surgery|dizz\w*|faint\w*"
        r"|chest pain|vomit\w*",
    ),
]

COMPILED = [(reply, re.compile(rf"\b(?:{pattern})\b", re.IGNORECASE)) for reply, pattern in PATTERNS]


def check(message: str) -> str | None:
    for reply, pattern in COMPILED:
        if pattern.search(message):
            return reply
    return None
