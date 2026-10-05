"""Guard inputs. Adapter mode receives raw calls and selected read-only rows.

Rows are selected by argument values across every table, without a tool-specific
ownership resolver. The candidate must interpret tool schemas and record fields.
These are synthetic fixture records, never provider keys or evaluator cases.
"""

from copy import deepcopy

from patchloop.runtime.policy import MUTATION_TOOLS, guard_context


def data_view(db, arguments):
    values = set()

    def visit(value):
        if isinstance(value, str):
            values.add(value)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, dict):
            for child in value.values():
                visit(child)

    visit(arguments)
    return {table: {key: deepcopy(rows[key]) for key in values if key in rows}
            for table, rows in db.items()}


def guard_input(guard, db, user_id, name, arguments, *, confirmed=True):
    if getattr(guard, "interface", "fixed") == "fixed":
        return guard_context(db, user_id, name, arguments)
    # Consent exists only for a consequential change. Reads, lookups and catalog calls never
    # carry it, in validation or in live sessions; otherwise a guard that gates every call
    # on consent passes validation and then blocks reads and logins in real conversations.
    return {"tool": name, "arguments": deepcopy(arguments),
            "authenticated_user_id": user_id,
            "confirmation": {"matches_action": bool(confirmed) and name in MUTATION_TOOLS},
            "data": data_view(db, arguments)}
