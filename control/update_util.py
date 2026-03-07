# control/update_util.py
import os, sys, re, json, hashlib, tempfile, subprocess, time, urllib.request, ssl,ctypes,shutil

# ↓↓↓ 只改这两行为你的地址（优先用 JSON）
REMOTE_MANIFEST_JSON = "http://download.xiliu.store/latest.json"
REMOTE_MANIFEST_TXT  = "http://download.xiliu.store/latest.txt"

def is_frozen():
    return getattr(sys, "frozen", False)

def local_app_path() -> str:
    return sys.executable if is_frozen() else os.path.abspath(sys.argv[0])

def parse_version_from_name(name: str) -> str:
    """
    约定文件名 MikeTee_<版本>.exe，提取 <版本>，如 1.0 / 1.2.3
    """
    m = re.search(r"MikeTee[_-]([\d.]+)\.exe$", os.path.basename(name), re.I)
    return m.group(1) if m else ""

def get_local_version() -> str:
    # 直接从正在运行的可执行文件名解析版本
    return parse_version_from_name(local_app_path())

def _urlopen(url: str, timeout: int = 60):
    """
    使用自定义 opener：
      - 禁用系统代理（避免被代理/杀软劫持）
      - 添加常见浏览器头（UA/Referer/Accept/Accept-Encoding: identity）
      - 30x 重定向时保留原请求头（某些防盗链要 Referer/UA）
    """
    import urllib.request, ssl

    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
    REFERER = "https://download.xiliu.store/"

    class _KeepHeadersRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            new = super().redirect_request(req, fp, code, msg, headers, newurl)
            if new is None:
                return None
            for k, v in req.headers.items():
                if k not in new.headers:
                    new.add_header(k, v)
            return new

    ctx = ssl.create_default_context()
    try:
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
    except Exception:
        pass

    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),         # 禁用代理
        _KeepHeadersRedirect(),
        urllib.request.HTTPSHandler(context=ctx),
        urllib.request.HTTPHandler(),
    )
    opener.addheaders = [
        ("User-Agent", UA),
        ("Referer", REFERER),
        ("Accept", "*/*"),
        ("Accept-Encoding", "identity"),        # 二进制直传，避免被压缩改写
        ("Connection", "keep-alive"),
    ]
    req = urllib.request.Request(url, method="GET")
    return opener.open(req, timeout=timeout)

def _head_info(url: str, timeout: int = 20):
    """返回 (content_length:int, accept_range:bool, etag:str, last_modified:str)"""
    import urllib.request, ssl

    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
    REFERER = "https://download.xiliu.store/"

    class _KeepHeadersRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            new = super().redirect_request(req, fp, code, msg, headers, newurl)
            if new is None: return None
            for k, v in req.headers.items():
                if k not in new.headers:
                    new.add_header(k, v)
            return new

    ctx = ssl.create_default_context()
    try:
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
    except Exception:
        pass

    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _KeepHeadersRedirect(),
        urllib.request.HTTPSHandler(context=ctx),
        urllib.request.HTTPHandler(),
    )
    opener.addheaders = [
        ("User-Agent", UA),
        ("Referer",  REFERER),
        ("Accept",   "*/*"),
        ("Accept-Encoding", "identity"),
        ("Connection", "keep-alive"),
    ]

    req = urllib.request.Request(url, method="HEAD")
    try:
        with opener.open(req, timeout=timeout) as r:
            cl = r.headers.get("Content-Length")
            ar = "bytes" in (r.headers.get("Accept-Ranges","").lower())
            return (int(cl) if cl and cl.isdigit() else 0), ar, (r.headers.get("ETag") or "").strip(), (r.headers.get("Last-Modified") or "").strip()
    except Exception:
        return 0, False, "", ""

def fetch_remote_version() -> tuple[str, str]:
    """
    返回 (remote_version, download_url)
    优先读 JSON，失败则退化到 TXT
    """
    # JSON
    try:
        with _urlopen(REMOTE_MANIFEST_JSON) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ver = str(data.get("version") or "")
            url = str(data.get("url") or "")
            if ver and url:
                return ver, url
    except Exception:
        pass

    # TXT（只有文件名）
    try:
        with _urlopen(REMOTE_MANIFEST_TXT) as resp:
            filename = resp.read().decode("utf-8").strip()
            ver = parse_version_from_name(filename)
            if ver:
                # 如果 TXT 没给完整 URL，就默认拼子域名根路径
                if filename.startswith("http"):
                    return ver, filename
                # 你也可以固定放根目录
                return ver, f"http://download.xiliu.store/{filename}"
    except Exception:
        pass

    return "", ""

def version_tuple(v: str):
    return tuple(int(x) for x in re.findall(r"\d+", v))

def newer_than(v_remote: str, v_local: str) -> bool:
    # 纯数字点号语义比较，1.10 > 1.2
    try:
        return version_tuple(v_remote) > version_tuple(v_local)
    except Exception:
        return (v_remote and not v_local)

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def _has_mei_tail(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            f.seek(-8, os.SEEK_END)
            return f.read(8) == b"MEI\x0c\x0b\x0a\x0b\x0e"
    except Exception:
        return False
def _make_opener():
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
    REFERER = "https://download.xiliu.store/"

    class _KeepHeadersRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            new = super().redirect_request(req, fp, code, msg, headers, newurl)
            if new is None: return None
            for k, v in req.headers.items():
                if k not in new.headers:
                    new.add_header(k, v)
            return new

    ctx = ssl.create_default_context()
    try: ctx.set_ciphers("DEFAULT@SECLEVEL=1")
    except Exception: pass

    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),  # 禁用系统代理
        _KeepHeadersRedirect(),
        urllib.request.HTTPSHandler(context=ctx),
        urllib.request.HTTPHandler(),
    )
    opener.addheaders = [
        ("User-Agent", UA),
        ("Referer",  REFERER),
        ("Accept",   "*/*"),
        ("Accept-Encoding", "identity"),
        ("Connection", "keep-alive"),
    ]
    return opener

import os, tempfile, time, urllib.request, ssl

# 用下面这段替换原来的 download_file（签名保持一致）
import os, tempfile, time, urllib.request, ssl

# —— 仅替换 download_file，保持函数签名不变 —— 
import os, tempfile, time, urllib.request, ssl

def download_file(url: str, to_path: str, progress_cb=None, retries: int = 6):
    """
    稳健下载（保留：重试/指数退避 + MZ 头校验 + 已知 Content-Length 的完整性校验）
    变更点：
      - 移除了“PyInstaller MEI 尾标”校验
      - 每次尝试从 0 开始完整下载（不做断点续传）
      - 不做 416 兜底
    """
    opener = _make_opener()
    total, *_ = _head_info(url)  # 仅用于进度估算/长度校验

    # 把临时文件建在目标目录，避免跨盘原子替换错误
    dst_dir = os.path.dirname(to_path)
    os.makedirs(dst_dir, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="mike_dl_", suffix=".part", dir=dst_dir)
    os.close(fd)

    try:
        for attempt in range(retries):
            try:
                # 每次重试都从头开始：清空临时文件
                open(tmp, "wb").close()
                downloaded = 0

                req = urllib.request.Request(url, method="GET")
                with opener.open(req, timeout=180) as resp:
                    # 用 Content-Length 估算总长（用于进度和完整性校验）
                    cl = resp.headers.get("Content-Length")
                    if total == 0 and cl and cl.isdigit():
                        total = int(cl)

                    ctype = (resp.headers.get("Content-Type") or "").lower()
                    if "text/html" in ctype and url.lower().endswith(".exe"):
                        raise ValueError("服务器返回网页而非安装包（可能 404/防盗链）")

                    with open(tmp, "wb") as f:
                        while True:
                            chunk = resp.read(1 << 16)  # 64 KiB
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_cb and total:
                                progress_cb(min(int(downloaded * 100 / total), 100))

                # —— 收尾校验（保留 MZ 与长度；去掉 MEI 尾标）——
                with open(tmp, "rb") as f:
                    if f.read(2) != b"MZ":
                        raise ValueError("不是有效 EXE（缺少 MZ 头，可能是错误页）")

                if total and downloaded < total:
                    # 已知总长但未下满：判不完整 -> 交给下一轮重试/最终抛错
                    raise ValueError(f"文件未完整下载：{downloaded} / {total} 字节")

                # 通过校验 -> 原子替换落地
                os.replace(tmp, to_path)
                return

            except Exception:
                if attempt == retries - 1:
                    raise
                time.sleep(1.5 ** attempt)  # 指数退避后重试
                continue

    finally:
        # 清理残留
        if os.path.exists(tmp) and (not os.path.exists(to_path) or os.path.getmtime(tmp) >= os.path.getmtime(to_path)):
            try:
                os.remove(tmp)
            except Exception:
                pass
    
def _confirm_install(title="更新", text="下载完成，是否立即安装并重启？") -> bool:
    # MB_YESNO(0x4) | MB_ICONQUESTION(0x20)
    return ctypes.windll.user32.MessageBoxW(0, text, title, 0x00000024) == 6

def download_to_cache_and_prompt(url: str, rename_to: str = "MikeTee.exe"):
    """
    按你的需求：
    1) 把新包下载到【图2的第一个文件夹】dist\\update_cache
    2) 立刻弹窗“是否安装并重启”
    3) 点“是” → 覆盖当前 exe 并重启新版本
    """
    local = local_app_path()
    cache_dir, _ = update_dirs(local)  # => <dist>\update_cache
    # 用 URL 的文件名（形如 MikeTee_4.0.5.exe），也可以自定义
    fname = os.path.basename(urllib.parse.urlparse(url).path) or f"MikeTee_{int(time.time())}.exe"
    new_path = os.path.join(cache_dir, fname)

    # 下载（落在 update_cache），下载完成立即返回
    download_file(url, new_path, progress_cb=None)

    # 询问并安装
    if _confirm_install():
        apply_update_and_restart(local_path=local,
                                 new_file_path=new_path,
                                 debug=False,
                                 rename_to=rename_to)  # 最终把新包改名/覆盖为 MikeTee.exe



def get_app_base():
    """返回当前运行程序所在目录（开发态返回脚本目录）"""
    return os.path.dirname(sys.executable if getattr(sys, "frozen", False)
                           else os.path.abspath(sys.argv[0]))

def update_dirs(local_path: str = None):
    """返回(缓存目录, 日志目录)，均位于 EXE 同目录，若不存在自动创建"""
    base = os.path.dirname(local_path) if local_path else get_app_base()
    cache_dir = os.path.join(base, "update_cache")
    log_dir   = os.path.join(base, "update_logs")
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(log_dir,   exist_ok=True)
    return cache_dir, log_dir
# 放到 update_util.py
def refresh_explorer_icon(path: str):
    """让资源管理器刷新指定文件的图标，不会黑屏。"""
    import ctypes
    from ctypes import c_wchar_p
    SHCNE_UPDATEITEM = 0x00002000  # 该文件项更新
    SHCNF_PATHW      = 0x0005      # 参数是路径(Unicode)
    ctypes.windll.shell32.SHChangeNotify(SHCNE_UPDATEITEM, SHCNF_PATHW, c_wchar_p(path), None)
    # 保险起见再广播一次“关联变化”，不闪屏
    SHCNE_ASSOCCHANGED = 0x08000000
    ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, 0, None, None)


def apply_update_and_restart(local_path: str,
                             new_file_path: str,
                             debug: bool = False,
                             rename_to: str = ""):
    """
    覆盖式更新：等待主进程退出 -> 删除旧 exe -> 以新名字(可选)落地 -> 轻量刷新图标 -> 启动新 exe
    不再重启 explorer.exe，因此不会黑屏；启动时显式设置工作目录，避免资源找不到。
    """
    import os, sys, subprocess, ctypes

    # 以程序所在目录为基准（打包后和调试态都兼容）
    base_dir = os.path.dirname(local_path if getattr(sys, "frozen", False)
                               else os.path.abspath(sys.argv[0]))

    log_dir = os.path.join(base_dir, "update_logs")
    os.makedirs(log_dir, exist_ok=True)

    pid = os.getpid()
    bat_path = os.path.join(log_dir, f"update_{pid}.cmd")
    log_path = os.path.join(log_dir, f"mike_update_{pid}.log")

    # 批处理脚本（轻量刷新：清图标缓存 + SHChangeNotify，不杀 explorer）
    bat_content = rf"""@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "APP=%~1"
set "NEW=%~2"
set "PID=%~3"
set "RENAME=%~4"
set "LOG={log_path}"

echo.>>"%LOG%"
echo =====================>>"%LOG%"
echo [%date% %time%] updater start (PID=%PID%)>>"%LOG%"
echo APP=!APP!>>"%LOG%"
echo NEW=!NEW!>>"%LOG%"
echo RENAME=!RENAME!>>"%LOG%"

REM 等待主进程退出
:waitpid
tasklist /FI "PID eq %PID%" | find "%PID%" >nul
if not errorlevel 1 (
  timeout /t 1 /nobreak >nul
  goto waitpid
)

REM 保险再等 1 秒
timeout /t 1 /nobreak >nul

REM 计算目标路径（可改名）
for %%I in ("!APP!") do set "APPDIR=%%~dpI"
if not "!RENAME!"=="" (
  set "TARGET=!APPDIR!!RENAME!"
) else (
  set "TARGET=!APP!"
)

REM 删除旧 exe（最多重试 120 次）
set /a tries=0
:waitunlock
set /a tries+=1
del /f /q "!APP!" >>"%LOG%" 2>&1
if exist "!APP!" (
  if !tries! GEQ 120 (
    echo [%date% %time%] ERROR still locked after !tries! tries>>"%LOG%"
    goto end
  )
  timeout /t 1 /nobreak >nul
  goto waitunlock
)

echo [%date% %time%] moving NEW -> TARGET>>"%LOG%"
move /y "!NEW!" "!TARGET!" >>"%LOG%" 2>&1

REM —— 轻量刷新图标缓存（不重启 Explorer，不会黑屏） ——
ie4uinit.exe -ClearIconCache   >>"%LOG%" 2>&1
rundll32.exe shell32.dll,SHChangeNotify 0x08000000 0 0  >>"%LOG%" 2>&1

REM —— （可选）重建用户级开始菜单和公共桌面快捷方式 ——
set "SM_USER=%AppData%\Microsoft\Windows\Start Menu\Programs"
set "PUB_DESK=%Public%\Desktop"
for %%D in ("!SM_USER!" "!PUB_DESK!") do (
  if exist "%%~D" (
    powershell -NoProfile -Command ^
      "$s=(New-Object -COM WScript.Shell).CreateShortcut('%%~D\\MikeTee.lnk');" ^
      "$s.TargetPath='%TARGET%';$s.WorkingDirectory='%APPDIR%';$s.IconLocation='%TARGET%,0';$s.Save()" >>"%LOG%" 2>&1
  )
)

REM —— 启动新程序：一定指定工作目录，避免资源相对路径失效 ——
echo [%date% %time%] launching new exe>>"%LOG%"
start "" /D "!APPDIR!" "!TARGET!" >>"%LOG%" 2>&1

:end
echo [%date% %time%] updater done>>"%LOG%"
del "%~f0"
"""

    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    # 调用批处理（ShellExecute 失败则回退到 cmd.exe）
    args = f'"{local_path}" "{new_file_path}" {pid} "{rename_to or ""}"'
    SW_SHOW, SW_HIDE = 5, 0
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(None, "open", bat_path, args, base_dir,
                                                   SW_SHOW if debug else SW_HIDE)
        if ret <= 32:
            raise RuntimeError(f"ShellExecuteW failed: {ret}")
    except Exception:
        cmdexe = os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe")
        flags = (0x00000010 if debug else (0x00000008 | 0x08000000))  # 新控制台 或 隐藏/分离
        subprocess.Popen([cmdexe, "/c", bat_path, local_path, new_file_path, str(pid), rename_to or ""],
                         creationflags=flags, close_fds=True)

