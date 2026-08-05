import json

import dukpy

# js2py cannot be used: it rewrites CPython bytecode and breaks on 3.12+.
# dukpy embeds Duktape (ES5.1 plus some ES6) and ships wheels for every
# platform we run on, so no compiler is needed to install it.


def evaljs(script: str, **variables):
    """Run javascript and return the result as a native Python value.

    Accepts either an expression ("2 + 2") or a function body
    ("var a = 2; return a + 2"). Keyword arguments are exposed to the script
    through dukpy's `dukpy` object, e.g. `dukpy['name']`.

    Raises dukpy.JSRuntimeError for syntax and runtime errors. Note that
    execution cannot be interrupted: a script that loops forever hangs the
    caller, so only run scripts you trust.
    """
    try:
        return dukpy.evaljs(script, **variables)
    except dukpy.JSRuntimeError as e:
        if "return not in a function" not in str(e):
            raise
    # retry as a function body so scripts may use `return`
    return dukpy.evaljs(f"(function(){{{script}\n}})()", **variables)


def runjs(script: str, **variables) -> str:
    """Run javascript and return the result as a string.

    Strings come back as-is; everything else is rendered as JSON, so numbers
    give "4", booleans "true", and null/undefined "null".
    """
    result = evaljs(script, **variables)
    return result if isinstance(result, str) else json.dumps(result)
