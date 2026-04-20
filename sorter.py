import os
import shutil
import time
from ai_classifier import classify


def process_file(file_path, config):

    wait_until_ready(file_path)

    filename = os.path.basename(file_path)

    rules = config["rules"]
    

    for rule in rules:

        for keyword in rule["keywords"]:

            if keyword.lower() in filename.lower():

                destination = rule["destination"]

                move_file(file_path, destination)

                print("Matched rule:", rule["name"])

                return

    # ak nič nenašlo
    if config["ai_enabled"]:
        label = classify(file_path)

        if label:
            print("AI classified as:", label)

    else:
        print("No rule matched")

        unknown = config["unknown_folder"]

        move_file(file_path, unknown)

        log(f"Unknown file moved to fallback: {file_path}")


def move_file(file_path, destination):

    os.makedirs(destination, exist_ok=True)

    filename = os.path.basename(file_path)

    target = os.path.join(destination, filename)

    shutil.move(file_path, target)

    print("Moved to:", target)
    log(f"Moved {file_path} -> {target}")

def process_existing_files(folder, config):

    for file in os.listdir(folder):

        file_path = os.path.join(folder, file)

        if os.path.isfile(file_path):
            print("Processing existing file:", file_path)
            process_file(file_path, config)

def wait_until_ready(file_path):

    while True:
        try:
            with open(file_path, "rb"):
                return
        except PermissionError:
            time.sleep(0.5)

def log(message):

    with open("sorter_log.txt", "a", encoding="utf-8") as f:
        f.write(message + "\n")
      