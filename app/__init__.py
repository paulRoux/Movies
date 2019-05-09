import os
import pymysql
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_redis import FlaskRedis


app = Flask(__name__)  # 创建app对象
app.debug = True  # 开启调试模式


# MySQL数据库连接
pymysql.install_as_MySQLdb()
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://root:123456@127.0.0.1:3306/movies"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config['SECRET_KEY'] = 'roux'
db = SQLAlchemy(app)


# 定义文件上传保存的路径，在__init__.py文件所在目录创建media文件夹，用于保存上传的文件
app.config['UP_DIR'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/media/')
# 存放用户头像的路径
app.config['USER_IMAGE'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/image/')


# 配置redis
app.config["REDIS_URL"] = 'redis://127.0.0.1:6379/1'
rd = FlaskRedis(app)


from app.home import home as home_blueprint
from app.admin import admin as admin_blueprint

# 注册蓝图
app.register_blueprint(home_blueprint)
app.register_blueprint(admin_blueprint, url_prefix="/admin")


# 添加全局404页面
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


# 添加全局401无权限页面
@app.errorhandler(401)
def unauthorized_access(error):
    return render_template('401.html'), 401
