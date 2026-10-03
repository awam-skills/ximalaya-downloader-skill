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
| 下载前付费预扫描（付费集标记跳过，不下载不绕过） | ✅ | 自动执行 |
| 命名宽度按全专辑集数统一（区间下载不出 `1_` vs `001_` 不一致） | ✅ | 自动执行 |
| 并发下载 | ✅ 并发 3 | `--workers N` |
| 失败集自动重试一轮 | ✅ | 自动执行 |
| 生成 Markdown 目录清单 `<专辑名>_清单.md` | ✅ 默认执行 | `--no-manifest` 关闭 |
| m4a 批量转 mp3 | ❌ 默认不转 | `--to-mp3` 开启 |
| 预演（只列将下载集数/付费标记，不写文件） | ❌ | `--dry-run` |

## 主流程（用脚本下载）

脚本位置：`scripts/ximalaya_album_downloader.py`

1. 从用户链接解析专辑 ID（`/album/<id>`）。
2. 拉取专辑曲目列表（接口 `revision/play/v1/show`，分页）。若 `ret != 200`，按「兜底」处理。
3. 确定专辑标题（从首集单集接口取 `album_title`，付费集也能取到），作为目录名（非法字符替换为 `_`）。
4. **付费预扫描**：下载前逐集确认 `is_paid`，付费集标记跳过并汇总（不下载、不绕过）。
5. 并发下载（默认 3 线程）：逐集取直链（`m.ximalaya.com/tracks/<id>.json` 的 `play_path_64`）并下载为 m4a。
   - 已存在同名且非空文件：跳过（支持断点续传）。
   - **失败集自动重试一轮**，仍失败才计入失败。
6. 生成 MD 清单（默认）。
7. 若 `--to-mp3`：调用 ffmpeg 将目录内 m4a 转为 mp3（保留原 m4a）。

### 命令示例

```bash
# 下载整个专辑到 Downloads（并发默认 3）
python scripts/ximalaya_album_downloader.py "https://www.ximalaya.com/album/72503439"

# 指定输出目录 + 转 mp3 + 并发 5
python scripts/ximalaya_album_downloader.py "https://www.ximalaya.com/album/<ID>" -o "D:\Downloads" --to-mp3 --workers 5

# 只下 10-20 集
python scripts/ximalaya_album_downloader.py "https://www.ximalaya.com/album/<ID>" --start 10 --end 20

# 预演：只列将下载集数与付费标记，不写文件
python scripts/ximalaya_album_downloader.py "https://www.ximalaya.com/album/<ID>" --dry-run

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
