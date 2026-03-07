from PyQt5.QtCore import QThread, pyqtSignal
import requests
import json
import sys
import os


class IpThread(QThread):
    result_ip = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)


    def run(self):
        try:
            url = "http://httpbin.org/ip"  # 也可以直接在浏览器访问这个地址
            r = requests.get(url)  # 获取返回的值
            ip = json.loads(r.text)["origin"]  # 取其中某个字段的值
            print(ip)

            # 发送get请求
            url = f'http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query&lang=zh-CN'
            # 其中fields字段为定义接受返回参数，可不传；lang为设置语言，zh-CN为中文，可以传
            res = requests.get(url)  # 发送请求
            jsonobj = json.loads(res.text)
            print(f'jsonobj:{jsonobj}')
            # print(res.json(), end="\n")
            
            json_path = self.resource_path('json.json')
            data = json.loads(res.text)
            with open(json_path, 'w', encoding='utf-8') as file:
                file.write(json.dumps(data, indent=2, ensure_ascii=False))

            dataJson = json.load(open(json_path, encoding='UTF-8'))  # 打开json文件，并将其中的数据全部读取
            jsondata = [dataJson["country"], dataJson["regionName"], dataJson["city"]]  # 读取json文件中我们需要的部分
            region = dataJson["regionName"]
            city = dataJson["city"]
            self.result_ip.emit(f'{region}{city}')
            # print(f"ip:{region}{city}")
        except Exception as e:
            print(e)
    


    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)