# 狗头军师 Jev Chat · Windows 源码适配

本目录基于 [jev-chat-windows](https://github.com/jev-chat/jev-chat-windows) 的窗口采集、RapidOCR、悬浮窗和微信草稿填入链路。接入狗头军师的证据边界与自然口吻约束：先核对识别原文及说话人，再做策略判断、生成并排序候选；悬浮窗显示可能意图、模型估计的判断把握、已知事实、仍未知、下一步和停止条件。对方明确要求停止联系时，这轮不生成候选。

**状态：可构建预览 ZIP，尚未在 Windows 实机验收。** GitHub Actions 会提供预览包；构建通过不代表微信各版本实机测试通过。策略可选 Jev 或 DeepSeek 官方；DeepSeek 独立整理证据，尝试以三次标签轮换的首 token 权重核对策略，无法稳定取得权重时明确标注不可用。候选百分比为本轮相对推荐权重，并非回复成功率。

使用流程：打开微信会话并保持窗口可见；首次进入设置，选择策略与回复模型，配置 Key；识图可选本地 RapidOCR、DeepSeek 图片识别或 OpenRouter 图片识别。云端识图会上传裁剪后的聊天区截图并可能计费。读取新消息后点「核对原文并分析」，逐行修正“我／对方”的归属和文字，再确认。结果页可选「详细分析」「更像我一点」，也可复制或填入候选草稿。K 线窗口内置五种走势并支持导入带 `timestamp,sender,message` 的聊天 CSV；图中展示消息方向净差，无法衡量关系质量。设置页可按会话保存阶段、目标和简短背景；完整聊天仅留在运行时内存。OCR 可能认错说话人，填入前还须确认当前会话、收件人和文字；程序不会自动发送。

要求 Windows 10 1903+ 或 Windows 11、微信 Windows 4.x、Python 3.10–3.12。源码运行：

```powershell
cd integrations\jev_windows
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

密钥写入当前 Windows 用户的 `GOUTOU_JEV_API_KEY`、`GOUTOU_DEEPSEEK_STRATEGY_KEY`、`GOUTOU_LLM_API_KEY` 和 `GOUTOU_OCR_API_KEY` 环境变量（按实际选择填写）；识图来源与回复来源相同时可以复用回复 Key。不会读取原版 Jev 安装时保存的 Key。其他设置写在本目录的 `config.json`，已被 Git 忽略。`build.bat` 可在 Windows 上生成可执行目录和 `dist/goutoujunshi-jev-chat-windows-preview.zip`；ZIP 解压后保持整个目录完整，从其中运行 `.exe`。数据使用见仓库根目录 [说明](../../PRIVACY.md)。

源码来源及第三方组件许可见本目录的 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。特别是 PySide6-Fluent-Widgets 会影响 Windows 发布包的许可条件；发布时须单独核对。
