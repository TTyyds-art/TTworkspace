# 语言切换实施待办（繁体）

## 目标
- 基于 `QTranslator` + `.qm` 方式，实现全局繁体（zh_TW）语言切换与持久化。

## 待办清单
- [ ] **梳理文本来源**
  - [ ] UI 生成文本：确认所有 `ui_1080_py/Ui_*.py` 与 `ui_1080_py/ui_language_settings.py` 的 `retranslateUi()` 覆盖范围。
  - [ ] 业务硬编码文本：梳理 `main_1080_mata.py` 与 `control/*.py` 中直接写死的文案与提示。

- [ ] **准备翻译文件**
  - [ ] 使用 `pylupdate5` 扫描项目生成 `zh_TW.ts`（已生成请跳过）。
  - [ ] 用 Qt Linguist 完成翻译并导出 `zh_TW.qm`。

- [ ] **加载翻译器**
  - [ ] 在入口处初始化 `QTranslator`（主入口见 `main_1080_mata.py`）。
  - [ ] 在语言切换时重新 `installTranslator()`，并触发所有窗口 `retranslateUi()`。
  - [ ] 在设置页“应用/切换语言”按钮中调用切换逻辑（`control/language_settings_mata.py`）。

- [ ] **刷新全部界面**
  - [ ] 对所有 UI 类调用 `retranslateUi()`（例如 `Ui_main_1080_ui.retranslateUi()`、`Ui_main_ui.retranslateUi()`）。
  - [ ] 业务文案通过统一 `tr()` 或字典映射返回翻译，避免遗漏。

- [ ] **持久化语言**
  - [ ] 语言选择写入配置（JSON/INI）。
  - [ ] 启动时读取并应用语言。

- [ ] **可选快速落地**
  - [ ] 先用 OpenCC 批量转繁体生成初版翻译，再人工修订。

## 里程碑
- [ ] `zh_TW.qm` 生成完成并可被加载。
- [ ] 主界面与设置界面切换为繁体无遗漏。
- [ ] 重启后语言保持繁体。
