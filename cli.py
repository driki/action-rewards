#!/usr/bin/env python3
"""CLI for action-rewards strategy learner."""
import argparse, json, sys
from actionrewards.tracker import Tracker

def cmd_record(args):
    t = Tracker(db_path=args.db)
    ctx = json.loads(args.context) if args.context else None
    aid = t.record(args.type, args.key, subtype=args.subtype, context=ctx)
    print(f"Recorded action #{aid}: {args.type}/{args.subtype or '-'} key={args.key}")

def cmd_resolve(args):
    t = Tracker(db_path=args.db)
    t.resolve(args.action_id, args.outcome, args.reward, detail=args.detail)
    print(f"Resolved #{args.action_id}: {args.outcome} (reward={args.reward})")

def cmd_weights(args):
    t = Tracker(db_path=args.db)
    w = t.weights(args.type)
    if not w: print(f"No data for '{args.type}' yet."); return
    print(f"=== Strategy weights for '{args.type}' ===")
    for sub, stats in sorted(w.items(), key=lambda x: x[1]["success_rate"], reverse=True):
        print(f"  {sub}: {stats['success_rate']:.0%} success, avg reward {stats['avg_reward']}, n={stats['n']}")

def cmd_rules(args):
    t = Tracker(db_path=args.db)
    rules = t.get_rules(args.type)
    if not rules: print(f"No active rules for '{args.type}'."); return
    for r in rules:
        print(f"  [{r['confidence']:.0%}] {r['name']}: {r['action']} ({r['successes']}+/{r['failures']}-)")

def cmd_summary(args):
    t = Tracker(db_path=args.db)
    s = t.summary()
    print(f"Active rules: {s['active_rules']}")
    for atype, outcomes in s["by_type"].items():
        total = sum(v["count"] for v in outcomes.values())
        print(f"\n  {atype} ({total} actions):")
        for outcome, stats in outcomes.items():
            print(f"    {outcome}: {stats['count']} (avg reward {stats['avg_reward']})")

def main():
    p = argparse.ArgumentParser(prog="ar", description="Action-Rewards Strategy Learner")
    p.add_argument("--db", help="Database path")
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("record"); s.add_argument("--type", required=True); s.add_argument("--key", required=True)
    s.add_argument("--subtype"); s.add_argument("--context"); s.set_defaults(func=cmd_record)

    s = sub.add_parser("resolve"); s.add_argument("action_id", type=int)
    s.add_argument("--outcome", required=True); s.add_argument("--reward", type=float, required=True)
    s.add_argument("--detail"); s.set_defaults(func=cmd_resolve)

    s = sub.add_parser("weights"); s.add_argument("--type", required=True); s.set_defaults(func=cmd_weights)
    s = sub.add_parser("rules"); s.add_argument("--type", required=True); s.set_defaults(func=cmd_rules)
    s = sub.add_parser("summary"); s.set_defaults(func=cmd_summary)

    args = p.parse_args()
    if not args.cmd: p.print_help(); sys.exit(1)
    args.func(args)

if __name__ == "__main__": main()
