import sqlite3
import sys
import os

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

def create_tables():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS order_info")
    cursor.execute("DROP TABLE IF EXISTS tee_info")
    cursor.execute("DROP TABLE IF EXISTS message_info")
    cursor.execute("DROP TABLE IF EXISTS conduit_info")

    # SQL statements to create tables
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS order_info (
          _id INTEGER PRIMARY KEY AUTOINCREMENT,
          order_id varchar(255) DEFAULT NULL,
          order_time varchar(255) DEFAULT NULL,
          remarks varchar(255) DEFAULT NULL,
          today_id varchar(255) DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS tee_info (
          _id INTEGER PRIMARY KEY AUTOINCREMENT,
          order_id varchar(255) DEFAULT NULL,
          product_id varchar(255) DEFAULT NULL,
          product_name varchar(255) DEFAULT NULL,
          product_sugar varchar(255) DEFAULT NULL,
          product_quantity varchar(255) DEFAULT NULL,
          product_ice varchar(255) DEFAULT NULL,
          product_simp varchar(255) DEFAULT NULL,
          unit_price varchar(255) DEFAULT NULL,
          num_tee varchar(255) DEFAULT NULL,
          state varchar(255) DEFAULT NULL,
          recipe varchar(255) DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS message_info (
          _id INTEGER PRIMARY KEY AUTOINCREMENT,
          message_id varchar(255) DEFAULT NULL,
          message_type varchar(255) DEFAULT NULL,
          message_level varchar(255) DEFAULT NULL,
          message_content varchar(255) DEFAULT NULL,
          time varchar(255) DEFAULT NULL
        );
        
        CREATE TABLE IF NOT EXISTS conduit_info (
              _id INTEGER PRIMARY KEY AUTOINCREMENT,
              conduit varchar(255) DEFAULT NULL,
              margin varchar(255) DEFAULT NULL,
              max_capacity varchar(255) DEFAULT NULL,
              conduit_type varchar(255) DEFAULT NULL,
              name varchar(255) DEFAULT NULL,
              shield varchar(255) DEFAULT NULL,
              begin_time varchar(255) DEFAULT NULL,
              effective_time varchar(255) DEFAULT NULL,
              red_warning_value varchar(255) DEFAULT NULL,
              yellow_warning_value varchar(255) DEFAULT NULL
            );
        CREATE TABLE IF NOT EXISTS maketee_conduit_info (
              _id INTEGER PRIMARY KEY AUTOINCREMENT,
              conduit            varchar(255) DEFAULT NULL,   -- 通道编号/槽位
              margin             varchar(255) DEFAULT NULL,   -- 剩余量
              max_capacity       varchar(255) DEFAULT NULL,   -- 容量
              conduit_type       varchar(255) DEFAULT NULL,   -- 类型
              name               varchar(255) DEFAULT NULL,   -- 物料名称
              shield             varchar(255) DEFAULT NULL,   -- 屏蔽 1/2
              begin_time         varchar(255) DEFAULT NULL,   -- 启用时间
              effective_time     varchar(255) DEFAULT NULL,   -- 有效期
              red_warning_value  varchar(255) DEFAULT NULL,   -- 红色预警阈值
              yellow_warning_value varchar(255) DEFAULT NULL  -- 黄色预警阈值
            );
    ''')


    # cursor.execute("DROP TABLE IF EXISTS conduit_info")

    # cursor.executescript('''
    #         CREATE TABLE IF NOT EXISTS conduit_info (
    #           _id INTEGER PRIMARY KEY AUTOINCREMENT,
    #           conduit varchar(255) DEFAULT NULL,
    #           margin varchar(255) DEFAULT NULL,
    #           max_capacity varchar(255) DEFAULT NULL,
    #           conduit_type varchar(255) DEFAULT NULL,
    #           name varchar(255) DEFAULT NULL,
    #           shield varchar(255) DEFAULT NULL,
    #           begin_time varchar(255) DEFAULT NULL,
    #           effective_time varchar(255) DEFAULT NULL,
    #           red_warning_value varchar(255) DEFAULT NULL,
    #           yellow_warning_value varchar(255) DEFAULT NULL
    #         );
    #
    #     ''')

    # cursor.execute("DROP TABLE IF EXISTS tee_info")
    # cursor.executescript('''
    #     CREATE TABLE IF NOT EXISTS tee_info (
    #       _id INTEGER PRIMARY KEY AUTOINCREMENT,
    #       order_id varchar(255) DEFAULT NULL,
    #       product_id varchar(255) DEFAULT NULL,
    #       product_name varchar(255) DEFAULT NULL,
    #       product_sugar varchar(255) DEFAULT NULL,
    #       product_quantity varchar(255) DEFAULT NULL,
    #       product_ice varchar(255) DEFAULT NULL,
    #       product_simp varchar(255) DEFAULT NULL,
    #       unit_price varchar(255) DEFAULT NULL,
    #       num_tee varchar(255) DEFAULT NULL,
    #       state varchar(255) DEFAULT NULL,
    #       recipe varchar(255) DEFAULT NULL
    #     );
    # ''')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # Create tables
    create_tables()

