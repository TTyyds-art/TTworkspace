import json
import hashlib
import logging
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
import time
import requests
import sys
import ssl
import certifi

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except Exception:
    tk = None
    ttk = None
    messagebox = None

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "launcher_config.json"
LOG_PATH = BASE_DIR / "launcher.log"


def setup_logging() -> None:
    logging.basicConfig(
        filename=str(LOG_PATH),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


class LauncherUI:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled and tk is not None
        self.root = None
        self.label = None
        self.progress = None
        if self.enabled:
            self.root = tk.Tk()
            self.root.title("更新中")
            self.root.resizable(False, False)
            self.label = tk.Label(self.root, text="准备中...")
            self.label.pack(padx=16, pady=8)
            self.progress = ttk.Progressbar(self.root, length=260, mode="determinate")
            self.progress.pack(padx=16, pady=(0, 12))
            self.root.update()

    def set_status(self, text: str) -> None:
        logging.info(text)
        if self.enabled and self.label:
            self.label.config(text=text)
            self.root.update()

    def set_progress(self, value: int) -> None:
        if self.enabled and self.progress:
            self.progress["value"] = max(0, min(100, value))
            self.root.update()

    def set_indeterminate(self) -> None:
        if self.enabled and self.progress:
            self.progress.configure(mode="indeterminate")
            self.progress.start(10)
            self.root.update()

    def set_determinate(self) -> None:
        if self.enabled and self.progress:
            self.progress.stop()
            self.progress.configure(mode="determinate")
            self.root.update()

    def alert(self, title: str, message: str) -> None:
        if self.enabled and messagebox:
            messagebox.showinfo(title, message)

    def close(self) -> None:
        if self.enabled and self.root:
            self.root.destroy()


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_config_path() -> Path:
    if CONFIG_PATH.exists():
        return CONFIG_PATH
    parent_path = BASE_DIR.parent / "launcher_config.json"
    if parent_path.exists():
        return parent_path
    return CONFIG_PATH


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_paths(config: dict):
    app_dir = BASE_DIR / config["app_dir"]
    temp_dir = BASE_DIR / config["temp_dir"]
    backup_dir = BASE_DIR / config["backup_dir"]
    app_exe = app_dir / config["app_exe"]
    version_file = app_dir / "version.json"
    return app_dir, temp_dir, backup_dir, app_exe, version_file


def get_local_version(version_file: Path) -> str:
    if not version_file.exists():
        return "0.0.0"
    return load_json(version_file).get("version", "0.0.0")


def fetch_manifest(url: str) -> dict:
    logging.info("TLS ca_bundle=%s", certifi.where())
    logging.info("TLS version=%s", ssl.OPENSSL_VERSION)
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()


def parse_version(v: str):
    return tuple(int(x) for x in v.split("."))


def has_new(local: str, remote: str) -> bool:
    return parse_version(remote) > parse_version(local)


def download(url: str, path: Path, on_progress=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.info("download_url=%s", url)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        downloaded = 0
        with open(path, "wb") as f:
            for c in r.iter_content(8192):
                f.write(c)
                downloaded += len(c)
                if on_progress and total:
                    on_progress(int(downloaded * 100 / total))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(8192), b""):
            h.update(c)
    return h.hexdigest()


def backup(app_dir: Path, backup_dir: Path, version: str) -> Path:
    dst = backup_dir / f"app_{version}"
    if dst.exists():
        shutil.rmtree(dst)
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(app_dir, dst)
    return dst


def extract(zip_path: Path, target: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(target)


def launch(exe: Path) -> None:
    subprocess.Popen([str(exe)], cwd=str(exe.parent))


def restore(app_dir: Path, backup_path: Path) -> None:
    if app_dir.exists():
        shutil.rmtree(app_dir)
    shutil.copytree(backup_path, app_dir)


def is_app_running(exe_name: str) -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return exe_name.lower() in result.stdout.lower()
    except Exception as e:
        logging.warning("检测进程失败: %s", e)
        return False


def kill_app(exe_name: str) -> None:
    try:
        subprocess.run(["taskkill", "/F", "/IM", exe_name], check=False)
    except Exception as e:
        logging.warning("结束进程失败: %s", e)


def wait_for_exit(exe_name: str, timeout: int, ui: LauncherUI) -> bool:
    start = time.time()
    while is_app_running(exe_name):
        if timeout and time.time() - start > timeout:
            return False
        ui.set_status("请关闭正在运行的程序...")
        time.sleep(1)
    return True


def get_or_create_client_id(state_path: Path) -> str:
    if state_path.exists():
        state = load_json(state_path)
        if state.get("client_id"):
            return state["client_id"]

    client_id = hashlib.sha256(str(Path.cwd()).encode("utf-8")).hexdigest()
    save_json(state_path, {"client_id": client_id})
    return client_id


def percentile(client_id: str, key: str) -> int:
    h = hashlib.sha256(f"{client_id}:{key}".encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 100


def in_time_window(rollout: dict) -> bool:
    start = rollout.get("start")
    end = rollout.get("end")
    now = datetime.now().astimezone()
    if start:
        if now < datetime.fromisoformat(start):
            return False
    if end:
        if now > datetime.fromisoformat(end):
            return False
    return True


def pick_release(manifest: dict, channel: str, client_id: str) -> dict:
    channels = manifest.get("channels", {})
    rollouts = manifest.get("rollout", {})
    base = channels.get(channel)

    rollout = rollouts.get(channel)
    if rollout and in_time_window(rollout):
        pct = int(rollout.get("percentage", 0))
        if percentile(client_id, f"{channel}:{rollout.get('version', '')}") < pct:
            return {
                "version": rollout["version"],
                "download_url": rollout["download_url"],
                "sha256": rollout["sha256"],
            }

    if base:
        return {
            "version": base["version"],
            "download_url": base["download_url"],
            "sha256": base["sha256"],
        }

    return {
        "version": manifest["latest_version"],
        "download_url": manifest["download_url"],
        "sha256": manifest["sha256"],
    }


def main() -> None:
    setup_logging()
    ui = LauncherUI(enabled=False)
    force_update = False
    try:
        config = load_json(resolve_config_path())
        ui = LauncherUI(enabled=config.get("show_gui", False))
        app_dir, temp_dir, backup_dir, app_exe, version_file = get_paths(config)
        state_path = BASE_DIR / config.get("state_file", "client_state.json")
        channel = config.get("channel", "stable")
        auto_kill = config.get("auto_kill", False)
        wait_timeout = int(config.get("wait_close_timeout", 0))

        local_v = get_local_version(version_file)
        manifest = fetch_manifest(config["manifest_url"])

        client_id = get_or_create_client_id(state_path)
        release = pick_release(manifest, channel, client_id)
        remote_v = release["version"]

        min_supported = manifest.get("min_supported_version", "0.0.0")
        force_update = manifest.get("force_update", False)

        if not has_new(local_v, remote_v):
            launch(app_exe)
            return

        if parse_version(local_v) < parse_version(min_supported):
            force_update = True

        if is_app_running(app_exe.name):
            if auto_kill:
                ui.set_status("正在关闭运行中的程序...")
                kill_app(app_exe.name)
            if not wait_for_exit(app_exe.name, wait_timeout, ui):
                raise Exception("等待程序关闭超时")

        zip_path = temp_dir / f"app_{remote_v}.zip"
        ui.set_status("正在下载更新包...")
        ui.set_determinate()
        download(release["download_url"], zip_path, on_progress=ui.set_progress)

        if sha256(zip_path) != release["sha256"]:
            raise Exception("sha256 mismatch")

        ui.set_status("正在备份当前版本...")
        backup_path = backup(app_dir, backup_dir, local_v)

        shutil.rmtree(app_dir)
        app_dir.mkdir()

        ui.set_status("正在解压新版本...")
        ui.set_indeterminate()
        extract(zip_path, app_dir)
        ui.set_determinate()

        ui.set_status("启动新版本...")
        launch(app_dir / config["app_exe"])
        ui.close()

    except Exception as e:
        logging.exception("更新失败")
        ui.set_status(f"更新失败: {e}")
        if "backup_path" in locals():
            restore(app_dir, backup_path)
            if not force_update:
                launch(app_dir / config["app_exe"])
            else:
                ui.alert("更新失败", "必须更新后才能继续使用，请重试。")
        ui.close()


if __name__ == "__main__":
    main()
