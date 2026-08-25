#!/usr/bin/env python3
"""Write activity.json from Strava, for the TRMNL Today screen (IDX_2).

Never writes today.json. If this script fails, the plan and the screen are unaffected.

Env: STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

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


def summarise(act, planned):
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
        entry["detail"] = zone_for(hr) if hr else ""
    elif kind == "strength":
        entry["headline"] = f"Strength {hms(moving)}"
        entry["detail"] = act.get("name", "")
    else:
        entry["headline"] = f"{kind.title()} {hms(moving)}"
        entry["detail"] = ""

    cap = (planned or {}).get("hr_cap")
    expected = EXPECTED.get((planned or {}).get("type"))
    if expected and kind != expected:
        entry["verdict"] = f"Unplanned {kind}. {planned.get('hero','')} still owed."
    elif kind == "run" and cap and hr:
        over = int(round(hr - cap))
        if over <= 0:
            entry["verdict"] = "Held under the cap. Exactly right."
        elif over <= 8:
            entry["verdict"] = f"{over} bpm over the cap. Close enough."
        else:
            entry["verdict"] = f"{over} bpm over the cap. Too hard for an easy day."
    elif kind == "run" and cap and not hr:
        entry["verdict"] = "No heart rate recorded."
    elif planned:
        entry["verdict"] = "Session complete."
    else:
        entry["verdict"] = "Bonus session."
    return entry


def main():
    try:
        token = access_token()
    except Exception as e:
        print("Token refresh failed:", e, file=sys.stderr)
        return 1

    after = int((datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).timestamp())
    acts = api(f"https://www.strava.com/api/v3/athlete/activities?after={after}&per_page=100", token=token)

    plan_days = {}
    try:
        with open(PLAN_FILE) as fh:
            plan_days = {d["date"]: d for d in json.load(fh).get("days", [])}
    except Exception as e:
        print("Plan not readable, continuing without verdicts:", e, file=sys.stderr)

    # One entry per day: the longest activity matching what was planned, else the longest overall
    by_day = {}
    for a in acts:
        if not a.get("start_date_local"):
            continue
        day = a["start_date_local"][:10]
        by_day.setdefault(day, []).append(a)

    entries = []
    for day, day_acts in sorted(by_day.items()):
        planned = plan_days.get(day)
        want = EXPECTED.get((planned or {}).get("type"))
        matching = [a for a in day_acts if KIND.get(a.get("sport_type", "")) == want] if want else []
        chosen = max(matching or day_acts, key=lambda a: a.get("moving_time") or 0)
        entries.append(summarise(chosen, planned))

    out = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "activities": entries,
    }
    with open(OUT_FILE, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print(f"Wrote {len(entries)} day(s) to {OUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
