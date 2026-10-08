import extract
import load
import weather
from analysis import marathon, training_load, weather_impact

STEPS = (
    ("Extract", extract.main),
    ("Load", load.main),
    ("Weather", weather.main),
    ("Marathon prediction", marathon.main),
    ("Training load", training_load.main),
    ("Weather impact", weather_impact.main),
)


def main():
    for name, step in STEPS:
        print(f"\n=== {name} ===")
        step()
    print("\nPipeline complete.")


if __name__ == "__main__":
    main()
