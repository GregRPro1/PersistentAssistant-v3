"""
Legacy harvest utility stub.
Selectively import vetted modules from legacy/ after tests pass.
"""
def import_legacy_module(name: str):
    # Stub: ensure only whitelisted names allowed in real impl.
    if not name.startswith("legacy_"):
        raise ValueError("Module not whitelisted")
    return f"[legacy-stub:{name}]"
