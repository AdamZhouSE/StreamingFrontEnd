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


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)


if __name__ == '__main__':
    socketio.run(app, debug=True)