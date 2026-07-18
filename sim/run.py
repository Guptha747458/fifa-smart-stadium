"""CLI entrypoint to run the simulator standalone."""
import sys
from sim.simulator import run_forever

if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    run_forever(seed=seed, interval=interval)
