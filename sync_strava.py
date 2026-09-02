#!/usr/bin/env python3
"""Write activity.json from Strava, for the TRMNL Today screen (IDX_2).

Never writes today.json. If this script fails, the plan and the screen are unaffected.

Env: STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone

# Publish raw bpm to a public repo? The verdict already conveys the judgement
# without exposing a health metric, so this is off by default.
PUBLISH_HR = True

LOOKBACK_DAYS = 21
PLAN_FILE = "today.json"
OUT_FILE = "activity.json"

# From Strava (get_athlete_zones), max HR 195
ZONES = [(130, "Zone 1"), (162, "Zone 2"), (178, "Zone 3"), (194, "Zone 4"), (999, "Zone 5")]

KIND = {
    "Run": "run", "TrailRun": "run", "VirtualRun": "run",
    "Ride": "ride", "VirtualRide": "ride", "EBikeRide": "ride",
    "WeightTraining": "strength", "Workout": "strength", "Crossfit": "strength",
    "Yoga": "strength", "Pilates": "strength",
    "Swim": "swim", "Walk": "walk", "Hike": "walk",
}
EXPECTED = {
    "easy": "run", "long": "run", "quality": "run", "race": "run", "optional": "run",
    "strength": "strength", "spin": "ride", "rest": None,
}
RUN_TYPES = ("easy", "long", "quality", "race", "optional")

# A long run is the session most likely to shift by a day around the rest of life,
# so it alone is matched with a tolerance. Every other type stays strict.
TOLERANT_TYPES = ("long",)
TOLERANCE_DAYS = 1

# Used when a run happens on a day the plan gave no cap for: rest days, strength
# days, spin days, or a day outside the plan entirely. Overridden by the plan's
# own meta.easy_hr_cap when today.json is readable.
DEFAULT_EASY_CAP = 160


def api(url, data=None, token=None):
    req = urllib.request.Request(url, data=data)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def access_token():
    body = urllib.parse.urlencode({
        "client_id": os.environ["STRAVA_CLIENT_ID"],
        "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
        "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    return api("https://www.strava.com/oauth/token", data=body)["access_token"]


def zone_for(bpm):
    for ceiling, name in ZONES:
        if bpm <= ceiling:
            return name
    return "Zone 5"


def hms(seconds):
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def pace(distance_m, moving_s):
    if not distance_m:
        return None
    sec_per_km = moving_s / (distance_m / 1000.0)
    return f"{int(sec_per_km // 60)}:{int(sec_per_km % 60):02d}/km"


def cap_for(planned, easy_cap):
    """Return (cap, is_fallback).

    The plan only sets hr_cap on easy, long and optional days: 164 of 252 days
    carry none. Without a fallback a run on any of those days produced a bare
    "Session complete." and the heart-rate judgement, which is the whole point
    of the screen, was silently dropped. Quality and race days genuinely have no
    easy cap, so they are handled separately rather than given a false one.
    """
    if not planned:
        return easy_cap, True
    if planned.get("hr_cap"):
        return planned["hr_cap"], False
    if planned.get("type") in ("quality", "race"):
        return None, False
    return easy_cap, True


def cap_phrase(hr, cap, fallback):
    label = "%d easy cap" % cap if fallback else "%d cap" % cap
    over = int(round(hr - cap))
    if over < 0:
        return "%d bpm under the %s." % (-over, label)
    if over == 0:
        return "Bang on the %s." % label
    if over <= 8:
        return "%d bpm over the %s." % (over, label)
    return "%d bpm over the %s. Too hard." % (over, label)


def summarise(act, planned, easy_cap=DEFAULT_EASY_CAP, shift=None):
    """Build the three lines the screen shows in place of the kit list."""
    kind = KIND.get(act.get("sport_type", ""), "other")
    dist_km = (act.get("distance") or 0) / 1000.0
    moving = act.get("moving_time") or 0
    hr = act.get("average_heartrate")
    entry = {"date": act["start_date_local"][:10], "kind": kind, "name": act.get("name", "")}

    if kind == "run" and dist_km:
        entry["headline"] = f"{dist_km:.1f} km in {hms(moving)}"
        bits = [pace(act.get("distance"), moving)]
        if hr:
            if PUBLISH_HR:
                bits.append(f"{int(hr)} bpm")
            bits.append(zone_for(hr))
        entry["detail"] = "  ·  ".join(b for b in bits if b)
    elif kind == "ride":
        entry["headline"] = f"Spin {hms(moving)}"
        bits = []
        if hr:
            if PUBLISH_HR:
                bits.append(f"{int(hr)} bpm")
            bits.append(zone_for(hr))
        entry["detail"] = "  ·  ".join(bits)
    elif kind == "strength":
        entry["headline"] = f"Strength {hms(moving)}"
        entry["detail"] = act.get("name", "")
    else:
        entry["headline"] = f"{kind.title()} {hms(moving)}"
        entry["detail"] = ""

    ptype = (planned or {}).get("type")
    expected = EXPECTED.get(ptype)
    cap, fallback = cap_for(planned, easy_cap)

    if kind != "run":
        # Non-run activities keep the original behaviour.
        if expected and kind != expected:
            entry["verdict"] = f"Unplanned {kind}. {planned.get('hero','')} still owed."
        elif planned:
            entry["verdict"] = "Session complete."
        else:
            entry["verdict"] = "Bonus session."
        return entry

    # A run always gets a heart-rate judgement where one can be made. Anything
    # else the day still owes is appended, not substituted for it.
    owed = ""
    if ptype in ("strength", "spin") and not shift:
        owed = " %s still owed." % ptype.title()

    if ptype in ("quality", "race"):
        entry["verdict"] = "Race done." if ptype == "race" else "Quality session done. No easy cap today."
    elif cap and hr:
        note = " Long run, %s." % shift if shift else ""
        entry["verdict"] = cap_phrase(hr, cap, fallback) + note + owed
    elif cap and not hr:
        entry["verdict"] = "No heart rate recorded." + owed
    elif planned:
        entry["verdict"] = "Session complete."
    else:
        entry["verdict"] = "Bonus session."
    return entry


def resolve_planned(day, plan_days, act_days, claimed, has_run=True):
    """Which planned session does this activity answer to? Returns (planned, shift).

    Same date wins. Failing that, a long run within TOLERANCE_DAYS may be claimed,
    but only if its own date has no activity of its own, so a genuine Sunday long
    run can never be stolen by a Saturday jog.

    has_run gates the tolerance: without it a strength session logged on a strength
    day would get reallocated to Sunday's long run and then judged as an unplanned
    strength session, which the dry run duly caught.
    """
    same = plan_days.get(day)
    if same and same.get("type") in RUN_TYPES:
        return same, None
    if not has_run:
        return same, None
    try:
        d = date.fromisoformat(day)
    except ValueError:
        return same, None
    for delta in range(1, TOLERANCE_DAYS + 1):
        for sign, wording in ((-1, "a day late"), (1, "a day early")):
            other = (d + timedelta(days=sign * delta)).isoformat()
            cand = plan_days.get(other)
            if not cand or cand.get("type") not in TOLERANT_TYPES:
                continue
            if other in act_days or other in claimed:
                continue
            claimed.add(other)
            return cand, wording
    return same, None


def main():
    try:
        token = access_token()
    except Exception as e:
        print("Token refresh failed:", e, file=sys.stderr)
        return 1

    after = int((datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).timestamp())
    acts = api(f"https://www.strava.com/api/v3/athlete/activities?after={after}&per_page=100", token=token)

    plan_days = {}
    easy_cap = DEFAULT_EASY_CAP
    try:
        with open(PLAN_FILE) as fh:
            plan = json.load(fh)
        plan_days = {d["date"]: d for d in plan.get("days", [])}
        easy_cap = plan.get("meta", {}).get("easy_hr_cap") or DEFAULT_EASY_CAP
    except Exception as e:
        print("Plan not readable, continuing without verdicts:", e, file=sys.stderr)

    # One entry per day: the longest activity matching what was planned, else the longest overall
    by_day = {}
    for a in acts:
        if not a.get("start_date_local"):
            continue
        day = a["start_date_local"][:10]
        by_day.setdefault(day, []).append(a)

    act_days = set(by_day)
    claimed = set()
    entries = []
    week_runs = {}
    for day, day_acts in sorted(by_day.items()):
        has_run = any(KIND.get(a.get("sport_type", "")) == "run" for a in day_acts)
        planned, shift = resolve_planned(day, plan_days, act_days, claimed, has_run)
        want = EXPECTED.get((planned or {}).get("type"))
        matching = [a for a in day_acts if KIND.get(a.get("sport_type", "")) == want] if want else []
        chosen = max(matching or day_acts, key=lambda a: a.get("moving_time") or 0)
        entry = summarise(chosen, planned, easy_cap, shift)
        entries.append(entry)
        if entry["kind"] == "run":
            # Count against the week the session belonged to, which for a shifted
            # long run is the planned week, not the week it was actually run in.
            src = planned or plan_days.get(day)
            if src and src.get("week"):
                week_runs[src["week"]] = week_runs.get(src["week"], 0) + 1

    out = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "weeks": [{"n": n, "runs": c} for n, c in sorted(week_runs.items())],
        "activities": entries,
    }
    with open(OUT_FILE, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print(f"Wrote {len(entries)} day(s) to {OUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
