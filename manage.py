from app import app
# from flask_script import Manager

# manager = Manager(app)

if __name__ == "__main__":
    """此项目在视频和其他人的基础上做了一些修改，以及一些bug的fix
    如果不是本地测试，那么需要关闭app.__init__的debug调试配置
    如果考虑管理的问题可以把本文件注释去掉，注释掉app.run()即可
    """
    # manager.run()
    app.run()
