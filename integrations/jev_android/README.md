# 狗头军师 Jev Chat · Android 源码适配

本目录基于 [Jev Android](https://github.com/jev-chat/jev-chat-jarvis) 的聊天应用采集、ML Kit 中文离线 OCR、悬浮窗、Jev 判断和候选填入链路。已改为独立应用 ID `com.goutoujunshi.chat`，接入狗头军师的自然口吻、事实与推测边界、下一步和停止条件。原文与说话人仍需用户核对；对方明确要求停止联系时不生成候选，不自动发送。

**状态：提供 Android 11+ 调试预览 APK，真机验收尚未完成。当前版本无法截取微信聊天画面，因此暂不支持微信。** QQ、X、飞书等聊天应用路径仍需在对应设备上验证。首次安装后的助手和自动分析默认关闭，需在界面中主动开启。本目录不包含上游现成 APK。

设置页可选择 Jev 或 DeepSeek 官方进行策略判断，回复模型可配 DeepSeek、OpenRouter 等兼容接口；两者分开配置。视觉接口可选择 DeepSeek Flash、OpenRouter、通义兼容或自定义模型，截图识别开关可在本地 ML Kit 与视觉模型之间切换。云端识图会发送聊天区域截图并产生服务用量。识别后的对话须核对原文和说话人，再由用户确认分析；结果包含意图、策略、相对排序、「详细分析」和「更像我一点」。关系联系人可保存阶段、目标和补充背景；K 线窗口可查看五种示例走势或导入带 `timestamp,sender,message` 的聊天 CSV。K 线展示消息方向净差，不能解释为关系质量或成功率。

从[最新 Release](https://github.com/shengjidaguai-china/goutoujunshi-jev-chat/releases/latest)下载 `goutoujunshi-jev-chat-android-debug.apk`，在 Android 11 或更新版本上允许系统安装此来源的应用后安装。旧版调试 APK 与新版可能由不同的临时调试证书签名；如提示签名不一致，需卸载旧包再安装，本机应用数据会随卸载清除，先记录好需要保留的设置。打开应用，配置判断和回复接口，按提示授予无障碍、悬浮窗权限，再主动开启助手。应用只生成草稿，由你决定是否发送。请勿使用该版本尝试读取微信聊天。

要求 Android 11+，构建机须安装 JDK 17、Android SDK 35。进入本目录后运行：

```bash
./gradlew :app:testDebugUnitTest :app:assembleDebug
```

成功后调试包在 `app/build/outputs/apk/debug/`。应用的设置页可分别配置判断、回复、视觉接口；只有同一协议、主机和端口的接口才能共用密钥，跨服务须分别填写。请仅在自己的设备和有权查看的对话中使用。数据使用见仓库根目录 [说明](../../PRIVACY.md)。

源码来源与署名见本目录的 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。
