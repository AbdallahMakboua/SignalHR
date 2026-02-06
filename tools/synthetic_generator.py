#!/usr/bin/env python3
"""Deterministic synthetic event generator for SignalHR demo.

Usage examples:
  python tools/synthetic_generator.py --profile alice --rate 1 --duration 0.01
  python tools/synthetic_generator.py --profile all --dry-run

This generator is seeded so runs are deterministic for the hackathon demo.
"""
import argparse
import json
import random
import sys
from datetime import datetime, timedelta
from uuid import uuid4

SEED = 20260207
random.seed(SEED)

PROFILES = {
    "alice": {"role": "engineer", "pattern": {"meetings": (6, 2), "messages": (40, 5), "prs": (1, 1)}},
    "ben": {"role": "engineer", "pattern": {"meetings": (2, 1), "messages": (10, 3), "prs": (5, 2)}},
    "carol": {"role": "engineer", "pattern": {"meetings": (3, 1), "messages": (15, 4), "prs": (2, 1)}},
}

FIXED_USERS = {
    "alice": str(uuid4()),
    "ben": str(uuid4()),
    "carol": str(uuid4()),
}


def deterministic_count(base, variance):
    return max(0, int(random.gauss(base, variance)))


def make_event(profile_name, day_ts):
    profile = PROFILES[profile_name]
    pattern = profile["pattern"]
    event = {
        "ingestionId": str(uuid4()),
        "schemaVersion": 1,
        "userId": FIXED_USERS[profile_name],
        "timestamp": day_ts.isoformat() + "Z",
        "signals": {k: deterministic_count(v[0], v[1]) for k, v in pattern.items()},
        "source": "synthetic_generator",
        "profile": profile_name,
    }
    return event


def generate(profile, rate_per_min, duration_hours, dry_run=False):
    now = datetime.utcnow()
    end = now + timedelta(hours=duration_hours)
    interval = 60.0 / max(1, rate_per_min)
    ts = now
    out = []
    while ts < end:
        ev = make_event(profile, ts)
        out.append(ev)
        if not dry_run:
            print(json.dumps(ev))
            sys.stdout.flush()
        ts += timedelta(seconds=interval)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["alice", "ben", "carol", "all"], default="all")
    parser.add_argument("--rate", type=int, default=60, help="events per minute")
    parser.add_argument("--duration", type=float, default=0.1, help="hours to run (can be fractional)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    profiles = [args.profile] if args.profile != "all" else ["alice", "ben", "carol"]
    for p in profiles:
        generate(p, args.rate, args.duration, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
