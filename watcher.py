import os
import time
import shutil


def safe_move(src, dst):
    """
    Ak súbor už existuje, neprerazí ho,
    ale vytvorí unikátny názov.
    """
    if not os.path.exists(dst):
        return dst

    base, ext = os.path.splitext(dst)
    i = 1

    while True:
        new_path = f"{base} ({i}){ext}"
        if not os.path.exists(new_path):
            return new_path
        i += 1


def start_watching(folder, config, stop_flag, log, status_callback, notify_callback):

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

            for file in files:

                full_path = os.path.join(folder, file)

                if os.path.isdir(full_path):
                    continue

                moved = False

                # =========================
                # RULE MATCHING
                # =========================
                for rule in config.get("rules", []):

                    for keyword in rule.get("keywords", []):

                        if keyword.lower() in file.lower():

                            target_dir = os.path.join(base_folder, rule["path"])
                            os.makedirs(target_dir, exist_ok=True)

                            target_path = os.path.join(target_dir, file)
                            target_path = safe_move(full_path, target_path)

                            try:
                                shutil.move(full_path, target_path)

                                msg = f"{file} → {rule['path']}"

                                log(f"📦 MOVED: {msg}")

                                processed_count += 1
                                last_action = msg

                                status["processed_count"] = processed_count
                                status["last_action"] = last_action

                                notify_callback(
                                    "Sorted",
                                    msg,
                                    "success"
                                )

                                push_status()

                            except Exception as e:

                                log(f"❌ MOVE ERROR: {e}")

                                notify_callback(
                                    "Error",
                                    str(e),
                                    "error"
                                )

                            moved = True
                            break

                    if moved:
                        break

                # =========================
                # FALLBACK (NEZARADENE)
                # =========================
                if not moved:

                    fallback_dir = os.path.join(base_folder, "School/Nezaradene")
                    os.makedirs(fallback_dir, exist_ok=True)

                    target_path = os.path.join(fallback_dir, file)
                    target_path = safe_move(full_path, target_path)

                    try:
                        shutil.move(full_path, target_path)

                        msg = f"{file} → Nezaradene"

                        log(f"⚠️ FALLBACK: {msg}")

                        processed_count += 1
                        last_action = msg

                        status["processed_count"] = processed_count
                        status["last_action"] = last_action

                        notify_callback(
                            "Unsorted",
                            msg,
                            "warning"
                        )

                        push_status()

                    except Exception as e:

                        log(f"❌ FALLBACK ERROR: {e}")

                        notify_callback(
                            "Error",
                            str(e),
                            "error"
                        )

            time.sleep(1)

        except Exception as e:
            log(f"❌ WATCHER CRASH: {e}")

            notify_callback(
                "Watcher crash",
                str(e),
                "error"
            )

            time.sleep(2)

    status["running"] = False
    push_status()

    log("🛑 WATCHER STOPPED")