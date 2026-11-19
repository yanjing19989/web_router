# 本地项目启动器（web_router）

一个面向 Windows 的极简本地 Web 项目启动与管理控制台。后端基于 Python 标准库 `ThreadingHTTPServer` 与原生 Win32 `ctypes`（系统托盘、高分屏文件夹选择器、Job Object 进程树兜底），前端为纯原生 HTML/CSS/JS，无重型框架依赖、常驻低占用。

## 核心特性

- **自动识别项目类型**：支持 `npm`（Vite / Next.js / react-scripts / 通用脚本）、`Python`（Django / `__main__.py` 包 / FastAPI / Flask / 脚本，自动优先使用项目 `.venv` 或 `venv`）与静态站点（`index.html`）。
- **低占用与快速响应**：单次系统进程快照批量采样、前端卡片原地增量更新、空闲或后台标签页自动暂停轮询、静态资源 `ETag / 304` 缓存协商。
- **可靠进程清理**：每个项目绑定独立 Windows Job Object（`KILL_ON_JOB_CLOSE`），无论是点击「停止」、托盘「停止全部」、退出启动器还是任务管理器强杀，均能完整清理整棵子进程树并释放端口。
- **使用友好**：重复启动自动检测已有实例并直接打开控制台；启动失败自动捕获并展示 `stderr` 报错；支持前台打开项目所在目录；自动读取项目图标并支持首字母大写 SVG 回退。

## 环境要求与安装

- **系统**：Windows 10 / 11（亦可在 Linux / macOS 下以 `--no-tray` 模式运行管理服务）
- **Python**：3.10 及以上

安装依赖（仅 `psutil` 用于精确采集 CPU / USS / VMS 指标，`pytest` 用于运行测试）：

```bash
pip install -r requirements.txt
```

## 启动方式

### 1. 日常无控制台窗口托盘模式（推荐）

双击或运行 `run_tray.pyw`，启动器会驻留在 Windows 系统托盘并自动打开浏览器控制台：

```bash
pythonw run_tray.pyw
```

如果只希望静默驻留托盘、不自动弹出浏览器（适合设为开机自启）：

```bash
pythonw run_tray.pyw --no-browser
```

> 若启动器已在运行，再次执行 `pythonw run_tray.pyw` 不会冲突报错，而是直接打开已有控制台页面。

### 2. 命令行模式

```bash
python app.py [--port 8888] [--no-browser] [--no-tray]
```

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--port` | 管理控制台监听端口（监听地址固定为 `127.0.0.1`） | `8888` |
| `--no-browser` | 启动时不自动打开浏览器 | 关闭 |
| `--no-tray` | 不创建系统托盘图标，直接在前台终端运行 | 关闭 |

## 项目自动识别规则

点击页面右上角「添加项目」选择本地文件夹后，启动器会按以下优先级自动识别并分配空闲端口（`3000–8999`）：

1. **npm 项目**（存在 `package.json` 且含 `dev` / `start` / `serve` 脚本）：
   - 自动识别 `Vite`（注入 `--host 127.0.0.1 --port {port}`）、`Next.js`（注入 `-H 127.0.0.1 -p {port}`）、`react-scripts` 或通用 `npm run <script>`。
2. **Python 项目**（优先检测项目内 `.venv/Scripts/python.exe` 或 `venv/Scripts/python.exe`）：
   - `manage.py` → Django `runserver`
   - 顶层含 `__main__.py` 的包目录 → `python -m <package> --host 127.0.0.1 --port {port}`
   - `main.py` / `app.py` 含 `FastAPI(` 或 `Flask(` → 自动生成 `uvicorn` / `flask run` 命令
   - 其他 `main.py` / `app.py` → 直接运行脚本并传入 `--host` / `--port`
3. **静态站点**（存在 `index.html`）：
   - 使用 `python -m http.server {port} --bind 127.0.0.1`。

保存前可在弹窗中手动修改项目名称、类型、启动命令（支持 `{port}` 占位符）及端口。

## 如何为项目添加卡片图标

启动器会在每张项目卡片的项目名称左侧显示项目图标，**自动扫描项目目录中的标准图标文件**；如果未找到任何图标文件，则自动回退显示以项目名称首字符大写生成的 SVG 图标。

### 支持的图标格式

按优先级支持：`.svg`（推荐，矢量清晰）、`.png`、`.ico`、`.webp`。修改或新增图标文件后，刷新控制台即可生效（接口自动携带文件修改时间参数防止浏览器缓存旧图）。

### 各类型项目推荐放置位置

- **通用（适用于所有类型，优先级最高）**：直接放在项目根目录：
  - `icon.svg` / `icon.png` / `icon.ico` / `icon.webp`
  - `favicon.svg` / `favicon.png` / `favicon.ico`
  - `logo.svg` / `logo.png`
- **npm 项目（Vite / Next.js / React 等）**：
  - Vite / CRA / 通用前端：`public/favicon.svg`（或 `.png` / `.ico`）、`public/icon.svg`、`public/logo.svg`
  - Next.js App Router：`src/app/icon.svg`（或 `.png` / `favicon.ico`）、`app/icon.svg`（或 `.png` / `favicon.ico`）
- **Python 项目（FastAPI / Flask / Django 等）**：
  - `static/favicon.svg`（或 `.png` / `.ico`）、`static/icon.svg`、`static/logo.svg`
  - `assets/favicon.svg`（或 `.png` / `.ico`）、`assets/icon.svg`
- **静态站点**：
  - 根目录 `favicon.svg` / `favicon.ico` / `icon.svg`，或 `assets/`、`static/`、`public/` 下的同名文件。

## 日常使用与托盘菜单

- **网页控制台**：
  - 按 `npm` / `Python` / `静态` 类别筛选项目；卡片标题栏通过图标直观区分项目类型。
  - 启动/停止项目、在浏览器中打开项目地址、前台打开项目所在目录、编辑配置或删除项目（运行中的项目需先停止再编辑或删除）。
- **系统托盘图标**：
  - **左键单击 / 双击**：打开管理控制台页面。
  - **右键菜单**：打开控制台、查看运行中项目数、停止全部项目、退出启动器。

## 数据存储与运行测试

- **配置持久化**：项目列表保存在仓库根目录的 `.local_data/projects.json`（已被 `.gitignore` 忽略），运行状态仅保存在当前启动周期内。
- **自动化测试**：

```bash
pytest -v
```
