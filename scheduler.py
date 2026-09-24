"""
scheduler.py
------------
Simple daily-time scheduler: no cron, no external service. main.py in
"normal mode" calls wait_until_next_run() in a loop, then runs one
quiz cycle each time it returns.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta


def get_next_run_time(hour: int, minute: int, now: datetime | None = None) -> datetime:
    now = now or datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if target <= now:
        target += timedelta(days=1)

    return target


def wait_until_next_run(hour: int, minute: int) -> None:
    target = get_next_run_time(hour, minute)

    print("\n" + "=" * 60)
    print("DAILY SCHEDULER")
    print("=" * 60)
    print(f"Next quiz: {target.strftime('%Y-%m-%d %H:%M:%S')}")

    while True:
        now = datetime.now()
        remaining = (target - now).total_seconds()

        if remaining <= 0:
            print("\nScheduled time reached.")
            return

        if remaining > 60:
            print(f"Waiting... {int(remaining // 60)} minutes remaining.")
            time.sleep(60)
        else:
            time.sleep(min(remaining, 5))
