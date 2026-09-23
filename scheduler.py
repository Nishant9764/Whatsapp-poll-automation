import time
from datetime import datetime, timedelta


def get_next_run_time(hour, minute):
    now = datetime.now()

    target = now.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0
    )

    # If today's scheduled time has already passed,
    # schedule for tomorrow.
    if target <= now:
        target += timedelta(days=1)

    return target


def wait_until_next_run(hour, minute):
    target = get_next_run_time(hour, minute)

    print("\n" + "=" * 60)
    print("DAILY SCHEDULER")
    print("=" * 60)

    print(f"Next poll: {target.strftime('%Y-%m-%d %H:%M:%S')}")

    while True:
        now = datetime.now()

        remaining = (target - now).total_seconds()

        if remaining <= 0:
            print("\n⏰ Scheduled time reached.")
            return

        # Don't spam the terminal every second.
        # Show an update approximately every minute.
        if remaining > 60:
            print(
                f"Waiting... "
                f"{int(remaining // 60)} minutes remaining."
            )

            time.sleep(60)

        else:
            time.sleep(min(remaining, 5))