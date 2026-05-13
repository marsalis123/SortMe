import os
import time
import shutil


def safe_move(src, dst):
    if not os.path.exists(dst):
        return dst

    base, ext = os.path.splitext(dst)
    i = 1

    while True:
        new_path = f"{base} ({i}){ext}"
        if not os.path.exists(new_path):
            return new_path
        i += 1


def start_watching(folder, config, stop_flag, log, status_callback, notify_callback, history_callback):

    log("🔥 WATCHER STARTED")

    folder = os.path.abspath(folder)
    base_folder = os.path.dirname(folder)

    log(f"📁 Watching: {folder}")

    processed_count = 0
    last_action = "None"

    status = {
        "running": True,
        "folder": folder,
        "processed_count": 0,
        "last_action": ""
    }

    def push_status():
        status_callback(status)

    push_status()

    while stop_flag():

        try:
            files = os.listdir(folder)

            # =========================
            # SAFE RULES READ
            # =========================
            rules = config.get("rules", [])

            if not isinstance(rules, list):
                log("❌ Invalid rules format in config")
                rules = []

            for file in files:

                try:

                    # =========================
                    # IGNORE TEMP FILES
                    # =========================
                    ignored_extensions = (
                        ".tmp",
                        ".crdownload",
                        ".part"
                    )

                    ignored_prefixes = (
                        "~$",
                    )

                    lower_file = file.lower()

                    if lower_file.endswith(ignored_extensions):
                        continue

                    if file.startswith(ignored_prefixes):
                        continue

                    full_path = os.path.join(folder, file)

                    # =========================
                    # FILE MAY DISAPPEAR
                    # =========================
                    if not os.path.exists(full_path):
                        continue

                    if os.path.isdir(full_path):
                        continue

                    moved = False

                    # =========================
                    # RULE MATCHING
                    # =========================
                    for rule in rules:

                        # =========================
                        # SAFE RULE TYPE
                        # =========================
                        if not isinstance(rule, dict):
                            log(f"❌ Invalid rule format: {rule}")
                            continue

                        # =========================
                        # SAFE PATH READ
                        # =========================
                        path = rule.get("path")

                        if not isinstance(path, str) or not path.strip():
                            log(f"❌ Skipping rule without valid path: {rule}")
                            continue

                        path = os.path.normpath(path)

                        # =========================
                        # SAFE KEYWORDS READ
                        # =========================
                        keywords = rule.get("keywords", [])

                        if isinstance(keywords, str):
                            keywords = [k.strip() for k in keywords.split(",")]

                        if not isinstance(keywords, list):
                            log(f"❌ Invalid keywords in rule: {rule}")
                            continue

                        # =========================
                        # KEYWORD MATCH
                        # =========================
                        for keyword in keywords:

                            if not isinstance(keyword, str):
                                continue

                            if keyword.lower() in file.lower():

                                target_dir = path

                                try:

                                    if not os.path.exists(target_dir):
                                        os.makedirs(target_dir)

                                    target_path = os.path.join(target_dir, file)
                                    target_path = safe_move(full_path, target_path)

                                    shutil.move(full_path, target_path)

                                    msg = f"{file} → {rule.get('name', 'Unnamed Rule')}"

                                    log(f"📦 MOVED: {msg}")

                                    history_callback(file, target_path)

                                    processed_count += 1
                                    last_action = msg

                                    status["processed_count"] = processed_count
                                    status["last_action"] = last_action

                                    notify_callback("Sorted", msg, "success")

                                    push_status()

                                except Exception as e:

                                    log(f"❌ MOVE ERROR: {e}")
                                    notify_callback("Error", str(e), "error")

                                moved = True
                                break

                        if moved:
                            break

                    # =========================
                    # FALLBACK
                    # =========================
                    if not moved:

                        fallback_dir = os.path.join(base_folder, "School/Nezaradene")

                        try:
                            os.makedirs(fallback_dir, exist_ok=True)

                            target_path = os.path.join(fallback_dir, file)
                            target_path = safe_move(full_path, target_path)

                            shutil.move(full_path, target_path)

                            msg = f"{file} → Nezaradene"

                            log(f"⚠️ FALLBACK: {msg}")

                            history_callback(file, target_path)

                            processed_count += 1
                            last_action = msg

                            status["processed_count"] = processed_count
                            status["last_action"] = last_action

                            notify_callback("Unsorted", msg, "warning")

                            push_status()

                        except Exception as e:

                            log(f"❌ FALLBACK ERROR: {e}")
                            notify_callback("Error", str(e), "error")

                except Exception as e:

                    log(f"❌ FILE PROCESS ERROR ({file}): {e}")

            time.sleep(1)

        except Exception as e:

            log(f"❌ WATCHER CRASH: {e}")
            notify_callback("Watcher crash", str(e), "error")

            time.sleep(2)

    status["running"] = False
    push_status()

    log("🛑 WATCHER STOPPED")