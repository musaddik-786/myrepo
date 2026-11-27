"""Change requirement document for a permanent fix: fixed schema, exported as JSON and Markdown."""
FIELDS = ["title", "problem", "root_cause", "evidence", "acceptance_criteria", "impacted_modules",
          "test_scenarios", "risk", "linked_tickets", "source_ticket", "source_card"]
LISTS = {"evidence", "acceptance_criteria", "impacted_modules", "test_scenarios", "linked_tickets"}


def validate(doc: dict) -> dict:
    """Return the doc normalised to the schema, or raise ValueError listing what is missing."""
    missing = [f for f in FIELDS if not doc.get(f)]
    if missing:
        raise ValueError("Requirement document missing: " + ", ".join(missing))
    out = {}
    for f in FIELDS:
        v = doc[f]
        out[f] = [str(x) for x in v] if f in LISTS and isinstance(v, list) else (
            [str(v)] if f in LISTS else str(v))
    return out


def to_markdown(doc: dict) -> str:
    d = validate(doc)
    def bullets(k): return "\n".join(f"- {x}" for x in d[k])
    return (f"# Change requirement: {d['title']}\n\n"
            f"Source ticket: {d['source_ticket']} | Knowledge card: {d['source_card']}\n\n"
            f"## Problem\n{d['problem']}\n\n## Root cause\n{d['root_cause']}\n\n"
            f"## Evidence\n{bullets('evidence')}\n\n## Acceptance criteria\n{bullets('acceptance_criteria')}\n\n"
            f"## Impacted modules\n{bullets('impacted_modules')}\n\n## Test scenarios\n{bullets('test_scenarios')}\n\n"
            f"## Risk\n{d['risk']}\n\n## Linked tickets\n{bullets('linked_tickets')}\n")
