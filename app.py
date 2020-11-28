"""
实现websocket
从hdfs中读取spark处理的结果，传送到前端生成词云
"""
from flask import Flask, request, render_template, redirect, sessions
from flask_socketio import SocketIO, emit
from threading import Lock
import pyhdfs
async_mode = None
app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)

thread = None
thread_lock = Lock()

HADOOP_URL = "172.20.10.3:9870"
HADOOP_USER = "root"
HADOOP_DIR = "/res/"
FILENAME = "part-00000"
client = pyhdfs.HdfsClient(hosts=HADOOP_URL, user_name=HADOOP_USER)
data = dict()


def get_data():
    # 获取目录下所有文件并遍历
    file_list = client.listdir(HADOOP_DIR)
    for f in file_list:
        pathname = HADOOP_DIR + f + "/" + FILENAME
        # 存在该文件
        if client.exists(pathname):
            file_status = client.list_status(pathname)
            # 文件不为空
            if file_status[0]["length"] > 0:
                response = client.open(pathname)
                content = ""
                for c in response:
                    content += str(c, "utf-8")
                # 对数据进行处理
                parse_data(content)


def parse_data(content):
    """
    传入的处理结果格式：一行一个字符串，形如('word', 1)\n，将其按照key-value的形式加入字典
    :param content: spark处理结果的字符串形式
    :return:
    """
    tuple_list = content.split("\n")
    for str_tuple in tuple_list:
        if len(str_tuple) > 0:
            # 将字符串转换为元组
            t = eval(str_tuple)
            key = t[0]
            value = t[1]
            if key in data:
                data[key] += value
            else:
                data[key] = value


# 后台线程 产生数据，即刻推送至前端
def background_thread():
    while True:
        # 每6秒传送一次
        socketio.sleep(6)
        # 将字典转化为指定格式
        get_data()
        if len(data) > 0:
            data_list = []
            for k in data:
                # 避免数字超过绘图的最大值
                cnt = data[k] % 1000
                data_list.append([k, cnt])
            print(data_list)
            socketio.emit('server_response', data=data_list, namespace='/test')
        else:
            print("empty")

        # 饼加折现图要求的数据格式
        # 如果要增减子列表个数，在dataset-link中也要对应增减option中series的行数
        data1 = [
            ['date', '10.12', '10.13', '10.14', '10.15', '10.16', '10.17', '10.18'],
            ['Matcha Latte', 41.1, 30.4, 65.1, 53.3, 83.8, 98.7],  # 故意少放一个数据看看效果
            ['牛奶', 86.5, 92.1, 85.7, 83.1, 73.4, 55.1, 47.9],
            ['芝士可可', 24.1, 67.2, 79.5, 86.4, 65.2, 82.5, 63.5],
            ['Walnut Brownie', 55.2, 67.1, 69.2, 72.4, 53.9, 39.1, 67.2],
            ['阿华田奶昔', 45.5, 67.1, 45.2, 72.4, 53.9, 39.1, 37.9],
        ]
        socketio.emit('server_response',
                      {'data': data1, 'itemName': data1[0][0]},
                      namespace='/test1')

        # 时间周期图要求的数据格式
        # 此处data2[i][j]表示第j天，第i个时间段内的发帖数
        timeCount = 6  # 每天分成6个时间段
        categoryCount = 16  # 共展示16天
        data2 = [
            [20.00, 7.1, 35.5, 54, 24, 43, 21, 35, 46, 9, 27, 36, 19, 27, 47, 28],
            [20, 17, 15, 24, 14, 23, 11, 25, 34, 19, 19, 29, 25, 20, 36, 28],
            [14, 23, 11, 25, 34, 19, 19, 29, 20, 7, 35, 54, 24, 43, 21, 28],
            [15, 24, 14, 23, 11, 25, 14, 23, 11, 25, 34, 19, 21, 35, 46, 28],
            [17, 15, 24, 14, 23, 34, 19, 19, 29, 20, 7, 11, 25, 14, 23, 28],
            [35, 54, 24, 43, 24, 14, 23, 34, 19, 23, 11, 25, 34, 19, 35, 28]
        ]
        socketio.emit('server_response',
                      {'data': data2, 'timeCount': timeCount, 'categoryCount': categoryCount},
                      namespace='/test2')



@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


@app.route('/test1')
def test1():
    return render_template('dataset-link.html', async_mode=socketio.async_mode)


@app.route('/test2')
def test2():
    return render_template('active-bar-trend.html', async_mode=socketio.async_mode)



@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)


@socketio.on('connect', namespace='/test1')
def test1_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)


@socketio.on('connect', namespace='/test2')
def test2_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)


if __name__ == '__main__':
    socketio.run(app, debug=True)