from __future__ import annotations

try:
    from .plan_tracker_tab import PlanTrackerTab as _Base
except Exception:
    _Base = object

class PlanTrackerTab(_Base):
    """
    Compat wrapper: accept optional `plan_path` without breaking the base signature.
    If the base exposes set_plan_path(), call it; otherwise stash as attribute.
    """
    def __init__(self, *args, plan_path=None, **kwargs):
        tried = False
        try:
            super().__init__(*args, **kwargs)
            tried = True
        except TypeError:
            # Base likely doesn't accept kwargs; retry with positional-only.
            super().__init__(*args)
            tried = True
        except Exception:
            pass

        if plan_path is not None:
            setter = getattr(self, "set_plan_path", None)
            if callable(setter):
                try: setter(plan_path)
                except Exception: setattr(self, "plan_path", plan_path)
            else:
                try: setattr(self, "plan_path", plan_path)
                except Exception: pass
