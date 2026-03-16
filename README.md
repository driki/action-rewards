# action-rewards

**Your automation is guessing.**

You've built a system that takes actions -- deploying code, sending alerts, scaling servers, routing tickets, retrying failed jobs. Some of those actions work. Some don't. But your system doesn't know which is which. It makes the same decisions regardless of outcomes, because nobody closed the loop.

**action-rewards closes the loop.** Record actions, evaluate outcomes, and the system learns which strategies actually work. Bad strategies auto-deactivate. Good ones get reinforced. No ML, no training, no GPU. Just SQLite and arithmetic.

## What it looks like

```
=== Strategy weights for 'deploy' ===
  canary:      82% success, avg reward 0.7, n=44
  blue_green:  71% success, avg reward 0.5, n=17
  direct:      34% success, avg reward -0.1, n=29

Active rules:
  [90%] avoid_friday_deploys: defer_to_monday (23+/2-)
  [75%] canary_for_breaking: extend_canary_window (8+/3-)
```

Your deploy system just learned that direct deploys fail 66% of the time, Friday deploys are cursed, and canary is the right default. It learned this from your own data, not from a blog post.

## The loop

```bash
# 1. Record an action
ar record --type deploy --key v2.4.1 --subtype canary \
    --context '{"day": "tuesday", "changes": 14}'

# 2. Later, record what happened
ar resolve 1 --outcome success --reward 0.9 --detail "Zero errors after 2h"

# 3. Check what's working
ar weights --type deploy

# 4. Before the next action, ask: is there a rule for this?
ar rules --type deploy
```

That's it. Four steps. Record, resolve, check weights, check rules. The system gets smarter every iteration.

## How strategy rules work

Rules are condition-action pairs with confidence scores:

- **Condition:** matches against action context (e.g., `{"day": "friday"}`)
- **Action:** what to do instead (e.g., `"defer_to_monday"`)
- **Confidence:** starts at 0.5, goes up with successes, down with failures
- **Auto-deactivation:** rules that fail more than 85% of the time after 5+ uses get turned off automatically

You can add rules manually or let the system learn them from patterns in the data.

## Not ML

This is not machine learning. There's no model, no training, no inference. It's success-rate tracking with conditional rules -- closer to a thermostat than a neural network. The database is SQLite. The math is division. It runs on a Raspberry Pi.

But it solves the same problem ML solves in the enterprise: "given what we've tried before, what should we try now?" For most automation, counting wins and losses is more useful than a transformer.

## Built for

- **CI/CD pipelines** -- which deploy strategies work for which services?
- **Alert systems** -- which alerts lead to real incidents vs noise?
- **Auto-scaling** -- which scaling decisions actually improved latency?
- **Chatbots** -- which response strategies get positive feedback?
- **Scrapers** -- which retry/backoff strategies succeed?
- **Ops runbooks** -- which remediation steps actually fix the problem?

Anything that takes automated actions and has measurable outcomes.

## Python API

```python
from actionrewards.tracker import Tracker

t = Tracker()

# Record
aid = t.record("deploy", "v2.4.1", subtype="canary",
               context={"region": "us-east", "day": "tuesday"})

# Resolve
t.resolve(aid, "success", reward=0.9, detail="Clean deploy")

# Learn
weights = t.weights("deploy")
# {"canary": {"success_rate": 0.82, "avg_reward": 0.7, "n": 44}}

# Check rules before acting
match = t.match_rule("deploy", {"day": "friday"})
# ("avoid_friday", "defer_to_monday", 0.9)
```

## Install

```bash
pip install action-rewards
```

Or clone and use directly:

```bash
git clone https://github.com/driki/action-rewards.git
cd action-rewards
python cli.py summary
```

Data lives in `~/.action-rewards/actions.db`. Override with `--db`.

## License

MIT
