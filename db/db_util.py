import sys
import os
import sqlite3, threading
from datetime import datetime

##对数据库操作可以在这里建立函数，在外面调用函数去操作

db_lock = threading.Lock()

def resource_path(relative_path):
    """ 获取资源的绝对路径 """
    if hasattr(sys, '_MEIPASS'):
        # 打包后的运行环境
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

db_path = resource_path('tee_data.db')

# db_util.py

def insert_order_info(order_id, order_time, remarks, today_id, state='3'):
    """插入一条订单，并返回自增主键 _id。"""
    with db_lock:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            sql = """
            INSERT INTO order_info (order_id, order_time, remarks, today_id, state)
            VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (order_id, order_time, remarks, today_id, state))
            conn.commit()
            return cursor.lastrowid      # ← 关键：回填自增ID
        except sqlite3.Error as e:
            print(f"插入 order_info 出错: {e}")
            return None
        finally:
            cursor.close(); conn.close()


def insert_tee_info(order_id, product_id, product_name, product_sugar, product_quantity,
                    product_ice, product_simp, unit_price, num_tee, state, recipe):
    """插入一条奶茶行，并返回自增主键 _id。"""
    with db_lock:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            sql = """
            INSERT INTO tee_info (order_id, product_id, product_name, product_sugar,
                                  product_quantity, product_ice, product_simp,
                                  unit_price, num_tee, state, recipe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (order_id, product_id, product_name, product_sugar,
                                 product_quantity, product_ice, product_simp,
                                 unit_price, num_tee, state, recipe))
            conn.commit()
            return cursor.lastrowid      # ← 关键：回填自增ID
        except sqlite3.Error as e:
            print(f"插入 tee_info 出错: {e}")
            return None
        finally:
            cursor.close(); conn.close()


# def insert_message_info(_id, message_id, message_type, message_level, message_content, time):
#     """
#     向 tee_info 表插入一条记录。

#     参数:
#         _id (str): 主键 ID。
#         message_id (str): 消息编号，例如 "MSG001"。
#         message_type (str): 消息类型，例如 "设备故障"。
#         message_level (str): 消息级别，例如 "红色"。
#         message_content (str): 消息内容，例如 "设备无响应，请检查设备。"。
#         time (str): 时间戳，格式为 "YYYY-MM-DD HH:MM:SS"。

#     返回:
#         bool: 插入成功返回 True，失败返回 False。
#     """
#     with db_lock:  # 加锁确保线程安全
#         conn = sqlite3.connect(db_path)
#         cursor = conn.cursor()

#         try:
#             sql = """
#             INSERT INTO tee_info (_id, message_id, message_type, message_level, message_content, time)
#             VALUES (?, ?, ?, ?, ?, ?)
#             """
#             cursor.execute(sql, (_id, message_id, message_type, message_level, message_content, time))
#             conn.commit()
#             print(f"成功插入记录: _id={_id}, message_id={message_id}, time={time}")
#             return True
#         except sqlite3.Error as e:
#             print(f"插入 tee_info 出错: {e}")
#             return False
#         finally:
#             cursor.close()
#             conn.close()
def insert_message_info(message_id, message_type, message_level, message_content, time):
    """
    向 message_info 表插入一条记录。

    参数:
        _id (str): 主键 ID。
        message_id (str): 消息编号，例如 "MSG001"。
        message_type (str): 消息类型，例如 "设备故障"。
        message_level (str): 消息级别，例如 "红色"。
        message_content (str): 消息内容，例如 "设备无响应，请检查设备。"。
        time (str): 时间戳，格式为 "YYYY-MM-DD HH:MM:SS"。

    返回:
        bool: 插入成功返回 True，失败返回 False。
    """
    with db_lock:  # 加锁确保线程安全
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            sql = """
            INSERT INTO message_info (message_id, message_type, message_level, message_content, time)
            VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (message_id, message_type, message_level, message_content, time))
            conn.commit()
            print(f"成功插入记录:message_id={message_id}, time={time}")
            return True
        except sqlite3.Error as e:
            print(f"插入 message_info 出错: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

def query_today_order_count():
    """
    查询指定表中当日订单的数量。

    返回:
        int: 当日订单数量。
    """
    with db_lock:  # 加锁确保线程安全
        # 获取当前日期
        today_date = datetime.now().strftime('%Y%m%d')  # 格式为 YYYYMMDD

        # 创建数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 构建查询语句，匹配以 "OYYYYMMDD" 开头的 order_id
        sql = "SELECT COUNT(*) FROM order_info WHERE order_id LIKE ?"

        try:
            # 执行查询，匹配 'O20241218%'
            cursor.execute(sql, (f"O{today_date}%",))
            result = cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            print(f"数据库查询出错: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()

def query_today_max_product_no() -> int:
    """
    返回“今天所有杯子 product_id（形如 P0001）的最大数字部分”，没有则返回 0。
    通过 tee_info 与 order_info 的 order_id 关联，并以 order_info.order_time 过滤今天。
    """
    with db_lock:
        import sqlite3
        from datetime import datetime
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            today = datetime.now().strftime("%Y-%m-%d")   # 与你现有 LIKE 'YYYY-MM-DD%' 保持一致
            sql = """
            SELECT COALESCE(MAX(
                CAST(
                    CASE
                        WHEN SUBSTR(t.product_id,1,1)='P' THEN
                            CASE
                                WHEN INSTR(t.product_id,'-') > 0 THEN SUBSTR(t.product_id, 2, INSTR(t.product_id,'-') - 2)
                                ELSE SUBSTR(t.product_id, 2)
                            END
                        ELSE t.product_id
                    END AS INTEGER)
            ), 0)
            FROM tee_info t
            JOIN order_info o ON o.order_id = t.order_id
            WHERE o.order_time LIKE ?
            """
            cursor.execute(sql, (f"{today}%",))
            row = cursor.fetchone()
            print(f"[DB] max P today -> {int(row[0]) if row and row[0] is not None else 0}")   # ★ 新增
            return int(row[0]) if row and row[0] is not None else 0
        except sqlite3.Error as e:
            print(f"[DB] query_today_max_product_no error: {e}")
            return 0
        finally:
            cursor.close(); conn.close()
        


def query_today_tea_quantity():
    """
    查询今日奶茶总数量（根据 order_info 表中的今日订单）。
    返回:
        int: 今日奶茶总数量。
    """
    with db_lock:  # 加锁确保线程安全
        # 获取当前日期
        today_date = datetime.now().strftime('%Y-%m-%d')  # 格式: 2024-12-18

        # 创建数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # 查询当日订单的 order_id
            sql_orders = """
            SELECT order_id
            FROM order_info
            WHERE order_time LIKE ?
            """
            cursor.execute(sql_orders, (f"{today_date}%",))  # 匹配日期开头（包含时间）
            order_ids = cursor.fetchall()
            # print(f'order_ids:{order_ids}')
            if not order_ids:
                return 0  # 如果没有当日订单，返回 0

            # 提取 order_id 列表
            order_ids = [row[0] for row in order_ids]

            # 构建查询 tee_info 表奶茶总数的 SQL
            sql_tea_quantity = f"""
            SELECT COUNT(*) 
            FROM tee_info
            WHERE order_id IN ({','.join(['?'] * len(order_ids))})
            """
            # 查询总奶茶数量
            cursor.execute(sql_tea_quantity, order_ids)
            result = cursor.fetchone()
            return result[0] if result and result[0] else 0  # 如果结果为空或为 NULL，返回 0
        except sqlite3.Error as e:
            print(f"数据库查询出错: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()


def query_products_by_tee_state(state):
    """
    查询 order_info 表中 state = '3' 的 order_id，
    并在 tee_info 表中查询所有关联的产品信息，按默认 ID 升序排序。

    返回:
        list: 包含所有关联产品的字典列表。
    """
    with db_lock:  # 加锁确保线程安全
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            # 查询 tee_info 表中所有关联的产品信息，按 ID 升序排序
            sql_products = f"""
                    SELECT * FROM tee_info
                    WHERE state = ?
                    """
            cursor.execute(sql_products, (state,))
            products = cursor.fetchall()
            # 将结果转换为字典列表
            columns = [desc[0] for desc in cursor.description]  # 获取列名
            result = [dict(zip(columns, row)) for row in products]

            return result
        except sqlite3.Error as e:
            print(f"查询出错: {e}")
            return []
        finally:
            cursor.close()
            conn.close()


def query_all_order_info():
    """
    查询 order_info 表中所有信息。

    返回:
        list: 包含所有订单信息的字典列表。
    """
    with db_lock:  # 加锁确保线程安全
        # 创建数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 构建查询语句
        sql = "SELECT * FROM order_info"

        try:
            # 执行查询
            cursor.execute(sql)
            rows = cursor.fetchall()

            # 获取列名
            columns = [desc[0] for desc in cursor.description]

            # 转换结果为字典列表
            result = [dict(zip(columns, row)) for row in rows]
            return result
        except sqlite3.Error as e:
            print(f"数据库查询出错: {e}")
            return []
        finally:
            cursor.close()
            conn.close()


def query_tee_info_by_state_1_or_4():
    """
    查询 order_info 表中所有信息。

    返回:
        list: 包含所有订单信息的字典列表。
    """
    with db_lock:  # 加锁确保线程安全
        # 创建数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 构建查询语句
        sql = "SELECT * FROM tee_info WHERE state = '1' or state = '4'"

        try:
            # 执行查询
            cursor.execute(sql)
            rows = cursor.fetchall()

            # 获取列名
            columns = [desc[0] for desc in cursor.description]

            # 转换结果为字典列表
            result = [dict(zip(columns, row)) for row in rows]
            return result
        except sqlite3.Error as e:
            print(f"数据库查询出错: {e}")
            return []
        finally:
            cursor.close()
            conn.close()


def query_all_tee_info():
    """
    查询 order_info 表中所有信息。

    返回:
        list: 包含所有订单信息的字典列表。
    """
    with db_lock:  # 加锁确保线程安全
        # 创建数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 构建查询语句
        sql = "SELECT * FROM tee_info"

        try:
            # 执行查询
            cursor.execute(sql)
            rows = cursor.fetchall()

            # 获取列名
            columns = [desc[0] for desc in cursor.description]

            # 转换结果为字典列表
            result = [dict(zip(columns, row)) for row in rows]
            return result
        except sqlite3.Error as e:
            print(f"数据库查询出错: {e}")
            return []
        finally:
            cursor.close()
            conn.close()


def query_tee_info_by_state_4():
    """
    查询 order_info 表中所有信息。

    返回:
        list: 包含所有订单信息的字典列表。
    """
    with db_lock:  # 加锁确保线程安全
        # 创建数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 构建查询语句
        sql = "SELECT * FROM tee_info WHERE state = '4'"

        try:
            # 执行查询
            cursor.execute(sql)
            rows = cursor.fetchall()

            # 获取列名
            columns = [desc[0] for desc in cursor.description]

            # 转换结果为字典列表
            result = [dict(zip(columns, row)) for row in rows]
            return result
        except sqlite3.Error as e:
            print(f"数据库查询出错: {e}")
            return []
        finally:
            cursor.close()
            conn.close()


def query_state_by_order_id(order_id):
    """
    根据指定的 order_id 查询 order_info 表中的 state 值。

    参数:
        order_id (str): 要查询的订单 ID。

    返回:
        str: 对应的 state 值，如果未找到则返回 None。
    """
    with db_lock:  # 加锁确保线程安全
        # 创建数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # 构建 SQL 查询语句
            sql = "SELECT state FROM order_info WHERE order_id = ?"

            # 执行查询
            cursor.execute(sql, (order_id,))
            result = cursor.fetchone()

            # 返回 state 值，如果未找到则返回 None
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"数据库查询出错: {e}")
            return None
        finally:
            cursor.close()
            conn.close()


def query_today_id_by_order_id(order_id):
    """
    根据指定的 order_id 查询 order_info 表中的 today_id 值。

    参数:
        order_id (str): 要查询的订单 ID。

    返回:
        str: 对应的 state 值，如果未找到则返回 None。
    """
    with db_lock:  # 加锁确保线程安全
        # 创建数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # 构建 SQL 查询语句
            sql = "SELECT today_id FROM order_info WHERE order_id = ?"

            # 执行查询
            cursor.execute(sql, (order_id,))
            result = cursor.fetchone()

            # 返回 state 值，如果未找到则返回 None
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"数据库查询出错: {e}")
            return None
        finally:
            cursor.close()
            conn.close()


def query_order_time_by_order_id(order_id):
    """
    根据指定的 order_id 查询 order_info 表中的 order_time 值。

    参数:
        order_id (str): 要查询的订单 ID。

    返回:
        str: 对应的 state 值，如果未找到则返回 None。
    """
    with db_lock:  # 加锁确保线程安全
        # 创建数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # 构建 SQL 查询语句
            sql = "SELECT order_time FROM order_info WHERE order_id = ?"

            # 执行查询
            cursor.execute(sql, (order_id,))
            result = cursor.fetchone()

            # 返回 state 值，如果未找到则返回 None
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"数据库查询出错: {e}")
            return None
        finally:
            cursor.close()
            conn.close()


def query_all_message_info():
    """
    查询 order_info 表中所有信息。

    返回:
        list: 包含所有订单信息的字典列表。
    """
    with db_lock:  # 加锁确保线程安全
        # 创建数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 构建查询语句
        sql = "SELECT * FROM message_info"

        try:
            # 执行查询
            cursor.execute(sql)
            rows = cursor.fetchall()

            # 获取列名
            columns = [desc[0] for desc in cursor.description]

            # 转换结果为字典列表
            result = [dict(zip(columns, row)) for row in rows]
            return result
        except sqlite3.Error as e:
            print(f"数据库查询出错: {e}")
            return []
        finally:
            cursor.close()
            conn.close()


def query_all_conduit_info():
    """
    查询 order_info 表中所有信息。
    返回:
        list: 包含所有订单信息的字典列表。
    """
    with db_lock:  # 加锁确保线程安全
        # 创建数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # 构建查询语句
        sql = "SELECT * FROM conduit_info"
        try:
            # 执行查询
            cursor.execute(sql)
            rows = cursor.fetchall()
            # 获取列名
            columns = [desc[0] for desc in cursor.description]
            # 转换结果为字典列表
            result = [dict(zip(columns, row)) for row in rows]
            return result
        except sqlite3.Error as e:
            print(f"数据库查询出错: {e}")
            return []
        finally:
            cursor.close()
            conn.close()


def insert_xlsx_conduit_bean_to_conduit_info(conduit_bean):
    """
            将xlsx中管道信息插入数据库中
        返回:
            bool: 插入成功返回 True，失败返回 False。
        """
    with db_lock:  # 加锁确保线程安全
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            current_time = datetime.now()
            begin_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
            sql = """
                INSERT INTO conduit_info (conduit, margin, max_capacity, conduit_type, name, shield, begin_time, effective_time, red_warning_value, yellow_warning_value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
            cursor.execute(sql, (
                str(conduit_bean.conduit),
                str(conduit_bean.margin),
                str(conduit_bean.max_capacity),
                str(conduit_bean.conduit_type),
                str(conduit_bean.name),
                '1',
                begin_time,
                str(conduit_bean.effective_time),
                str(conduit_bean.red_warning_value),
                str(conduit_bean.yellow_warning_value)))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"插入 conduit_info 出错: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

def update_conduit_info(_id, conduit_type, name, shield, effective_time, begin_time, red_warning_value, yellow_warning_value):
    """
    根据提供的数据更新 conduit_info 表中的记录。

    :param _id: 要更新的记录的主键 ID。
    :param conduit_type: 管道类型。
    :param name: 管道名称。
    :param shield: 保护状态，'1' 或 '2'。
    :param effective_time: 生效时间。
    :param begin_time: 开始时间。
    :param red_warning_value: 红色警告值。
    :param yellow_warning_value: 黄色警告值。
    """
    with db_lock:  # 加锁确保线程安全
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # 动态生成 SQL 语句
            sql = '''
                UPDATE conduit_info
                SET conduit_type = ?, 
                    name = ?, 
                    shield = ?, 
                    effective_time = ?, 
                    begin_time = ?, 
                    red_warning_value = ?, 
                    yellow_warning_value = ?
                WHERE _id = ?
            '''

            # 执行更新操作
            cursor.execute(sql, (conduit_type, name, shield, effective_time, begin_time, red_warning_value, yellow_warning_value, _id))
            conn.commit()

            # 检查是否成功更新
            if cursor.rowcount > 0:
                print(f"成功更新了 _id 为 {_id} 的记录。")
            else:
                print(f"_id 为 {_id} 的记录不存在，未更新任何数据。")
        except sqlite3.Error as e:
            print("更新 conduit_info 出错:", e)
        finally:
            cursor.close()
            conn.close()


def update_conduit_margin_info(_id, margin):
    """
    根据提供的数据更新 conduit_info 表中的记录。
    :param margin: 要更新的剩余量。
    """
    with db_lock:  # 加锁确保线程安全
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            # 动态生成 SQL 语句
            sql = '''
                UPDATE conduit_info
                SET margin = ?
                WHERE _id = ?
            '''
            # 执行更新操作
            cursor.execute(sql, (margin, int(_id)))
            conn.commit()
        except sqlite3.Error as e:
            print("更新 conduit_margin 出错:", e)
        finally:
            cursor.close()
            conn.close()

def update_conduit_multiple_margin_info(data_list):
    with db_lock:
        conn = sqlite3.connect(db_path, timeout=10.0)
        try:
            cursor = conn.cursor()
            sql = "UPDATE conduit_info SET margin = ? WHERE _id = ?"
            cursor.executemany(sql, data_list)
            conn.commit()
        except sqlite3.Error as e:
            print("更新 conduit_multiple_margin 出错:", e)
        finally:
            cursor.close()
            conn.close()

def update_begin_time_info(_id):
    """
    更新 conduit_info 表的 begin_time 为当前时间。
    :param _id: 要更新的记录的主键 ID。
    """
    # 获取当前时间
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with db_lock:  # 使用线程锁，确保线程安全
        conn = sqlite3.connect(db_path, timeout=10.0)
        try:
            cursor = conn.cursor()
            sql = '''
                UPDATE conduit_info
                SET begin_time = ?
                WHERE _id = ?
            '''
            cursor.execute(sql, (current_time, int(_id)))
            conn.commit()
        except sqlite3.Error as e:
            print("更新 begin_time 出错:", e)
        finally:
            cursor.close()
            conn.close()

def update_tee_info_state_by_id(_id, state):
    """
    根据提供的数据更新 tee_info 表中的记录。
    :param _id: 要更新的记录的主键 ID。
    :param state: 要更新的状态值。
    """
    with db_lock:  # 加锁确保线程安全
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # 动态生成 SQL 语句
            sql = '''
                UPDATE tee_info
                SET state = ? 
                WHERE _id = ?
            '''
            # 执行更新操作
            cursor.execute(sql, (state, int(_id)))  # 确保顺序正确
            conn.commit()
            # 检查是否成功更新
            if cursor.rowcount > 0:
                print(f"成功更新了 _id 为 {_id} 的记录，新的 state 为 {state}。")
            else:
                print(f"_id 为 {_id} 的记录不存在，未更新任何数据。")
        except sqlite3.Error as e:
            print("更新 tee_info 出错:", e)
        finally:
            cursor.close()
            conn.close()

def clear_tee_info_state_by_id(_id, state):
    """
    根据指定的 _id 和 state 删除 tee_info 表中的记录。

    :param _id: 要删除的记录的主键 ID。
    :param state: 要匹配的状态值。
    """
    with db_lock:  # 加锁确保线程安全
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # 构建 SQL 删除语句
            sql = '''
                DELETE FROM tee_info
                WHERE _id = ? AND state = ?
            '''
            # 执行删除操作
            cursor.execute(sql, (int(_id), state))  # 参数化查询，防止 SQL 注入
            conn.commit()
            
            # 检查是否成功删除
            if cursor.rowcount > 0:
                print(f"成功清除了 _id 为 {_id} 且 state 为 {state} 的记录。")
            else:
                print(f"没有找到 _id 为 {_id} 且 state 为 {state} 的记录，未删除任何数据。")
        except sqlite3.Error as e:
            print("清除 tee_info 数据时出错:", e)
        finally:
            cursor.close()
            conn.close()

def clear_tee_info(condition=None):
    """
    清除 tee_info 表中的数据，可以选择清除全部数据或根据条件清除。
    :param condition: 可选，指定清除条件的 SQL 片段。例如 "state = 1"。
                      如果未提供，则清除表中所有记录。
    """
    with db_lock:  # 加锁确保线程安全
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            if condition:
                # 根据条件删除数据
                sql = f'''
                    DELETE FROM tee_info
                    WHERE {condition}
                '''
            else:
                # 删除所有数据
                sql = '''
                    DELETE FROM tee_info
                '''
            cursor.execute(sql)
            conn.commit()
            print(f"清除了 {cursor.rowcount} 条记录。")
        except sqlite3.Error as e:
            print("清除 tee_info 数据时出错:", e)
        finally:
            cursor.close()
            conn.close()

def clear_order_info(condition=None):
    with db_lock:  # 加锁确保线程安全
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            if condition:
                # 根据条件删除数据
                sql = f'''
                    DELETE FROM order_info
                    WHERE {condition}
                '''
            else:
                # 删除所有数据
                sql = '''
                    DELETE FROM order_info
                '''
            cursor.execute(sql)
            conn.commit()
            print(f"清除了 {cursor.rowcount} 条记录。")
        except sqlite3.Error as e:
            print("清除 order_info 数据时出错:", e)
        finally:
            cursor.close()
            conn.close()

def clear_message_info(condition=None):
    with db_lock:  # 加锁确保线程安全
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            if condition:
                # 根据条件删除数据
                sql = f'''
                    DELETE FROM message_info
                    WHERE {condition}
                '''
            else:
                # 删除所有数据
                sql = '''
                    DELETE FROM message_info
                '''
            cursor.execute(sql)
            conn.commit()
            print(f"清除了 {cursor.rowcount} 条记录。")
        except sqlite3.Error as e:
            print("清除 message_info 数据时出错:", e)
        finally:
            cursor.close()
            conn.close()
def clear_conduit_info(condition=None):
    with db_lock:  # 加锁确保线程安全
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            if condition:
                # 根据条件删除数据
                sql = f'''
                    DELETE FROM conduit_info
                    WHERE {condition}
                '''
            else:
                # 删除所有数据
                sql = '''
                    DELETE FROM conduit_info
                '''
            cursor.execute(sql)
            conn.commit()
            print(f"清除了 {cursor.rowcount} 条记录。")
        except sqlite3.Error as e:
            print("清除 conduit_info 数据时出错:", e)
        finally:
            cursor.close()
            conn.close()

def get_next_message_id():
    """
    获取下一个递增的 message_id。

    返回:
        str: 下一个 message_id，格式为 MSGxxx（xxx 是三位数字）
    """
    with db_lock:  # 加锁确保线程安全
        # 创建数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 创建 message_info 表（如果不存在）
        create_table_sql = '''
            CREATE TABLE IF NOT EXISTS message_info (
                message_id TEXT PRIMARY KEY,
                message_type TEXT,
                message_level TEXT,
                message_content TEXT,
                time TEXT
            )
        '''
        cursor.execute(create_table_sql)

        # 构建查询语句，查询当前最大的 message_id 编号
        sql = "SELECT MAX(SUBSTR(message_id, 4)) FROM message_info"

        try:
            # 执行查询
            cursor.execute(sql)
            result = cursor.fetchone()[0]
            if result is None:
                next_id = 1
            else:
                next_id = int(result) + 1
            return f"MSG{next_id:03d}"
        except sqlite3.Error as e:
            print(f"数据库查询出错: {e}")
            return "MSG001"
        finally:
            cursor.close()
            conn.close()

if __name__ == '__main__':
    # print(f'today_id = {query_today_order_count()}')
    # print(f'today_product_id = {query_today_tea_quantity()}')
    #
    # print(f'query_all_order_info = {query_all_order_info()}')
    print(f'query_all_tee_info = {query_all_tee_info()}')
    update_tee_info_state_by_id('44', '2')
    print(f'query_all_tee_info = {query_all_tee_info()}')
    # print(f'query_all_conduit_info = {query_all_conduit_info()}')

def update_conduit_material_by_conduit(conduit: str, name: str, margin: str = None, reset_begin_time: bool = True):
    """
    根据 conduit（如 'P1001'）更新材料名称 name；
    可选：重置 margin（不想改就传 None）、刷新 begin_time 为当前时间。
    """
    from datetime import datetime
    with db_lock:
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            sets = ["name = ?"]
            params = [str(name)]
            if margin is not None:
                sets.append("margin = ?")
                params.append(str(margin))
            if reset_begin_time:
                sets.append("begin_time = ?")
                params.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            sql = f"UPDATE conduit_info SET {', '.join(sets)} WHERE conduit = ?"
            params.append(str(conduit))
            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print("更新 conduit_info 材料 出错:", e)
            return False
        finally:
            cursor.close()
            conn.close()


            
# ========= 泡茶页专用：maketee_conduit_info =========

def query_all_maketee_conduit_info():
    """读取泡茶页通道信息（含 expect_time）"""
    with db_lock:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            sql = """
            SELECT _id, conduit, expect_time, temp_goal, ice_coefficient, name,
                   tea_coefficient, begin_time, effective_time, red_warning_value, yellow_warning_value
            FROM maketee_conduit_info
            ORDER BY _id
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in rows]
        except sqlite3.Error as e:
            print(f"[DB] query_all_maketee_conduit_info error: {e}")
            return []
        finally:
            cursor.close(); conn.close()

def insert_maketee_conduit(conduit, margin, max_capacity, conduit_type, name,
                           shield, begin_time, effective_time, red_warning_value, yellow_warning_value):
    with db_lock:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            sql = """INSERT INTO maketee_conduit_info
                     (conduit, margin, max_capacity, conduit_type, name, shield, begin_time, effective_time, red_warning_value, yellow_warning_value)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            cursor.execute(sql, (str(conduit), str(margin), str(max_capacity), str(conduit_type),
                                 str(name), str(shield), str(begin_time), str(effective_time),
                                 str(red_warning_value), str(yellow_warning_value)))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print("插入 maketee_conduit_info 出错:", e)
            return None
        finally:
            cursor.close(); conn.close()


def update_maketee_conduit_info(_id, conduit_type=None, name=None, shield=None,
                                effective_time=None, begin_time=None,
                                red_warning_value=None, yellow_warning_value=None):
    with db_lock:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            sets, params = [], []
            if conduit_type is not None:      sets += ["conduit_type=?"];          params += [str(conduit_type)]
            if name is not None:              sets += ["name=?"];                  params += [str(name)]
            if shield is not None:            sets += ["shield=?"];                params += [str(shield)]
            if effective_time is not None:    sets += ["effective_time=?"];        params += [str(effective_time)]
            if begin_time is not None:        sets += ["begin_time=?"];            params += [str(begin_time)]
            if red_warning_value is not None: sets += ["red_warning_value=?"];     params += [str(red_warning_value)]
            if yellow_warning_value is not None: sets += ["yellow_warning_value=?"]; params += [str(yellow_warning_value)]
            if not sets:
                return False
            sql = f"UPDATE maketee_conduit_info SET {', '.join(sets)} WHERE _id=?"
            params.append(int(_id))
            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print("更新 maketee_conduit_info 出错:", e)
            return False
        finally:
            cursor.close(); conn.close()


def update_maketee_conduit_margin(_id, margin):
    with db_lock:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE maketee_conduit_info SET margin=? WHERE _id=?", (str(margin), int(_id)))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print("更新 maketee_conduit_info.margin 出错:", e)
            return False
        finally:
            cursor.close(); conn.close()


def clear_maketee_conduit_info(condition=None):
    with db_lock:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            if condition:
                cursor.execute(f"DELETE FROM maketee_conduit_info WHERE {condition}")
            else:
                cursor.execute("DELETE FROM maketee_conduit_info")
            conn.commit()
            return True
        except sqlite3.Error as e:
            print("清除 maketee_conduit_info 出错:", e)
            return False
        finally:
            cursor.close(); conn.close()


def update_maketee_conduit_material_by_conduit(conduit: str, name: str, margin: str = None, reset_begin_time: bool = True):
    """ 通过 conduit 更新泡茶物料名称/剩余量，可选重置 begin_time """
    from datetime import datetime
    with db_lock:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            sets, params = ["name=?"], [str(name)]
            if margin is not None:
                sets += ["margin=?"]; params += [str(margin)]
            if reset_begin_time:
                sets += ["begin_time=?"]; params += [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
            sql = f"UPDATE maketee_conduit_info SET {', '.join(sets)} WHERE conduit=?"
            params.append(str(conduit))
            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print("更新 maketee_conduit_info 材料 出错:", e)
            return False
        finally:
            cursor.close(); conn.close()
def get_conn():
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row    # ★ 关键
    return conn






