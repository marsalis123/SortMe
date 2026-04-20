import json
from watcher import start_watching
from sorter import process_existing_files

def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

def main():
    config = load_config()

    watch_folder = config["watch_folder"]

    print("SmartSorter started")
    print("Watching:", watch_folder)

    process_existing_files(watch_folder, config)

    start_watching(watch_folder, config)

if __name__ == "__main__":
    main()