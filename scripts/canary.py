"""
Skrypt canary: pre-flight dry-run check przed produkcją.
"""
import argparse
import os
import subprocess
import sys

sys.path.append(".")
from utils.slack_client import post_message


def main():
    """Wykonuje canary dry-run i raportuje na Slack."""
    ap = argparse.ArgumentParser(description="Canary pre-flight check")
    ap.add_argument("--config", default="configs/example_mom12_1.yaml", help="Config YAML")
    ap.add_argument("--channel", default=os.environ.get("SLACK_CHANNEL", "#alpha-lab"), help="Kanał Slack")
    args = ap.parse_args()

    print(f"🐦 Canary: uruchamiam dry-run z configiem {args.config}")

    env = dict(os.environ)
    env["DRY_RUN"] = "1"

    ret = subprocess.run(
        [sys.executable, "backtests/report_daily.py", "--config", args.config, "--dry-run"],
        env=env
    )

    if ret.returncode == 0:
        print("✓ Canary PASSED")
        try:
            post_message(args.channel, ":white_check_mark: Canary OK (dry-run)")
        except Exception as e:
            print(f"Nie udało się wysłać na Slack: {e}")
        sys.exit(0)
    else:
        print(f"❌ Canary FAILED (exit code: {ret.returncode})")
        try:
            post_message(args.channel, f":rotating_light: Canary FAIL rc={ret.returncode}")
        except Exception as e:
            print(f"Nie udało się wysłać na Slack: {e}")
        sys.exit(ret.returncode)


if __name__ == "__main__":
    main()
