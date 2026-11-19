# ximalaya-downloader

本文件是技能的工程说明；权威行为规范见 [`SKILL.md`](SKILL.md)。

## 简介

下载喜马拉雅免费专辑音频到本地。用本技能自带 Python 脚本走公开接口（无需登录），支持整专辑或区间下载为 m4a、默认生成 Markdown 清单、可选 ffmpeg 转 mp3；付费/VIP 集只跳过不绕过。在用户提供 ximalaya.com 专辑链接并要求下载时使用。主脚本失败时可回退已安装的 yt-dlp-downloader 或 youtube-downloader。不用于付费破解或非喜马拉雅站点。

## 何时使用

参见 `SKILL.md` frontmatter 的 `description` 字段所描述的触发场景。

## 主要章节

- 运行契约
- 何时使用
- 默认能力
- 主流程
- 兜底（主脚本无法处理时）
- 校验清单

## 脚本

- `scripts/self_check.py`
- `scripts/ximalaya_album_downloader.py`

## 目录结构

```text
SKILL.md           权威技能规范（agent 读取）
README.md          本文件，工程说明
references/        参考文档
assets/            示例与静态资源
expected_outputs/  期望输出样例（golden fixtures）
scripts/           可执行脚本（如存在）
```

> 版本：0.0.1
