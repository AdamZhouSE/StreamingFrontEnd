"""
实现websocket
从hdfs中读取spark处理的结果，传送到前端生成词云
"""
from flask import Flask, request, render_template, redirect, sessions
from flask_socketio import SocketIO, emit
from threading import Lock
import pyhdfs
import webbrowser
async_mode = None
app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)

thread = None
thread_lock = Lock()

HADOOP_URL = "172.20.10.3:9870"
HADOOP_USER = "root"
HADOOP_DIR = "/wordcount_res/"
HADOOP_ACTIVITY_DIR = "/activity_data/"
FILENAME = "part-00000"
client = pyhdfs.HdfsClient(hosts=HADOOP_URL, user_name=HADOOP_USER)
data = dict()


def get_data():
    global data
    data = dict()
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
    global data
    while True:
        # 每10秒传送一次
        socketio.sleep(10)
        # get_data()
        # if len(data) > 0:
        #     data_list = []
        #     for k in data:
        #         cnt = data[k]
        #         #对词频开根号，避免有的数字过大而超过绘图限制
        #         cnt = cnt**0.6
        #         data_list.append([k, cnt])
        #     print(data_list[:100])
        #     socketio.emit('server_response', data=data_list, namespace='/wordCloud')
        # else:
        #     print("empty")
        # 时间周期图要求的数据格式
        # 此处data2[i][j]表示第j天，第i个时间段内的发帖数
        bar_data = draw_bar_trend()
        timeCount = 4  # 每天分成6个时间段
        categoryCount = len(bar_data[0])  # 共展示16天
        data2 = bar_data
        socketio.emit('server_response',
                      {'data': data2, 'timeCount': timeCount, 'categoryCount': categoryCount},
                      namespace='/barChart')


def draw_bar_trend():
    bar_data = [[], [], [], []]
    # 获取目录下所有文件并遍历
    file_list = client.listdir(HADOOP_ACTIVITY_DIR)
    for f in file_list:
        pathname = HADOOP_ACTIVITY_DIR + f
        # 存在该文件
        if client.exists(pathname):
            file_status = client.list_status(pathname)
            # 文件不为空
            if file_status[0]["length"] > 0:
                response = client.open(pathname)
                i = 0
                for c in response:
                    content = str(c, "utf-8")
                    time_info = content.split()
                    bar_data[i].append(time_info[2])
                    i += 1
    return bar_data
    # 时间周期图要求的数据格式
    # 此处data2[i][j]表示第j天，第i个时间段内的发帖数
    # timeCount = 4  # 每天分成6个时间段
    # categoryCount = len(bar_data[0])  # 共展示16天
    # data2 = bar_data
    # socketio.emit('server_response',
    #             {'data': data2, 'timeCount': timeCount, 'categoryCount': categoryCount},
    #             namespace='/barChart')


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


@app.route('/barChart')
def test2():
    return render_template('active-bar-trend.html', async_mode=socketio.async_mode)


@socketio.on('connect', namespace='/wordCloud')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)


@socketio.on('connect', namespace='/barChart')
def test1_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread())


if __name__ == '__main__':
    socketio.run(app, debug=True)