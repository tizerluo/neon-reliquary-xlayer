# 开发环境：硬件与软件依赖

2026-10-02 盘点。数据来自唯一一台开发机的实测和对仓库代码的检查；**还没有在第二台机器上验证过**，“最低配置”是按实测内存和耗时推算的。

## 开发机（Blender 美术管线）

实测机器：Mac Studio，Apple M4 Max（16 核 CPU、40 核 GPU），128 GB 统一内存，macOS 27。

| 操作 | 耗时 | 内存峰值 |
| --- | --- | --- |
| `build_arena.py -- cathedral --no-export`（只构建场地） | 15 秒 | 约 1.1 GB |
| 同上加 `--review --only game-center,overview`（两张 Cycles GPU 审图） | 31 秒 | 约 14 GB |

审图是最吃内存的环节，一轮场地或角色审图要出十几到几十张。

| | 最低（推算） | 推荐 |
| --- | --- | --- |
| 机器 | Apple 芯片 Mac（M1 Pro 及以上） | M3 Max / M4 Max 级 |
| 内存 | 32 GB。16 GB 只够构建，审图会大量换页，需要调低 `ARENA_SAMPLES` 并且一次只跑一个 Blender | 64 GB 以上 |
| 显卡 | 支持 Metal 的 Apple GPU | 30 核以上 GPU |
| 硬盘空闲 | 20 GB | 50 GB 以上 |

硬盘构成：仓库约 2.4 GB（其中审图约 1.3 GB，已 gitignore，可重新生成；`.git` 约 350 MB），Blender 约 2 GB，每轮返工的备份会继续增加。

### Windows / Linux

审图脚本把 Cycles 设备写死为 Metal（`tools/kit/review.py`、`tools/arenas/review.py`、`tools/blades/review.py`、`tools/pickups/review.py`、`tools/render_nyx_review.py`）。在其他系统上会回退到 CPU 渲染，慢几十倍。要用的话需把 `compute_device_type` 改为 `OPTIX` / `CUDA` / `HIP`，建议 NVIDIA RTX、显存 12 GB 以上。

## 游戏测试设备（浏览器）

- 硬性要求：**WebGL2**（`src/renderer.js` 用 `webgl2`；three.js 0.186 只支持 WebGL2）。
- 已实测：只有上面这台 M4 Max。HD 画布 3.1–3.9 ms / 帧，场地层约 74 次绘制，数百把飞剑同屏不掉帧，显示器上限 100 FPS。详见 `docs/IN-GAME-VISUAL-TEST.md` 和 `HANDOFF.md`。
- 未实测：核显 / 低端独显、真实手机（发热、显存、长时间战斗）。`docs/VISUAL-UPGRADE-RESEARCH.md` 的“桌面 60 FPS、手机 30 FPS”是设计目标，不是已达成的结果。
- 建议的测试组合：一台 Apple 芯片或独显桌面机 + Chromium 内核浏览器；再补一台中端机或手机作为下限参考（目前缺）。

## 软件依赖

| 软件 | 当前版本 | 用途 | 要求 |
| --- | --- | --- | --- |
| Blender | 5.2.2 LTS（Homebrew） | 角色 / 飞剑 / 道具 / 场地建模、导出与 Cycles 审图 | 5.2.x（脚本在 5.2 上编写和验证） |
| Blender 自带 Python | — | `bpy`、`bmesh`、`mathutils`、`numpy` | 随 Blender 提供，无需另装 |
| 系统 Python 3 | 3.14.7 | `build.py`、本地服务器（只用标准库）；校验与印样 | `pip install -r requirements.txt`（Pillow、numpy） |
| Node.js / npm | 22.22.3 / 10.9.8 | `npm test`；安装 three.js | Node 18 以上（`package.json` 的 `engines`）；`npm ci --ignore-scripts` |
| npm 包 | three 0.186.0、ethers 6.16.0 | 高清画布 / 图鉴页直接加载 `node_modules/three` | 以 `package-lock.json` 为准 |
| 浏览器 | Chromium 内核（Ego Chromium、Claude 应用内置浏览器） | 游戏实测、截图、性能数据 | 支持 WebGL2 |
| git | — | 版本管理 | — |
| ffmpeg | 已装 | 现有脚本不使用，只在做视频时需要 | 可选 |

## 本地端口

| 端口 | 服务 | 命令 |
| --- | --- | --- |
| 4173 | 游戏与图鉴静态服务器 | `npm run visual:lab`（= `python3 -m http.server 4173 --bind 127.0.0.1`） |
| 4180 | 场地 three.js 审图 | `python3 tools/arenas/preview_server.py` |
| 8766 | 外部 AI 本地桥接（可选） | `python3 tools/live_server.py` |

## 首次搭建

```bash
brew install --cask blender
pip3 install -r requirements.txt
npm ci --ignore-scripts
npm test
```

## 已知问题

- 在 Claude Code 里跑 Blender 必须关闭 Bash 沙盒，否则 Metal 渲染崩溃。
- `blender -b` 偶发启动崩溃（NSURL nil），重试即可。
- 后台起的 4173 服务器最长 2 小时会被自动停，到时重启。
