import argparse
import json
import os
from pyrosm import get_data


def main(place):
    file_path = os.path.join("data", "OpenStreetMap")

    fp = get_data(place, directory=file_path, update=True)

    print(json.dumps(fp))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument("--place", type=str, required=True, help="Your name")

    args = parser.parse_args()
    main(args.place)
