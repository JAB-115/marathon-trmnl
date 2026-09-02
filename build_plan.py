#!/usr/bin/env python3
"""Build today.json for the TRMNL 'Today' screen from the 36-week plan.

Design rule: precompute anything date-derived here, so the Liquid template
does one lookup and no arithmetic. A plan revision changes data only.
"""
import json, datetime as dt

D = dt.date
def d(s): return D.fromisoformat(s)

RACE = d("2027-04-25")
W1 = d("2026-08-17")

CHECKPOINTS = [
    {"date": "2026-10-10", "short": "parkrun",  "name": "parkrun 5K time trial", "target": "27:00-28:00"},
    {"date": "2026-12-19", "short": "10K TT",   "name": "10K time trial",        "target": "54-57 min"},
    {"date": "2027-03-14", "short": "RSL half", "name": "Run South London Half", "target": "sub 1:58"},
    {"date": "2027-04-25", "short": "RACE DAY", "name": "London Marathon",       "target": "sub 4:00"},
]

PHASES = [
    {"id": "rebuild",  "name": "Rebuild",        "start": "2026-08-17", "end": "2026-10-25", "weeks": [1, 10]},
    {"id": "half",     "name": "Half build",     "start": "2026-10-26", "end": "2027-01-03", "weeks": [11, 20]},
    {"id": "marathon", "name": "Marathon block", "start": "2027-01-04", "end": "2027-04-25", "weeks": [21, 36]},
]

# Footer prose overrides only. Session counts are NOT declared here any more:
# they are derived from the emitted days further down, so they cannot drift.
DEMAND_PROSE = {
    4:  "holiday, walk lots",
    36: "taper, then race",
}

# Sessions: week -> list of (weekday 0=Mon, type, kit_class, hero, detail, km)
# type: easy | quality | long | race | strength | spin | rest | optional
S = {
 1:  [(1,"easy","easy","Easy 4km","Gentle restart",4),
      (3,"easy","easy","Easy 5km","",5),
      (6,"long","easy","Long 7km easy","",7)],
 2:  [(1,"easy","easy","Easy 5km","",5),
      (2,"easy","easy","Easy 4km","Away from Thursday",4)],
 3:  [(2,"easy","easy","Easy 5km","Back from Tuesday",5),
      (4,"easy","easy","Easy 4km + 4 strides","",4),
      (6,"long","easy","Long 8km easy","",8)],
 4:  [],
 5:  [(3,"easy","easy","Easy 4km","Back Wednesday",4),
      (5,"easy","easy","Easy 5km + 4 strides","",5),
      (6,"long","easy","Long 8km relaxed","",8)],
 6:  [(1,"easy","easy","Easy 6km + 6 strides","",6),
      (3,"easy","easy","Easy 6km","",6),
      (6,"long","easy","Long 10km easy","",10)],
 7:  [(1,"quality","quality","Fartlek 8 x 1 min brisk / 1 min jog","",8),
      (3,"easy","easy","Easy 6km","",6),
      (6,"long","easy","Long 11km easy","",11)],
 8:  [(1,"quality","quality","Fartlek 6 x 90 sec / 90 sec","",7),
      (3,"easy","easy","Easy 5km","",5),
      (5,"race","quality","parkrun 5K time trial","",5),
      (6,"long","easy","Long 8km relaxed","",8)],
 9:  [(1,"quality","quality","Threshold 3 x 5 min, 2 min jog","Recalculate paces from parkrun",8),
      (3,"easy","easy","Easy 7km","",7),
      (6,"long","easy","Long 12km easy","",12)],
 10: [(1,"quality","quality","Threshold 4 x 5 min, 2 min jog","",9),
      (3,"easy","easy","Easy 7km","",7),
      (6,"long","easy","Long 13km easy","",13)],
 11: [(1,"quality","quality","Threshold 20 min continuous","",8),
      (2,"easy","easy","Easy 6km","Away from Friday",6)],
 12: [(3,"easy","easy","Easy 6km","Back Wednesday",6),
      (4,"easy","easy","Easy 5km + 4 strides","",5),
      (6,"long","easy","Long 13km easy","",13)],
 13: [(1,"quality","quality","Threshold 3 x 8 min, 2 min jog","",9),
      (3,"easy","easy","Easy 7km","",7),
      (5,"optional","easy","Optional easy 5km","Only if the body feels good",5),
      (6,"long","easy","Long 14km easy","",14)],
 14: [(1,"quality","quality","Threshold 25 min continuous","",9),
      (3,"easy","easy","Easy 8km","",8),
      (5,"optional","easy","Optional easy 5km","",5),
      (6,"long","easy","Long 15km easy","",15)],
 15: [(1,"quality","quality","5 x 1km at 5K effort, 2.5 min jog","",10),
      (3,"easy","easy","Easy 8km","",8),
      (5,"optional","easy","Optional easy 5km","",5),
      (6,"long","easy","Long 16km, last 3km steady","",16)],
 16: [(1,"quality","quality","Threshold 2 x 12 min","",9),
      (3,"easy","easy","Easy 7km","",7),
      (6,"long","easy","Long 11km cutback","",11)],
 17: [(1,"quality","quality","Threshold 30 min continuous","",10),
      (3,"easy","easy","Easy 8km","",8),
      (5,"optional","easy","Optional easy 5km","",5),
      (6,"long","easy","Long 17km easy","",17)],
 18: [(1,"quality","quality","4 x 3 min at 5K effort","",8),
      (3,"easy","easy","Easy 5km + 4 strides","",5),
      (5,"race","quality","10K time trial or festive 10K","",10)],
 19: [(1,"easy","easy","Easy 7km relaxed","Away from Wednesday",7)],
 20: [(1,"easy","easy","Easy 6km","",6),
      (3,"easy","easy","Easy 7km + 4 strides","",7),
      (6,"long","easy","Long 14km easy","",14)],
 21: [(1,"quality","quality","Threshold 3 x 10 min","",10),
      (3,"easy","easy","Easy 7km + 4 strides","",7),
      (5,"optional","easy","Optional easy 5km","",5),
      (6,"long","easy","Long 17km easy","",17)],
 22: [(1,"quality","quality","6 x 1km at 5K effort","",11),
      (3,"easy","easy","Easy 8km","",8),
      (5,"optional","easy","Optional easy 5km","",5),
      (6,"long","easy","Long 19km easy","",19)],
 23: [(1,"quality","quality","Threshold 30 min continuous","",10),
      (3,"easy","easy","Easy 8km","",8),
      (5,"optional","easy","Optional easy 5km","",5),
      (6,"long","easy","Long 21km, last 3km at MP","",21)],
 24: [(1,"quality","quality","5 x 4 min at 5K effort","",9),
      (3,"easy","easy","Easy 8km","",8),
      (5,"optional","easy","Optional easy 5km","",5),
      (6,"long","easy","Long 15km cutback","",15)],
 25: [(1,"quality","quality","Threshold 2 x 15 min","",10),
      (3,"easy","easy","Easy 8km","",8),
      (5,"optional","easy","Optional easy 5km","",5),
      (6,"long","easy","Long 23km easy","",23)],
 26: [(1,"quality","quality","Steady 40 min","",8),
      (3,"easy","easy","Easy 8km","",8),
      (5,"optional","easy","Optional easy 5km","",5),
      (6,"long","easy","Long 17km with 5km at MP","",17)],
 27: [(1,"quality","quality","Threshold 3 x 10 min","",10),
      (3,"easy","easy","Easy 8km + 4 strides","",8),
      (5,"optional","easy","Optional easy 5km","",5),
      (6,"long","easy","Long 25km easy","",25)],
 28: [(1,"quality","quality","30 min at marathon pace","",9),
      (3,"easy","easy","Easy 8km","",8),
      (5,"optional","easy","Optional easy 5km","",5),
      (6,"long","easy","Long 27km easy","",27)],
 29: [(1,"quality","quality","4 x 2 min at 5K effort","",6),
      (3,"easy","easy","Easy 5km + 4 strides","",5),
      (6,"long","easy","Long 12km relaxed","",12)],
 30: [(1,"quality","quality","20 min with 10 min at MP","",6),
      (3,"easy","easy","Easy 5km + 4 strides","",5),
      (6,"race","quality","RACE: Run South London Half","Checkpoint 3. Sets your marathon goal",21)],
 31: [(1,"easy","easy","Recovery 8km very easy","Nothing hard before Thursday",8),
      (3,"easy","easy","Easy 8km","",8),
      (5,"optional","easy","Optional easy 5km","",5),
      (6,"long","easy","Long 26km relaxed","",26)],
 32: [(1,"quality","quality","2 x 20 min at marathon pace","",10),
      (3,"easy","easy","Easy 8km","",8),
      (5,"optional","easy","Optional easy 5km","",5),
      (6,"long","quality","Long 30-32km or 3:30, whichever first","Dress rehearsal: kit, breakfast, gels",31)],
 33: [(1,"quality","quality","30 min at marathon pace","",9),
      (3,"easy","easy","Easy 8km","",8),
      (5,"optional","easy","Optional easy 5km","",5),
      (6,"long","quality","Long 24km with 10km at MP","Last big one. Strength to maintenance",24)],
 34: [(1,"quality","quality","3 x 8 min at marathon pace","Taper begins",9),
      (3,"easy","easy","Easy 7km + 4 strides","",7),
      (6,"long","easy","Long 18km easy","",18)],
 35: [(1,"quality","quality","2 x 10 min at marathon pace","",8),
      (3,"easy","easy","Easy 6km + 4 strides","",6),
      (6,"long","quality","Long 13km with 3km at MP","",13)],
 36: [(1,"quality","quality","Easy 6km with 4 x 1 min at MP","",6),
      (3,"easy","easy","Easy 5km + 4 strides","",5),
      (4,"easy","easy","Shakeout 20 min jog","Lay out kit, pin number, sort gels",3),
      (6,"race","quality","RACE DAY: London Marathon","",42)],
}

# Non-run defaults by weekday
NONRUN = {
    0: ("rest",     "Rest · or yoga, reformer or recovery class", ""),
    2: ("strength", "Strength · gym session or Tempo class",      "Glutes & Legs or Conditioning fine midweek"),
    4: ("spin",     "Indoor cycling · easy to moderate",          ""),
    5: ("strength", "Strength · Tempo class",                     "Core & Upper is safest before a long run"),
}

RACE_SHOE_DATES = {"2027-03-14", "2027-03-28", "2027-04-04", "2027-04-18", "2027-04-25"}

def run_hour(day, dow, stype):
    ds = day.isoformat()
    if stype == "race":
        return (9, "09:00") if ds != "2027-04-25" else (10, "10:00")
    if dow == 6:
        return (9, "09:30")
    if dow == 5:
        return (11, "11:00")
    if stype == "quality" and d("2026-10-25") <= day <= d("2027-03-27"):
        return (12, "12:30")
    return (18, "18:00")

def shoe(day, dow, stype):
    ds = day.isoformat()
    if ds in RACE_SHOE_DATES:
        return "race_shoe"
    if stype == "long":
        return "triumph_23"
    if stype == "optional":
        return "triumph_20"
    if "Recovery" in ds:
        return "triumph_20"
    return "novablast_5"

def pace_for(stype, hero):
    h = hero.lower()
    if "race day" in h:            return "MP 5:55/km \u00b7 Zone 3 \u00b7 first 10km must feel easy"
    if "run south london" in h:    return "Target sub 1:58 \u00b7 5:35/km \u00b7 Zone 3-4"
    if "parkrun" in h:             return "Target 27:00-28:00 \u00b7 Zone 4"
    if "time trial" in h:          return "Target 54-57 min \u00b7 Zone 4"
    if "shakeout" in h:            return "8:00/km \u00b7 Zone 1-2 \u00b7 loosen up only"
    if "recovery" in h:            return "7:30-8:00/km \u00b7 Zone 1-2"
    if "at mp" in h or "marathon pace" in h:
        if stype == "long":        return "7:00-7:45/km Zone 2, MP segment 5:55/km Zone 3"
        if stype == "easy":        return "7:15-8:00/km Zone 2, MP bursts 5:55/km"
        return "5:55/km (MP) \u00b7 Zone 3 low"
    if "threshold" in h:           return "6:15-6:30/km \u00b7 Zone 3 top"
    if "5k effort" in h:           return "5:55-6:10/km \u00b7 Zone 4"
    if "fartlek" in h:             return "Brisk 6:00/km, jog 7:30/km"
    if "steady" in h:
        if stype == "long":        return "7:00-7:45/km Zone 2, close 6:30-6:45/km"
        return "6:30-6:45/km \u00b7 Zone 3 low"
    if stype == "long":            return "7:00-7:45/km \u00b7 Zone 2"
    return "7:15-8:00/km \u00b7 Zone 2"


MINS_PER_KM = {"easy": 7.6, "long": 7.4, "quality": 6.6, "optional": 7.8, "race": 5.7}


def hr_cap_for(stype, hero):
    """Cap the Strava sync compares against. None = no cap (quality/race)."""
    h = hero.lower()
    if "recovery" in h or "shakeout" in h: return 150
    if stype == "long":  return 162
    if stype in ("easy", "optional"): return 160
    return None


def phase_for(day):
    for p in PHASES:
        if d(p["start"]) <= day <= d(p["end"]):
            return p["id"]
    return PHASES[0]["id"]

def next_cp(day):
    for c in CHECKPOINTS:
        cd = d(c["date"])
        if cd >= day:
            return c["short"], (cd - day).days
    return "", 0

days = []
for w in range(1, 37):
    monday = W1 + dt.timedelta(days=(w - 1) * 7)
    planned = {s[0]: s for s in S[w]}
    for dow in range(7):
        day = monday + dt.timedelta(days=dow)
        cp_short, cp_days = next_cp(day)
        rec = {"date": day.isoformat(), "week": w}
        if dow in planned:
            _, stype, kit, hero, detail, km = planned[dow]
            h, disp = run_hour(day, dow, stype)
            mins = int(round(km * MINS_PER_KM.get(stype, 7.4)))
            rec.update({"type": stype, "kit": kit, "hero": hero, "km": km,
                        "mins": mins, "pace": pace_for(stype, hero),
                        "hr_cap": hr_cap_for(stype, hero),
                        "hour": h, "at": disp, "shoe": shoe(day, dow, stype)})
            if w >= 21 and mins >= 90:
                gels = 1 + max(0, (mins - 30) // 40)
                rec["fuel"] = gels
                rec["fuel_label"] = "Gel x%d" % gels
            if detail:
                rec["note"] = detail
        elif w == 4:
            rec.update({"type": "rest", "hero": "Holiday · walk lots, jog only if it appeals"})
        elif day.isoformat() == "2027-04-24":
            rec.update({"type": "rest", "hero": "Busy today, which is fine",
                        "note": "Off your feet, sip water, eat carbs, early dinner"})
        else:
            t, hero, detail = NONRUN.get(dow, ("rest", "Rest day", ""))
            rec.update({"type": t, "hero": hero})
            if detail:
                rec["note"] = detail
        rec["cp"] = cp_short
        rec["cpd"] = cp_days
        days.append(rec)

RUN_TYPES = ("easy", "long", "quality", "race", "optional")

def demand_string(w, runs, strength):
    """Prose for the footer fallback. Special-cased weeks keep their own wording;
    everything else is generated from the counts so it cannot contradict them."""
    if w in DEMAND_PROSE:
        return DEMAND_PROSE[w]
    if runs == 0 and strength == 0:
        return "rest week"
    s = "%d run%s" % (runs, "" if runs == 1 else "s")
    if strength:
        s += " + %d strength" % strength
    return s

weeks = []
for w in range(1, 37):
    monday = W1 + dt.timedelta(days=(w - 1) * 7)
    wd = [d for d in days if d["week"] == w]
    # Counts are DERIVED from the sessions actually emitted above. The old DEMAND
    # table asserted them separately and had drifted on 30 of 36 weeks, which would
    # have made the "run N of M" footer print things like "run 3 of 2".
    runs     = sum(1 for d in wd if d["type"] in RUN_TYPES)
    strength = sum(1 for d in wd if d["type"] == "strength")
    spin     = sum(1 for d in wd if d["type"] == "spin")
    weeks.append({"n": w, "start": monday.isoformat(), "phase": phase_for(monday),
                  "runs": runs, "strength": strength, "spin": spin,
                  "demand": demand_string(w, runs, strength)})

kit = {
  "defaults": {
    "easy":    {"top": "Tee", "bottom": "2-in-1 shorts", "acc": "Cushioned socks"},
    "quality": {"top": "Tee", "bottom": "Half tights",   "acc": "Everyday socks"}
  },
  "bands": [
    {"id": "raw",       "max": 2,  "label": "Raw"},
    {"id": "cold",      "max": 6,  "label": "Cold"},
    {"id": "damp_cold", "max": 10, "label": "Damp cold"},
    {"id": "mild",      "max": 15, "label": "Mild"},
    {"id": "warm",      "max": 20, "label": "Warm"},
    {"id": "hot",       "max": 99, "label": "Hot"}
  ],
  "deltas": [
    {"band":"raw","kit":"easy","top":"Thermal base + windproof jacket","bottom":"Thermal tights","acc":"Beanie, buff, thermal gloves, warm socks"},
    {"band":"raw","kit":"quality","top":"Thermal base + gilet","bottom":"Full tights","acc":"Headband, buff, thermal gloves"},
    {"band":"cold","kit":"easy","top":"Long-sleeve + windproof jacket","bottom":"Full tights","acc":"Beanie or headband, light gloves, warm socks"},
    {"band":"cold","kit":"quality","top":"Long-sleeve base","bottom":"Full tights","acc":"Headband, light gloves"},
    {"band":"damp_cold","kit":"easy","top":"Long-sleeve","bottom":"Full tights","acc":"Light gloves"},
    {"band":"damp_cold","kit":"quality","top":"Tee, deliberately underdressed","bottom":"Half tights","acc":"Light gloves, headband"},
    {"band":"mild","kit":"easy","top":"Tee","bottom":"2-in-1 shorts","acc":"Cushioned socks"},
    {"band":"mild","kit":"quality","top":"Tee","bottom":"Half tights","acc":"Everyday socks"},
    {"band":"warm","kit":"easy","top":"Tee","bottom":"2-in-1 shorts","acc":"Cap, sunglasses"},
    {"band":"warm","kit":"quality","top":"Mesh tee","bottom":"Half tights","acc":"Cap, sunglasses"},
    {"band":"hot","kit":"easy","top":"Mesh tee","bottom":"2-in-1 shorts","acc":"Cap, sunglasses, anti-chafe balm"},
    {"band":"hot","kit":"quality","top":"Mesh tee","bottom":"2-in-1 shorts","acc":"Cap, sunglasses, anti-chafe balm"}
  ],
  "modifiers": {
    "light_rain":    {"acc": "cap"},
    "heavy_rain":    {"top": "waterproof jacket", "acc": "cap"},
    "wind":          {"top": "windproof"},
    "fog":           {"acc": "reflective vest"},
    "any_rain_long": {"acc": "anti-chafe balm"},
    "ice":   "Trail shoes or move indoors",
    "fluid": "Fluid",
    "dark":  "Hi-Vis"
  }
}

shoes = [
  {"id":"novablast_5","name":"Novablast 5","short":"Novablast","km":146,"retire":625,"role":"Daily + threshold","target":0.40},
  {"id":"triumph_23","name":"Triumph 23","short":"Triumph 23","km":149,"retire":625,"role":"Long run","target":0.35},
  {"id":"triumph_20","name":"Triumph 20","short":"Triumph 20","km":536,"retire":625,"role":"Recovery / wet","target":0.20},
  {"id":"race_shoe","name":"TBC","short":"Race shoe","km":0,"retire":250,"role":"Race, buy early Feb","target":0.05},
  {"id":"parkclaw_g280","name":"Parkclaw G280","short":"Trail","km":0,"retire":625,"role":"Ice / wet ground","target":0.00}
]

payload = {
  "meta": {"version": "3.0", "generated": dt.date.today().isoformat(),
           "race": {"name": "London Marathon", "date": RACE.isoformat()},
           "mp_provisional": "5:55/km", "easy_hr_cap": 160},
  "phases": PHASES, "checkpoints": CHECKPOINTS,
  "completed": [], "weeks": weeks, "days": days, "kit": kit, "shoes": shoes
}

out = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
open("/home/claude/plan/today.json", "w").write(out)
pretty = json.dumps(payload, ensure_ascii=False, indent=2)
open("/home/claude/plan/today.pretty.json", "w").write(pretty)
print("days:", len(days))
print("minified bytes:", len(out.encode()), "=", round(len(out.encode())/1024, 1), "kB")
print("pretty bytes:", len(pretty.encode()), "=", round(len(pretty.encode())/1024, 1), "kB")
