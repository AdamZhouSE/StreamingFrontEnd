"""
实现websocket
目前只是测试效果，background_thread()方法中每五秒传一次数据
还需要和原来的项目连通
"""
from flask import Flask, request, render_template, redirect, sessions
from flask_socketio import SocketIO, emit
import random
from threading import Lock
async_mode = None
app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)

thread = None
thread_lock = Lock()


# 后台线程 产生数据，即刻推送至前端
def background_thread():
    count = 0
    while True:
        # 每5秒传送一次
        socketio.sleep(5)
        count += 1
        nums = []
        for i in range(0, 5):
            nums.append(random.randint(90, 100))
        # 词云要求的数据格式
        data = [['word', nums[0]], ['ji', nums[1]], ['dwd', nums[2]], ['hi', nums[3]]]
        socketio.emit('server_response',
                      {'data': data, 'count': count},
                      namespace='/test')


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