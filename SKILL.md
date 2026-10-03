---
name: ximalaya-downloader
description: >-
  下载喜马拉雅免费专辑音频到本地。使用本技能自带的 Python 脚本（走喜马拉雅公开接口，
  无需登录/webtk），下载整个专辑或指定区间为 m4a，默认生成 Markdown 目录清单，
  可选用 ffmpeg 转 mp3。当主脚本对某链接无法处理时，回退参考已安装的
  yt-dlp-downloader 与 youtube-downloader 技能。
disable-model-invocation: true
---

# ximalaya-downloader（喜马拉雅专辑下载）

下载喜马拉雅**免费/可合法获取**的专辑音频。仅处理喜马拉雅音频专辑；如需下载付费/VIP 内容或破解加密，请拒绝。

## 何时使用

- 用户提供 `www.ximalaya.com/album/<ID>` 链接，要求下载整个专辑或部分集数
- 需要把喜马拉雅专辑批量保存为 m4a / mp3，或生成专辑目录清单

## 依赖

- Python 3（脚本仅用标准库）
- ffmpeg（可选，仅 `--to-mp3` 时需要；不安装则跳过转换并提示）

## 核心能力与默认行为

| 能力 | 默认 | 开关 |
|------|------|------|
| 下载专辑/区间音频为 m4a | ✅ | 必做 |
| 自动建专辑目录并按 `集号_标题` 命名 | ✅ | — |
| 生成 Markdown 目录清单 `<专辑名>_清单.md` | ✅ 默认执行 | `--no-manifest` 关闭 |
| m4a 批量转 mp3 | ❌ 默认不转 | `--to-mp3` 开启 |

## 主流程（用脚本下载）

脚本位置：`scripts/ximalaya_album_downloader.py`

1. 从用户链接解析专辑 ID（`/album/<id>`）。
2. 拉取专辑曲目列表（接口 `revision/play/v1/show`，分页）。若 `ret != 200`，按「兜底」处理。
3. 确定专辑标题（取首集 `album_title`），作为目录名（非法字符替换为 `_`）。
4. 逐集取直链（`m.ximalaya.com/tracks/<id>.json` 的 `play_path_64`）并下载为 m4a。
   - 遇到 `is_paid=True`：报"付费/VIP 内容无法免费下载"，**不要**尝试绕过。
   - 已存在同名且非空文件：跳过（支持断点续传）。
5. 生成 MD 清单（默认）。
6. 若 `--to-mp3`：调用 ffmpeg 将目录内 m4a 转为 mp3（保留原 m4a）。

### 命令示例

```bash
# 下载整个专辑到 Downloads
python scripts/ximalaya_album_downloader.py "https://www.ximalaya.com/album/72503439"

# 指定输出目录 + 转 mp3
python scripts/ximalaya_album_downloader.py "https://www.ximalaya.com/album/<ID>" -o "D:\Downloads" --to-mp3

# 只下 10-20 集
python scripts/ximalaya_album_downloader.py "https://www.ximalaya.com/album/<ID>" --start 10 --end 20

# 只列目录不下载
python scripts/ximalaya_album_downloader.py "https://www.ximalaya.com/album/<ID>" --only-list
```

## 兜底参考（主脚本无法处理时）

仅当主脚本对目标链接报错、接口失效或返回异常时，按顺序回退以下已安装技能（它们基于 yt-dlp，适合**视频/多平台**内容，喜马拉雅专辑支持可能不稳）：

1. **yt-dlp-downloader**（`C:\Users\Administrator\.agents\skills\yt-dlp-downloader`）— 通用多站点下载，含 YouTube/B站/抖音/Twitter 等。
2. **youtube-downloader**（`C:\Users\Administrator\.agents\skills\youtube-downloader`）— 深度针对 YouTube/HLS，含 PO Token、浏览器 cookies、防盗链处理。

使用规则：
- 先尝试主脚本；确认失败（接口 ret≠200 / 无法解析专辑 / 单集直链缺失）才走兜底。
- 兜底同样**只下载免费/有权限的内容**，不用于绕过付费或会员限制。
- 主脚本恢复可用后回到主流程。

## 校验

- [ ] 输出的 m4a 均非空，按集号连续命名
- [ ] MD 清单已生成且包含集号/标题/时长/文件/大小
- [ ] 付费内容被正确拦截，未尝试破解
