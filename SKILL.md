---
name: ximalaya-downloader
version: 0.0.1
description: "下载喜马拉雅免费专辑音频到本地。用本技能自带 Python 脚本走公开接口（无需登录），支持整专辑或区间下载为 m4a、默认生成 Markdown 清单、可选 ffmpeg 转 mp3；付费/VIP 集只跳过不绕过。在用户提供 ximalaya.com 专辑链接并要求下载时使用。主脚本失败时可回退已安装的 yt-dlp-downloader 或 youtube-downloader。不用于付费破解或非喜马拉雅站点。"
disable-model-invocation: true
---

# ximalaya-downloader（喜马拉雅专辑下载）

下载喜马拉雅**免费/可合法获取**的专辑音频。仅处理喜马拉雅音频专辑；付费、VIP 或加密绕过请求直接拒绝。

## 运行契约

- 环境：Python 3（脚本仅用标准库）；ffmpeg 仅在 `--to-mp3` 时需要
- 允许效果：向用户指定或默认 `~/Downloads/<专辑名>/` 写入 m4a（及可选 mp3、Markdown 清单）
- 禁止效果：登录破解、付费直链绕过、下载非喜马拉雅目标
- 主可观察结果：目录内非空 m4a（或 dry-run/only-list 的列表输出）+ 默认生成的 `<专辑名>_清单.md`

## 何时使用

- 用户给出 `www.ximalaya.com` 专辑链接，要求下载整专辑或部分集数
- 需要批量保存为 m4a / mp3，或生成专辑目录清单

近邻边界：多站点通用下载归 `yt-dlp-downloader`；YouTube/HLS 深度处理归 `youtube-downloader`。本技能只拥有喜马拉雅专辑音频分支。

## 默认能力

| 能力 | 默认 | 开关 |
|------|------|------|
| 下载专辑/区间为 m4a | 开启 | 必做 |
| 专辑目录 + `集号_标题` 命名 | 开启 | — |
| 付费预扫描（付费集跳过，不绕过） | 开启 | 自动 |
| 命名宽度按全专辑集数统一 | 开启 | 自动 |
| 并发下载 | 并发 3 | `--workers N` |
| 失败集自动重试一轮 | 开启 | 自动 |
| Markdown 清单 `<专辑名>_清单.md` | 开启 | `--no-manifest` 关闭 |
| m4a 转 mp3 | 关闭 | `--to-mp3` |
| 预演（列集数/付费标记，不写文件） | 关闭 | `--dry-run` |
| 仅列曲目 | 关闭 | `--only-list` |

## 主流程

脚本：`scripts/ximalaya_album_downloader.py`

1. 从用户链接解析专辑 ID（路径段中的数字 ID）。
2. 分页拉取曲目列表（`revision/play/v1/show`）。若 `ret != 200`，进入兜底。
3. 取专辑标题（首集单集接口的 `album_title`；失败则 `album_<id>`），清洗非法文件名字符。
4. 付费预扫描：标记 `is_paid` 集为跳过并汇总。
5. 并发下载（默认 3）：取 `play_path_64`（或 32）写入 m4a；已存在非空文件跳过；失败自动重试一轮。
6. 默认写 Markdown 清单。
7. 若 `--to-mp3`：用 ffmpeg 转换（保留 m4a）；找不到 ffmpeg 则跳过并提示。

完成标准：脚本退出且汇总行可核对；非 dry-run/only-list 时输出目录存在、免费集 m4a 非空（或明确记入失败）、付费集未下载、清单与开关一致。

### 命令示例

```bash
# 整专辑（默认输出到 ~/Downloads/<专辑名>/）
python scripts/ximalaya_album_downloader.py "https://www.ximalaya.com/album/72503439"

# 指定目录 + 转 mp3 + 并发 5
python scripts/ximalaya_album_downloader.py "https://www.ximalaya.com/album/72503439" -o "D:\Downloads" --to-mp3 --workers 5

# 只下第 10–20 集
python scripts/ximalaya_album_downloader.py "https://www.ximalaya.com/album/72503439" --start 10 --end 20

# 预演：不写文件
python scripts/ximalaya_album_downloader.py "https://www.ximalaya.com/album/72503439" --dry-run

# 只列曲目
python scripts/ximalaya_album_downloader.py "https://www.ximalaya.com/album/72503439" --only-list
```

在技能根目录执行上述命令；或把 `scripts/ximalaya_album_downloader.py` 换成当前安装路径下的同名脚本。

## 兜底（主脚本无法处理时）

仅当主脚本报错、接口 `ret≠200`、无法解析专辑或单集直链缺失时，按顺序尝试**已安装**技能（基于 yt-dlp，喜马拉雅支持可能不稳）：

1. `yt-dlp-downloader` — 通用多站点
2. `youtube-downloader` — YouTube/HLS 深度场景

规则：先主脚本；确认失败后再兜底；兜底同样只取免费/有权限内容；主脚本恢复后回到主流程。未安装对应技能时如实说明，不伪造路径。

## 校验清单

发布或改脚本后，先跑离线自检：`python scripts/self_check.py`。

- [ ] 自检通过；CLI `--help` 含 `--start/--end/--dry-run/--to-mp3` 等已文档开关
- [ ] 免费集 m4a 非空，命名宽度与全专辑集数一致
- [ ] 未关闭清单时已生成 `<专辑名>_清单.md`（含集号/标题/时长/状态/文件/大小）
- [ ] 付费集仅标记跳过，未尝试破解
- [ ] 失败集已重试或记入失败汇总
