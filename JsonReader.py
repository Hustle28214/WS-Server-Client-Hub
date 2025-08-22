import json
import requests
import YB_Pcb_Car  #导入亚博智能专用的底层库文件
import time

# 定义一个car对象
car = YB_Pcb_Car.YB_Pcb_Car()

def read_json():
    read_url = "http://127.0.0.1:80"
    response = requests.get(read_url,timeout=10)
    response.raise_for_status()

    temp_json = response.json()

    json_data = json.loads(temp_json)

    return json_data

# def write_car_motor():
#     json_data = read_json()
#     cord_x = jso


