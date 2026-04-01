# 启动器功能自检指南

本文用于验证当前启动器：进程检测/关闭、日志、GUI、强制更新与灰度发布是否生效。

## 0. 预置文件与目录

确保目录结构如下（与你当前项目文件名对应）：

```
f:/miketee4(1080)_4.0.11backup/
  launcher.exe
  launcher.py
  launcher_config.json
  app/
    main_1080_mata.exe
    version.json
```

`version.json` 示例：

```json
{ "version": "1.0.0" }
```

## 1. 准备 manifest.json 示例

示例（含灰度与强制更新字段）：

```json
{
  "latest_version": "1.0.2",
  "download_url": "https://github.com/xxx/releases/download/v1.0.2/app_1.0.2.zip",
  "sha256": "<sha256-1.0.2>",
  "min_supported_version": "1.0.0",
  "force_update": false,
  "channels": {
    "stable": {
      "version": "1.0.1",
      "download_url": "https://github.com/xxx/releases/download/v1.0.1/app_1.0.1.zip",
      "sha256": "<sha256-1.0.1>"
    }
  },
  "rollout": {
    "stable": {
      "version": "1.0.2",
      "download_url": "https://github.com/xxx/releases/download/v1.0.2/app_1.0.2.zip",
      "sha256": "<sha256-1.0.2>",
      "percentage": 30,
      "start": "2026-03-01T00:00:00+08:00",
      "end": "2026-03-31T23:59:59+08:00"
    }
  }
}
```

## 2. launcher_config.json 示例

```json
{
  "manifest_url": "https://raw.githubusercontent.com/xxx/xxx/main/manifest.json",
  "app_dir": "app",
  "temp_dir": "temp",
  "backup_dir": "backup",
  "app_exe": "your_app.exe",
  "show_gui": true,
  "auto_kill": false,
  "wait_close_timeout": 60,
  "state_file": "client_state.json",
  "channel": "stable"
}
```

## 3. 测试项与步骤

### A. 进程检测与自动关闭

1. 先启动主程序 `main_1080_mata.exe`（保持运行）。
2. 运行 `launcher.exe`。
3. 期望：
   - 若 `auto_kill=false`：出现提示“请关闭正在运行的程序...”，手动关闭后继续更新。
   - 若 `auto_kill=true`：主程序被自动结束后继续更新。

### B. 日志系统（launcher.log）

1. 运行 `launcher.exe` 完成一次检查/更新。
2. 期望：目录中生成 `launcher.log`，包含“正在下载/备份/解压”等记录。

### C. 更新 GUI/进度

1. 配置 `show_gui=true`。
2. 运行 `launcher.exe`。
3. 期望：出现简单窗口显示状态与进度条。

### D. 强制更新

1. 将 `manifest.json` 设置：
   - `force_update: true`
   - 或 `min_supported_version` 大于本地版本
2. 让下载包故意失败（如改错 `download_url` 或 `sha256`）。
3. 期望：
   - 更新失败后**不启动旧版本**
   - GUI 弹窗提示必须更新

### E. 灰度发布

1. 设定 `rollout.stable.percentage=30`。
2. 在 `client_state.json` 中固定 `client_id`（让同一台设备命中率稳定）。
3. 多台设备或修改 `client_id` 后多次测试：
   - 命中的设备拉取 `rollout.version`
   - 未命中则拉取 `channels.stable.version`

## 4. 常见问题

- GUI 不显示：检查本机是否有 `tkinter` 支持。
- 进程检测失败：确保 `app_exe` 名称与任务管理器中一致（此处为 `main_1080_mata.exe`）。
- 下载进度不动：服务器未返回 `Content-Length` 时将看不到进度百分比。
