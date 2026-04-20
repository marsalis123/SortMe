import time
import os
import shutil


def start_watching(folder, config, stop_flag, log):

    log("🔥 WATCHER STARTED")

    watch_root = os.path.abspath(folder)

    # 🧠 NOVÉ: BASE ROOT (kam sa triedi)
    base_root = os.path.dirname(watch_root)

    log(f"📁 WATCH ROOT: {watch_root}")
    log(f"📦 BASE ROOT: {base_root}")

    scan_and_sort(watch_root, base_root, config, log)

    previous = set(os.listdir(watch_root))

    while stop_flag():

        try:
            current = set(os.listdir(watch_root))
            new_files = current - previous

            for file in new_files:

                full_path = os.path.join(watch_root, file)

                if os.path.isdir(full_path):
                    continue

                process_file(file, full_path, base_root, config, log)

            previous = current
            time.sleep(1)

        except Exception as e:
            log(f"❌ ERROR: {e}")

    log("🛑 STOPPED")


# =========================
# INITIAL SCAN
# =========================
def scan_and_sort(watch_root, base_root, config, log):

    log("🚀 INITIAL SCAN...")

    for file in os.listdir(watch_root):

        full = os.path.join(watch_root, file)

        if os.path.isdir(full):
            continue

        process_file(file, full, base_root, config, log)

    log("✅ INITIAL DONE")


# =========================
# RULE ENGINE (FIXED)
# =========================
def process_file(file, full_path, base_root, config, log):

    log(f"📄 Detected: {file}")

    moved = False

    for rule in config.get("rules", []):

        keywords = rule.get("keywords", [])
        rel_path = rule.get("path")

        if any(k.lower() in file.lower() for k in keywords):

            log(f"🧠 Rule match: {rule['name']} → {rel_path}")

            target_dir = os.path.join(base_root, rel_path)
            os.makedirs(target_dir, exist_ok=True)

            target_path = os.path.join(target_dir, file)

            try:
                shutil.move(full_path, target_path)
                log(f"📦 Moved: {file} → {rel_path}")
            except Exception as e:
                log(f"❌ Move error: {file} ({e})")

            moved = True
            break

    # =========================
    # FALLBACK
    # =========================
    if not moved:

        fallback = os.path.join(base_root, "School/Nezaradene")
        os.makedirs(fallback, exist_ok=True)

        target_path = os.path.join(fallback, file)

        try:
            shutil.move(full_path, target_path)
            log(f"⚠️ No rule → Nezaradene: {file}")
        except Exception as e:
            log(f"❌ Fallback error: {file} ({e})")