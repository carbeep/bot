from datetime import datetime, timedelta, timezone
from typing import Any

MSK = timezone(timedelta(hours=3))


def is_zone_active_now(zone: dict[str, Any]) -> bool:
    schedule = zone.get("schedule", "")
    if not schedule:
        return True
    now = datetime.now(MSK)
    parts = {p.split(":")[0]: p.split(":", 1)[1] for p in schedule.split(";") if ":" in p}
    if "days" in parts:
        allowed = [int(d) for d in parts["days"].split(",") if d.isdigit()]
        if now.weekday() not in allowed:
            return False
    if "hours" in parts:
        rng = parts["hours"].split("-")
        if len(rng) == 2:
            try:
                h_s, h_e = int(rng[0]), int(rng[1])
                h = now.hour
                if h_s <= h_e:
                    if not (h_s <= h < h_e):
                        return False
                elif not (h >= h_s or h < h_e):
                    return False
            except ValueError:
                pass
    return True


def is_quiet_hours(user: dict[str, Any]) -> bool:
    qs, qe = user.get("quiet_start", -1), user.get("quiet_end", -1)
    if qs < 0 or qe < 0:
        return False
    h = datetime.now(MSK).hour
    if qs <= qe:
        return qs <= h < qe
    return h >= qs or h < qe
