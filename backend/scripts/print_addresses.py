"""Print every agent's address WITHOUT starting it, so you can paste them into .env.

  cd backend/fetch.ai && python ../scripts/print_addresses.py
The address comes from the seed: same seed = same address, forever.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fetch.ai"))
from uagents.crypto import Identity  # noqa: E402

from common.config import SEEDS  # noqa: E402

for key, seed in SEEDS.items():
    if not seed or "CHANGE-ME" in seed:
        print(f"ADDR_{key.upper()}=   # set SEED_{key.upper()} first")
        continue
    print(f"ADDR_{key.upper()}={Identity.from_seed(seed, 0).address}")
