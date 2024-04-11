import sys
from pathlib import Path


def save_file(paths: list, index: int):
    with open(f"listphp{index:04}.txt", "w") as file:
        for path in paths:
            file.write(f"{path}\n")


if __name__ == "__main__":
    files = Path(sys.argv[1]).resolve().rglob("*.php")
    temp = []
    count = 1

    for path in files:
        if path.is_file():
            temp.append(path)

        if len(temp) == 100:
            save_file(temp, count)
            temp = []
            count += 1

    if len(temp) > 0:
        save_file(temp, count)
