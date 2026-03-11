# TodoFloat 设计文档

## 项目概述

一个 Windows 桌面悬浮待办事项工具，打包为单个 `.exe`，始终置顶在屏幕右上角。支持今日待办展示、紧急/一般优先级、完成勾选、历史查看，数据存储于本地 SQLite。

---

## 技术栈

- **语言**：Python 3.x
- **UI 框架**：PyQt6
- **数据库**：SQLite3（Python 内置）
- **打包工具**：PyInstaller（单文件 exe）
- **主题**：浅色（白/浅灰底）

---

## 架构

单进程应用，4 个模块：

```
dbsx/
├── main.py                  # 入口：初始化 DB、启动 QApplication、显示面板
├── db/
│   └── database.py          # SQLite 封装，所有 CRUD 操作
├── ui/
│   ├── floating_panel.py    # 主窗口：置顶、拖拽、折叠/展开、缩放、系统托盘
│   └── todo_widget.py       # 待办列表区：日期切换、添加、勾选
└── build.spec               # PyInstaller 打包配置
```

数据流：UI 事件 → `database.py` → SQLite 文件（`%APPDATA%\TodoFloat\todo.db`）

---

## 数据模型

SQLite 单表 `todos`：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | 主键 |
| title | TEXT NOT NULL | 待办内容 |
| date | TEXT NOT NULL | 日期，格式 YYYY-MM-DD |
| priority | TEXT NOT NULL | `urgent`（紧急）/ `normal`（一般） |
| completed | INTEGER NOT NULL DEFAULT 0 | 0=未完成，1=已完成 |
| created_at | TEXT NOT NULL | 创建时间 ISO 格式 |

---

## UI 组件

### 悬浮面板（FloatingPanel）

- 启动定位：屏幕右上角，距边缘 10px
- 窗口标志：`FramelessWindowHint` + `WindowStaysOnTopHint` + `Tool`
- **标题栏**：
  - 左：应用名"待办清单"
  - 右：折叠按钮（▲/▼）+ 关闭按钮（关闭=隐藏到托盘）
  - 拖拽标题栏可移动窗口
- **折叠**：点击折叠按钮，面板高度收缩至标题栏（36px），再次点击展开
- **缩放**：右下角拖拽手柄，可自由缩放面板大小
- **默认尺寸**：360×500px，最小 280×200px

### 待办列表（TodoWidget）

- **顶部日期栏**：
  - `◀` 前一天 / 日期显示（点击弹出日期选择器）/ `▶` 后一天
  - 今天显示"今天 MM-DD"，其他日期显示"YYYY-MM-DD"
- **待办列表**：
  - 每项：复选框 + 内容文字 + 优先级标签
  - 优先级标签：红色背景"紧急" / 灰色背景"一般"
  - 已完成：文字加删除线，颜色变为浅灰
  - 支持右键删除
- **底部输入区**：
  - 文本输入框（占位符"添加待办..."）
  - 优先级下拉（一般 / 紧急）
  - "添加"按钮（或回车触发）

### 系统托盘

- 图标常驻系统托盘
- 右键菜单：显示面板 / 退出

---

## 关键行为

1. **置顶**：使用 `Qt.WindowType.WindowStaysOnTopHint`，始终在最上层
2. **开机启动**（可选，暂不实现）
3. **日期隔离**：每天的待办独立，切换日期查看历史
4. **数据持久化**：每次操作（添加/勾选/删除）立即写入 SQLite
5. **窗口记忆**：退出前保存窗口位置和大小，下次启动恢复

---

## 打包说明

使用 PyInstaller 生成单文件 exe：

```bash
pip install pyqt6 pyinstaller
pyinstaller --onefile --windowed --name TodoFloat main.py
```

生成文件：`dist/TodoFloat.exe`，无需安装，双击运行。
