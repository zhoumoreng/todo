from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QPushButton, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QFontDatabase


# 推荐字体列表（中文友好）
FONT_CANDIDATES = [
    "Microsoft YaHei", "微软雅黑",
    "SimSun", "宋体",
    "SimHei", "黑体",
    "KaiTi", "楷体",
    "FangSong", "仿宋",
    "Arial", "Segoe UI", "Tahoma", "Verdana",
]


def get_available_fonts() -> list[str]:
    all_fonts = QFontDatabase.families()  # PyQt6 静态方法，无需实例化
    result = []
    seen = set()
    # 先放推荐字体（只加系统中存在的）
    for f in FONT_CANDIDATES:
        if f in all_fonts and f not in seen:
            result.append(f)
            seen.add(f)
    return result if result else ["Arial"]


class SettingsDialog(QDialog):
    font_changed = pyqtSignal(str, int)  # family, size

    def __init__(self, current_family: str, current_size: int, parent=None):
        super().__init__(parent)
        self._family = current_family
        self._size = current_size
        self.setWindowTitle("字体设置")
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setFixedWidth(320)
        self.setStyleSheet("""
            QDialog {
                background: #F8F9FB;
            }
            QLabel {
                color: #2D3748;
                font-size: 12px;
            }
            QComboBox, QSpinBox {
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 5px 10px;
                background: white;
                color: #2D3748;
                font-size: 12px;
            }
            QComboBox:focus, QSpinBox:focus {
                border-color: #5B8AF5;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 字体系列
        layout.addWidget(QLabel("字体"))
        self.font_combo = QComboBox()
        fonts = get_available_fonts()
        for f in fonts:
            self.font_combo.addItem(f)
        idx = self.font_combo.findText(self._family)
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)
        self.font_combo.currentTextChanged.connect(self._on_change)
        layout.addWidget(self.font_combo)

        # 字号
        layout.addWidget(QLabel("字号（pt）"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 18)
        self.size_spin.setValue(self._size)
        self.size_spin.setSuffix(" pt")
        self.size_spin.valueChanged.connect(self._on_change)
        layout.addWidget(self.size_spin)

        # 预览
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #E8ECF0;")
        layout.addWidget(line)

        preview_label = QLabel("预览")
        preview_label.setStyleSheet("color: #718096; font-size: 11px;")
        layout.addWidget(preview_label)

        self.preview = QLabel("今天完成了重要的工作任务 ✓\n明天记得开会和提交报告！")
        self.preview.setWordWrap(True)
        self.preview.setStyleSheet("""
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 10px 12px;
            color: #2D3748;
        """)
        self._update_preview()
        layout.addWidget(self.preview)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 6px 18px;
                color: #4A5568;
                font-size: 12px;
            }
            QPushButton:hover { background: #F7FAFC; }
        """)
        cancel_btn.clicked.connect(self.reject)

        ok_btn = QPushButton("应用")
        ok_btn.setStyleSheet("""
            QPushButton {
                background: #5B8AF5;
                border: none;
                border-radius: 6px;
                padding: 6px 18px;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover { background: #4A7AE8; }
        """)
        ok_btn.clicked.connect(self._apply)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    def _on_change(self):
        self._family = self.font_combo.currentText()
        self._size = self.size_spin.value()
        self._update_preview()

    def _update_preview(self):
        font = QFont(self._family, self._size)
        self.preview.setFont(font)

    def _apply(self):
        self.font_changed.emit(self._family, self._size)
        self.accept()
