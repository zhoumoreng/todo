import sqlite3
import os
from datetime import datetime


def get_db_path():
    app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
    db_dir = os.path.join(app_data, 'TodoFloat')
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, 'todo.db')


def get_connection():
    return sqlite3.connect(get_db_path())


def init_db():
    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'normal',
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_date ON todos(date)')
        conn.commit()


def add_todo(title: str, date: str, priority: str = 'normal') -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            'INSERT INTO todos (title, date, priority, completed, created_at) VALUES (?, ?, ?, 0, ?)',
            (title, date, priority, datetime.now().isoformat())
        )
        conn.commit()
        return cursor.lastrowid


def get_todos_by_date(date: str) -> list[dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            'SELECT * FROM todos WHERE date = ? ORDER BY priority DESC, created_at ASC',
            (date,)
        )
        return [dict(row) for row in cursor.fetchall()]


def toggle_todo(todo_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute('SELECT completed FROM todos WHERE id = ?', (todo_id,))
        row = cursor.fetchone()
        if row is None:
            return False
        new_state = 0 if row[0] else 1
        conn.execute('UPDATE todos SET completed = ? WHERE id = ?', (new_state, todo_id))
        conn.commit()
        return bool(new_state)


def delete_todo(todo_id: int):
    with get_connection() as conn:
        conn.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
        conn.commit()


def get_all_todos(only_incomplete: bool = True) -> list[dict]:
    """返回所有待办，按日期倒序、优先级排序。only_incomplete=True 只返回未完成。"""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        if only_incomplete:
            cursor = conn.execute(
                'SELECT * FROM todos WHERE completed = 0 ORDER BY date DESC, priority DESC, created_at ASC'
            )
        else:
            cursor = conn.execute(
                'SELECT * FROM todos ORDER BY date DESC, priority DESC, created_at ASC'
            )
        return [dict(row) for row in cursor.fetchall()]


def get_dates_with_todos() -> list[str]:
    with get_connection() as conn:
        cursor = conn.execute('SELECT DISTINCT date FROM todos ORDER BY date DESC')
        return [row[0] for row in cursor.fetchall()]
