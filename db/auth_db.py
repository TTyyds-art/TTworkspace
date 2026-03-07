# db/auth_db.py
import os, sqlite3, sys

def resource_path(rel):
    # 开发环境：写到 db/ 目录；打包后：写到 exe 同级目录（可写）
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(__file__)
    return os.path.join(base, rel)

DB_PATH = resource_path("auth.db")
BOOK_TXT = resource_path("password_book.txt")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users(
                account  TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        """)
        c.execute("INSERT OR IGNORE INTO users(account,password) VALUES(?,?)",
                  ("xlzz123456", "123456"))
        conn.commit()
    sync_password_book()

def check_user(account: str, password: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE account=?", (account.strip(),))
        row = cur.fetchone()
        return (row is not None) and (row[0] == password)

# 插入/覆盖一个用户，并同步密码本
def add_user(account: str, password: str, overwrite: bool = True) -> str:
    account = account.strip()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        if overwrite:
            cur.execute("INSERT OR REPLACE INTO users(account,password) VALUES(?,?)",
                        (account, password))
        else:
            cur.execute("INSERT INTO users(account,password) VALUES(?,?)",
                        (account, password))
        conn.commit()
    return sync_password_book()

# 把 users 表完整导出成记事本（账号\t密码，每行一个）
def sync_password_book() -> str:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT account, password FROM users ORDER BY account").fetchall()
    with open(BOOK_TXT, "w", encoding="utf-8") as f:
        f.write("# 账号\t密码\n")
        for acc, pwd in rows:
            f.write(f"{acc}\t{pwd}\n")
    return BOOK_TXT

# ⬇⬇ 入口：直接运行本文件时会创建数据库并提示路径
if __name__ == "__main__":
    init_db()
    print("Auth DB created at:", DB_PATH)
