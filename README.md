### 微电影平台

#### 介绍

- 此项目是一个类似于电影平台的网站，用户可以登陆观看并评论及收藏等。管理员可以管理所有的后台资源，如：电影增加、删除，标签和预告的增加、删除，日志的查看等。

#### 模块

1. 后台管理(admin)

2. 前台(home)

#### 划分

1. 数据模型: models

2. 表单: forms

3. 视图: views

4. 调度: manage

#### 运行

- 此项目依赖于mysql5.7, redis4.3， python3.6

- 下载此项目, 然后执行`pip install -r requirements.txt`进行依赖环境的安装

- 安装完成后, 将models里面的注释进行取消, 然后执行`python models.py`进行数据库的创建(自行修改数据库的连接配置), 然后将role.sql导入到mysql里面

- 最后在根目录下执行`python manage.py`即可
