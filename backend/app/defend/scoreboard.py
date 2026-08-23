"""
Persistent scoreboard for the adversarial evolution loop. Every call to
adversarial.evolve() that reaches round 2 (i.e. round 1 was actually
caught, so there was something to evade) gets recorded here -- whether
it came from the Simulate tab's "Evolve this attack" button, the Metrics
page's "Robustness" section, or the Arena's battle mode. One shared
scoreboard, three entry points, since it's all the same underlying event.

In-memory, like the live feed -- resets on server restart, which is fine
for a demo tool and avoids adding a database dependency.
"""
import threading
from collections import defaultdict
from datetime import datetime, timezone

_lock = threading.Lock()
_battles: list[dict] = []


def record(attack_id: str, display_name: str, tier: str, evaded: bool, score_delta: float, mutation_description: str):
    with _lock:
        _battles.append({
            "attack_id": attack_id,
            "display_name": display_name,
            "tier": tier,
            "evaded": evaded,
            "score_delta": score_delta,
            "mutation_description": mutation_description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


def summary() -> dict:
    with _lock:
        battles = list(_battles)

    total = len(battles)
    red_wins = sum(1 for b in battles if b["evaded"])
    blue_wins = total - red_wins

    by_attack = defaultdict(lambda: {"battles": 0, "red_wins": 0, "display_name": "", "tier": ""})
    for b in battles:
        entry = by_attack[b["attack_id"]]
        entry["battles"] += 1
        entry["red_wins"] += 1 if b["evaded"] else 0
        entry["display_name"] = b["display_name"]
        entry["tier"] = b["tier"]

    leaderboard = []
    for attack_id, stats in by_attack.items():
        blue_win_rate = 1 - (stats["red_wins"] / stats["battles"]) if stats["battles"] else 0
        leaderboard.append({
            "attack_id": attack_id,
            "display_name": stats["display_name"],
            "tier": stats["tier"],
            "battles": stats["battles"],
            "red_wins": stats["red_wins"],
            "blue_wins": stats["battles"] - stats["red_wins"],
            "blue_win_rate": round(blue_win_rate, 3),
        })
    # Toughest specialists first (highest blue win rate), min 1 battle to qualify
    leaderboard.sort(key=lambda x: (-x["blue_win_rate"], -x["battles"]))

    return {
        "total_battles": total,
        "red_wins": red_wins,
        "blue_wins": blue_wins,
        "blue_win_rate": round(blue_wins / total, 3) if total else None,
        "leaderboard": leaderboard,
        "recent_battles": list(reversed(battles))[:20],
    }


def reset():
    with _lock:
        _battles.clear()
