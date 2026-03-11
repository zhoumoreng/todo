# TodoFloat - Windows 桌面悬浮待办事项

一个始终悬浮在 Windows 桌面右上角的轻量级待办事项工具，支持优先级管理、历史查看、系统托盘等功能，打包为单个 `.exe` 文件无需安装。

## 功能特性

- **悬浮置顶**：始终显示在屏幕右上角，不遮挡主要工作区
- **今日待办**：快速查看和管理当天的待办事项
- **优先级管理**：支持「紧急」和「一般」两种优先级
- **完成状态**：圆形复选框勾选，已完成项显示打勾状态
- **历史查看**：通过日期导航或日历选择器查看任意日期的待办
- **全部待办**：单独标签页展示所有未完成（或全部）待办，按日期分组
- **数据持久化**：SQLite 本地数据库，数据不丢失
- **字体设置**：可自定义字体家族和字号
- **系统托盘**：关闭按钮最小化到托盘，右键退出
- **单实例运行**：同一时间只允许运行一个实例
- **可拖动缩放**：支持拖拽移动窗口位置，右下角可调整大小

## 截图预览

```
┌─────────────────────────────┐
│  待办事项            ⚙  ✕  │  ← 标题栏（可拖动）
├──────────┬──────────────────┤
│  今日    │  全部待办        │  ← 标签切换
├──────────┴──────────────────┤
│  ◀  2026-03-11  ▶  [日历]  │  ← 日期导航
│  完成 1/3                   │
├─────────────────────────────┤
│  ○ 写周报              紧急 │
│  ● 回复邮件            完成 │  ← 待办列表
│  ○ 代码评审            一般 │
├─────────────────────────────┤
│  [ 输入新待办内容...       ]│
│  优先级: [一般 ▼]  [+ 添加]│  ← 输入区
└─────────────────────────────┘
```

## 快速开始

### 直接使用（推荐）

下载 `dist/TodoFloat.exe`，双击运行即可，无需安装任何依赖。

### 从源码运行

**环境要求**

- Python 3.11+
- Windows 10/11

**安装依赖**

```bash
pip install -r requirements.txt
```

**运行**

```bash
python main.py
```

### 打包为 exe

```bash
pyinstaller TodoFloat.spec
```

打包完成后在 `dist/TodoFloat.exe`（约 36MB）。

## 项目结构

```
dbsx/
├── main.py                  # 程序入口，单实例控制
├── requirements.txt         # 依赖列表
├── TodoFloat.spec           # PyInstaller 打包配置
├── db/
│   ├── __init__.py
│   └── database.py          # SQLite 数据库操作层
├── ui/
│   ├── __init__.py
│   ├── floating_panel.py    # 主窗口（标题栏、标签、布局）
│   ├── todo_widget.py       # 待办组件（列表、输入、全部待办）
│   └── settings_dialog.py   # 字体设置对话框
└── dist/
    └── TodoFloat.exe        # 打包输出
```

## 数据存储

| 内容 | 路径 |
|------|------|
| 数据库 | `%APPDATA%\TodoFloat\todo.db` |
| 设置文件 | `%APPDATA%\TodoFloat\settings.json` |

即 `C:\Users\<用户名>\AppData\Roaming\TodoFloat\`

## 使用说明

### 基本操作

| 操作 | 说明 |
|------|------|
| 拖动标题栏 | 移动窗口位置 |
| 拖动右下角 | 调整窗口大小 |
| ▲ / ▼ 按钮 | 折叠/展开窗口 |
| ✕ 按钮 | 最小化到系统托盘 |
| ⚙ 按钮 | 打开字体设置 |

### 添加待办

1. 在底部输入框输入内容（支持多行，Enter 提交，Shift+Enter 换行）
2. 选择优先级：紧急 / 一般
3. 点击「+ 添加」或按 Enter 键确认

### 查看历史

- 点击 ◀ / ▶ 切换前后日期
- 点击日期文字打开日历选择器，可跳转到任意日期

### 全部待办

- 切换到「全部待办」标签查看所有日期的待办
- 点击「未完成」/「全部」按钮切换筛选模式

### 系统托盘

- 点击 ✕ 隐藏窗口到托盘
- 单击托盘图标重新显示窗口
- 右键托盘图标选择「退出」关闭程序

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 运行环境 |
| PyQt6 | ≥6.4.0 | GUI 框架 |
| SQLite3 | 内置 | 本地数据库 |
| PyInstaller | ≥5.0 | 打包为 exe |

## 开发说明

### 数据库结构

```sql
CREATE TABLE todos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    date        TEXT    NOT NULL,  -- 格式: YYYY-MM-DD
    priority    TEXT    NOT NULL,  -- 'urgent' | 'normal'
    completed   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL
);
```

### 单实例机制

使用 Windows 命名互斥体（Named Mutex）实现：

```python
handle = ctypes.windll.kernel32.CreateMutexW(None, True, "TodoFloat_SingleInstance_Mutex")
if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
    sys.exit(0)
```

## License

MIT
