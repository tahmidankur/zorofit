"""Pick a small, hand-checked set of exercises from yuhonas/free-exercise-db.

Usage: python scripts/curate_exercises.py [raw exercises.json] [out exercises.json]
Download the source from
https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json into data/raw/.
"""

import json
import sys
from pathlib import Path

# (source name, pattern, equipment needed, seconds of work per set)
# Equipment uses the app's own names; an empty list means bodyweight only.
CURATED = [
    # squat
    ("Bodyweight Squat", "squat", [], 40),
    ("Freehand Jump Squat", "squat", [], 30),
    ("Goblet Squat", "squat", ["kettlebell"], 45),
    ("Dumbbell Squat", "squat", ["dumbbells"], 45),
    ("Barbell Squat", "squat", ["barbell", "rack"], 50),
    ("Front Barbell Squat", "squat", ["barbell", "rack"], 50),
    ("Leg Press", "squat", ["machines"], 45),
    # hinge
    ("Single Leg Glute Bridge", "hinge", [], 40),
    ("Barbell Deadlift", "hinge", ["barbell"], 50),
    ("Romanian Deadlift", "hinge", ["barbell"], 50),
    ("Stiff-Legged Dumbbell Deadlift", "hinge", ["dumbbells"], 45),
    ("One-Arm Kettlebell Swings", "hinge", ["kettlebell"], 40),
    ("Barbell Hip Thrust", "hinge", ["barbell", "bench"], 45),
    ("Band Good Morning", "hinge", ["bands"], 40),
    ("Cable Deadlifts", "hinge", ["cable"], 45),
    # lunge
    ("Bodyweight Walking Lunge", "lunge", [], 45),
    ("Step-up with Knee Raise", "lunge", [], 45),
    ("Dumbbell Lunges", "lunge", ["dumbbells"], 50),
    ("Dumbbell Rear Lunge", "lunge", ["dumbbells"], 50),
    ("Split Squat with Dumbbells", "lunge", ["dumbbells"], 50),
    ("Dumbbell Step Ups", "lunge", ["dumbbells", "bench"], 50),
    ("Barbell Lunge", "lunge", ["barbell", "rack"], 55),
    # push_horizontal
    ("Pushups", "push_horizontal", [], 35),
    ("Incline Push-Up", "push_horizontal", [], 35),
    ("Decline Push-Up", "push_horizontal", ["bench"], 35),
    ("Dumbbell Bench Press", "push_horizontal", ["dumbbells", "bench"], 45),
    ("Barbell Bench Press - Medium Grip", "push_horizontal", ["barbell", "bench", "rack"], 45),
    ("Barbell Incline Bench Press - Medium Grip", "push_horizontal", ["barbell", "bench", "rack"], 45),
    ("Cable Chest Press", "push_horizontal", ["cable"], 40),
    ("Machine Bench Press", "push_horizontal", ["machines"], 40),
    ("Alternating Floor Press", "push_horizontal", ["kettlebell"], 45),
    # push_vertical
    ("Handstand Push-Ups", "push_vertical", [], 30),
    ("Standing Dumbbell Press", "push_vertical", ["dumbbells"], 40),
    ("Arnold Dumbbell Press", "push_vertical", ["dumbbells"], 45),
    ("Barbell Shoulder Press", "push_vertical", ["barbell", "rack"], 45),
    ("Alternating Kettlebell Press", "push_vertical", ["kettlebell"], 45),
    ("Cable Shoulder Press", "push_vertical", ["cable"], 40),
    ("Machine Shoulder (Military) Press", "push_vertical", ["machines"], 40),
    # pull_horizontal
    ("Inverted Row", "pull_horizontal", ["pull_up_bar"], 40),
    ("Bent Over Two-Dumbbell Row", "pull_horizontal", ["dumbbells"], 45),
    ("One-Arm Dumbbell Row", "pull_horizontal", ["dumbbells", "bench"], 50),
    ("Bent Over Barbell Row", "pull_horizontal", ["barbell"], 45),
    ("Seated Cable Rows", "pull_horizontal", ["cable"], 40),
    ("Alternating Kettlebell Row", "pull_horizontal", ["kettlebell"], 45),
    ("Band Pull Apart", "pull_horizontal", ["bands"], 35),
    ("Face Pull", "pull_horizontal", ["cable"], 40),
    # pull_vertical
    ("Pullups", "pull_vertical", ["pull_up_bar"], 35),
    ("Chin-Up", "pull_vertical", ["pull_up_bar"], 35),
    ("Band Assisted Pull-Up", "pull_vertical", ["pull_up_bar", "bands"], 40),
    ("Wide-Grip Lat Pulldown", "pull_vertical", ["cable"], 40),
    ("Close-Grip Front Lat Pulldown", "pull_vertical", ["cable"], 40),
    # core
    ("Plank", "core", [], 45),
    ("Dead Bug", "core", [], 40),
    ("Reverse Crunch", "core", [], 35),
    ("Mountain Climbers", "core", [], 30),
    ("Hanging Leg Raise", "core", ["pull_up_bar"], 35),
    ("Pallof Press", "core", ["cable"], 40),
    ("Cable Crunch", "core", ["cable"], 35),
    # carry
    ("Farmer's Walk", "carry", ["dumbbells"], 45),
]

PATTERNS = {"squat", "hinge", "lunge", "push_horizontal", "push_vertical", "pull_horizontal", "pull_vertical", "core", "carry"}


def curate(source: list[dict]) -> list[dict]:
    by_name = {exercise["name"]: exercise for exercise in source}
    missing = [name for name, *_ in CURATED if name not in by_name]
    if missing:
        raise SystemExit(f"Not in free-exercise-db: {missing}")
    curated = []
    for name, pattern, equipment, seconds_per_set in CURATED:
        assert pattern in PATTERNS, pattern
        exercise = by_name[name]
        curated.append(
            {
                "id": exercise["id"],
                "name": exercise["name"],
                "pattern": pattern,
                "equipment": equipment,
                "seconds_per_set": seconds_per_set,
                "level": exercise["level"],
                "primary_muscles": exercise["primaryMuscles"],
                "instructions": exercise["instructions"][:3],
            }
        )
    return curated


if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent.parent / "data"
    source_path = Path(sys.argv[1]) if len(sys.argv) > 1 else data_dir / "raw" / "exercises.json"
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else data_dir / "exercises.json"
    exercises = curate(json.loads(source_path.read_text()))
    out_path.write_text(json.dumps(exercises, indent=2) + "\n")
    print(f"wrote {len(exercises)} exercises to {out_path}")
