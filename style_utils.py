class MenuStyle:
    weight_changed_style_1 = '''
        background-color:rgba(44,159,97,0.22);
        border-top-left-radius:5px;
        border-bottom-left-radius:5px;
        border: 1px solid rgb(21, 136, 74);
        color:rgb(20, 126, 69);
    '''
    weight_changed_style_2 = '''
        background-color:rgba(44,159,97,0.22);
        border-top-right-radius:5px;
        border-bottom-right-radius:5px;
        border-top: 1px solid rgb(21, 136, 74);
        border-bottom: 1px solid rgb(21, 136, 74);
        border-right: 1px solid rgb(21, 136, 74);
        color:rgb(255, 100, 100);
    '''
    weight_no_changed_style_1 = '''
        border-top-left-radius:5px;
        border-bottom-left-radius:5px;
        border: 1px solid rgb(169, 227, 196);
        color:rgb(20, 126, 69);
    '''
    weight_no_changed_style_2 = '''
        border-top-right-radius:5px;
        border-bottom-right-radius:5px;
        border-top: 1px solid rgb(169, 227, 196);
        border-bottom: 1px solid rgb(169, 227, 196);
        border-right: 1px solid rgb(169, 227, 196);
        color:rgb(255, 100, 100);
    '''
    sugar_changed_style = '''
        background-color:rgba(44,159,97,0.22);
        border-radius:5px;
        border: 1px solid rgb(21, 136, 74);
        color:rgb(20, 126, 69);
    '''
    sugar_no_changed_style = '''
        border-radius:5px;
        border: 1px solid rgb(169, 227, 196);
        color:rgb(20, 126, 69);
    '''
    mark_no_change_style = '''
        QWidget#label_widget{
            background-color:rgb(60, 211, 130);
            color:rgb(255, 255, 255);
            border-radius:19px;
            
        }
    '''
    mark_change_style = '''
        QWidget#label_widget{
            background-color:rgb(255, 255, 255);
            color:rgb(60, 211, 130);
            border-radius:19px;
        }
    '''
    add_btn_style = '''
        QPushButton#menu_add_cart_btn{
            background-color:white;
            border: 1px solid rgb(232, 233, 239);
            border-radius:44px;
            color:rgb(44, 159, 97);
        }
        QPushButton#menu_add_cart_btn:pressed{
            background-color:rgb(44, 159, 97);
            border: 1px solid rgb(232, 233, 239);
            border-radius:44px;
            color:white;
        }
    '''

    clean_day_style = """
        QWidget#wbtn_clean_day{
            background-color:white;
            border-radius:31px;
        }
    """
    clean_day_selected_style = """
         QWidget#wbtn_clean_day{
            background-color:rgb(83, 203, 49);
            border-radius:31px;
        }
    """

    clean_week_style = """
        QWidget#wbtn_clean_week{
            background-color:white;
            border-radius:31px;
        }
    """
    clean_week_selected_style = """
        QWidget#wbtn_clean_week{
            background-color:rgb(83, 203, 49);
            border-radius:31px;
        }
    
    """
    clean_day_icon_style = 'border-image: url(:/icon/icon_clean_no_selected.png);'
    clean_day_icon_selected_style = 'border-image: url(:/icon/icon_clean_selected.png);'

    clean_font_color_selected_style = 'color:white;'
    clean_font_color_style = 'color:rgb(83, 203, 49);'

    clean_record_style = """
           QWidget#wbtn_clean_record{
               background-color:white;
               border-radius:31px;
           }
       """
    clean_record_selected_style = """
           QWidget#wbtn_clean_record{
               background-color:rgb(83, 203, 49);
               border-radius:31px;
           }

       """

    clean_record_icon_style = 'border-image:url(:/icon/icon_clean_record_no_selected.png);'
    clean_record_icon_selected_style = 'border-image:url(:/icon/icon_clean_record_no_selected.png);'


    sw_scan_code_notice_widget_green = """
        QWidget#sw_scan_code_notice_widget{
            background-color:rgba(44, 159, 97, 1);
            border-radius:10px;
        }
    """
    icon_sw_scan_code_notice_green = 'border-image: url(:/icon/icon_sw_scan_code_notice.png);'
    sw_scan_code_notice_widget_yellow = """
        QWidget#sw_scan_code_notice_widget{
            background-color:rgba(255, 154, 24, 1);
            border-radius:10px;
        }
    """
    icon_sw_scan_code_notice_yellow = 'border-image: url(:/icon/icon_notice_remind.png);'
    sw_scan_code_notice_widget_red = """
        QWidget#sw_scan_code_notice_widget{
            background-color:rgba(255, 83, 74, 1);
            border-radius:10px;
        }
    """
    icon_sw_scan_code_notice_red = 'border-image: url(:/icon/icon_notice_warn.png);'

    debug_false_style = """
        QWidget#wbtn_setting_debug{
            border-image: url(:/icon/background_setting_debug.png);
        }
    """
    debug_true_style = """
            QWidget#wbtn_setting_debug{
                background-color:rgba(44, 159, 97, 0.5);
                border-image: url(:/icon/background_setting_debug.png);
                border-radius: 30px;
            }
        """

    screen_false_style = """
            QWidget#wbtn_setting_second_screen{
                border-image: url(:/icon/background_setting_debug.png);
            }
        """
    scree_true_style = """
                QWidget#wbtn_setting_second_screen{
                    background-color:rgba(44, 159, 97, 0.5);
                    border-image: url(:/icon/background_setting_debug.png);
                    border-radius: 30px;
                }
            """

    logo_login_style = """
        QWidget#icon_tee_widget{
            border-image: url(:/icon/logo.png);
            border-radius:50px;
        }
    """

    logo_debug_style = """
            QWidget#icon_tee_widget{
                border-image: url(:/icon/debug.png);
                border-radius:50px;
            }
        """