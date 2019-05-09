from . import admin
from flask import render_template, redirect, url_for, flash, session, request, abort
from app.admin.forms import LoginFrom, TagForm, MovieForm, PreviewForm, PwdForm, AuthForm, RoleForm, AdminForm
from app.models import Admin, Tag, Movie, Preview, User, Comment, MovieCollect, Auth, Role, OperateLog, UserLog, AdminLog
from functools import wraps
from app import db, app
from werkzeug.utils import secure_filename
import os
import uuid  # 生成唯一字符串
import datetime  # 生成时间


# 上下文应用处理器 会将函数的变量转换为全局变量
@admin.context_processor
def tpl_extra():
    data = dict(
        online_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    return data


# 要求登录才能访问
def admin_login_require(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if session.get('login_admin', None) is None:
            # 如果session中未找到该键，则用户需要登录
            return redirect(url_for('admin.login', next=request.url))
        return func(*args, **kwargs)

    return decorated_function


# 权限控制装饰器
def permission_control(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        login_admin = Admin.query.join(
            Role
        ) .filter(
            Role.id == Admin.role_id,
            Admin.name == session['login_admin']
        ).first()

        all_auth = Auth.query.all()  # 数据库所有权限

        auths = login_admin.role.auths
        auths = list(map(lambda item: int(item), auths.split(',')))  # 用户权限id列表
        urls = [auth.url for auth in all_auth for admin_auth_id in auths if admin_auth_id == auth.id]

        # print(urls)
        rule = request.url_rule
        # print(rule)  # 需要转为str判断是否在list中
        if str(rule) not in urls and login_admin.is_super != 0:  # 权限不存在，且不是超级管理员
            abort(401)
        return func(*args, **kwargs)
    return decorated_function


# 修改文件名称
def change_filename(filename):
    fileinfo = os.path.splitext(filename)  # 分离包含路径的文件名与包含点号的扩展名
    filename = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4().hex + fileinfo[-1])
    print('函数中修改后的文件名：', filename)
    return filename


@admin.route("/")
@admin_login_require
@permission_control
def index():
    return render_template('admin/index.html')


# 登陆
@admin.route("/login/", methods=['GET', 'POST'])
def login():
    form = LoginFrom()
    if form.validate_on_submit():
        # 提交的时候验证表单
        data = form.data  # 获取表单的数据
        # print(data)
        login_admin = Admin.query.filter_by(name=data['account']).first()
        if not login_admin.check_pwd(data['pwd']):
            # 判断密码错误，然后将错误信息返回，使用flash用于消息闪现
            flash('密码错误！')
            return redirect(url_for('admin.login'))
        # 如果密码正确，session中添加账号记录，然后跳转到request中的next，或者是跳转到后台的首页
        session['login_admin'] = data['account']
        # 操作日志
        session['admin_id'] = login_admin.id
        # 管理员登录日志
        admin_log = AdminLog(
            admin_id=login_admin.id,
            ip=request.remote_addr
        )
        db.session.add(admin_log)
        db.session.commit()
        return redirect(request.args.get('next') or url_for('admin.index'))
    return render_template('admin/login.html', form=form)


# 退出
@admin.route("/logout/")
@admin_login_require
def logout():
    session.pop('login_admin', None)  # 删除session中的登录账号
    session.pop('admin_id', None)
    return redirect(url_for("admin.login"))


# 修改密码
@admin.route("/pwd/", methods=['GET', 'POST'])
@admin_login_require
def pwd():
    form = PwdForm()
    if form.validate_on_submit():
        data = form.data
        login_name = session['login_admin']
        admin = Admin.query.filter_by(name=login_name).first()
        from werkzeug.security import generate_password_hash
        admin.pwd = generate_password_hash(data['new_pwd'])
        db.session.commit()  # 提交新密码保存，然后跳转到登录界面
        flash('密码修改成功，请重新登录！', category='ok')
        return redirect(url_for('admin.logout'))
    return render_template('admin/pwd.html', form=form)


# 增加标签
@admin.route("/tag/add/", methods=['GET', 'POST'])
@admin_login_require
@permission_control
def tag_add():
    form = TagForm()
    if form.validate_on_submit():
        data = form.data
        tag_num = Tag.query.filter_by(name=data['name']).count()
        if tag_num == 1:
            flash('标签名称已存在！', category='err')
            return redirect(url_for('admin.tag_add'))
        # 如果标签不存在，就添加到数据库
        tag = Tag(
            name=data['name']
        )
        db.session.add(tag)
        db.session.commit()
        # 提交完成后也返回一条成功的消息
        flash('标签添加成功！', category='ok')
        # 日志
        operatelog = OperateLog(
            admin_id=session['admin_id'],
            ip=request.remote_addr,
            reason="添加标签{}".format(data['name'])
        )
        db.session.add(operatelog)
        db.session.commit()
        return redirect(url_for('admin.tag_add'))
    return render_template('admin/tag_add.html', form=form)


# 标签列表
@admin.route("/tag/list/<int:page>/", methods=['GET'])
@admin_login_require
@permission_control
def tag_list(page=None):
    if page is None:
        page = 1
    # 设置per_page每页显示多少个数据
    page_tags = Tag.query.order_by(Tag.add_time.desc()).paginate(page=page, per_page=10)
    return render_template('admin/tag_list.html', page_tags=page_tags)


# 删除标签
@admin.route("/tag/delete/<int:delete_id>/", methods=['GET'])
@admin_login_require
@permission_control
def tag_delete(delete_id=None):
    if delete_id:
        tag = Tag.query.filter_by(id=delete_id).first_or_404()
        db.session.delete(tag)
        db.session.commit()
        # 删除后闪现消息
        flash('删除标签成功！', category='ok')
    return redirect(url_for('admin.tag_list', page=1))


# 更新标签
@admin.route("/tag/update/<int:update_id>/", methods=['GET', 'POST'])
@admin_login_require
@permission_control
def tag_update(update_id=None):
    form = TagForm()
    tag = Tag.query.get_or_404(update_id)  # 首先查询到该标签，用主键查询，如果不存在，则返回404
    if form.validate_on_submit():
        data = form.data
        tag_num = Tag.query.filter_by(name=data['name']).count()
        if tag_num == 1:
            flash('标签名称已存在！', category='err')
            return redirect(url_for('admin.tag_update', update_id=update_id))
        # 如果标签不存在，就进行修改
        tag.name = data['name']
        db.session.commit()
        # 提交完成后也返回一条成功的消息
        flash('标签修改成功！', category='ok')
        return redirect(url_for('admin.tag_update', update_id=update_id))
    return render_template('admin/tag_update.html', form=form, tag=tag)


# 增加电影
@admin.route("/movie/add/", methods=['GET', 'POST'])
@admin_login_require
@permission_control
def movie_add():
    form = MovieForm()
    if form.validate_on_submit():
        data = form.data

        # 提交的片名在数据库中已存在
        if Movie.query.filter_by(title=data['title']).count() == 1:
            flash('电影片名已存在，请检查', category='err')
            return redirect(url_for('admin.movie_add'))

        # 获取上传文件的名称
        file_url = secure_filename(form.url.data.filename)
        file_logo = secure_filename(form.logo.data.filename)
        # 文件保存路径操作
        file_save_path = app.config['UP_DIR']  # 文件上传保存路径
        if not os.path.exists(file_save_path):
            os.makedirs(file_save_path)  # 如果文件保存路径不存在，则创建一个多级目录
            import stat
            os.chmod(file_save_path, stat.S_IRWXU)  # 授予可读写权限
        # 对上传的文件进行重命名
        url = change_filename(file_url)
        logo = change_filename(file_logo)
        # 保存文件，需要给文件的保存路径+文件名
        form.url.data.save(file_save_path + url)
        form.logo.data.save(file_save_path + logo)

        movie = Movie(
            title=data['title'],
            url=url,
            info=data['info'],
            logo=logo,
            star=data['star'],
            play_num=0,
            comment_num=0,
            tag_id=data['tag_id'],
            area=data['area'],
            release_time=data['release_time'],
            length=data['length']
        )
        db.session.add(movie)
        db.session.commit()
        flash('添加电影成功', 'ok')
        return redirect(url_for('admin.movie_add'))
    return render_template('admin/movie_add.html', form=form)


# 电影列表
@admin.route("/movie/list/<int:page>/", methods=['GET'])
@admin_login_require
@permission_control
def movie_list(page=None):
    if page is None:
        page = 1
    # 查询的时候关联标签Tag进行查询：使用join(Tag)
    # 单表过滤使用filter_by，多表关联使用filter，将Tag.id与Movie的tag_id进行关联
    page_movies = Movie.query.join(Tag).filter(
        Tag.id == Movie.tag_id
    ).order_by(
        Movie.add_time.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/movie_list.html', page_movies=page_movies)


# 删除电影
@admin.route("/movie/delete/<int:delete_id>/", methods=['GET'])
@admin_login_require
@permission_control
def movie_delete(delete_id=None):
    if delete_id:
        movie = Movie.query.filter_by(id=delete_id).first_or_404()
        print(movie.logo)
        # 删除电影同时要从磁盘中删除电影的文件和封面文件
        file_save_path = app.config['UP_DIR']  # 文件上传保存路径
        # 如果存在将进行删除，不判断，如果文件不存在删除会报错
        if os.path.exists(os.path.join(file_save_path, movie.url)):
            os.remove(os.path.join(file_save_path, movie.url))
        if os.path.exists(os.path.join(file_save_path, movie.logo)):
            os.remove(os.path.join(file_save_path, movie.logo))

        # 删除数据库，提交修改，注意后面要把与电影有关的评论都要删除
        db.session.delete(movie)
        db.session.commit()
        # 删除后闪现消息
        flash('删除电影成功！', category='ok')
    return redirect(url_for('admin.movie_list', page=1))


# 更新电影
@admin.route("/movie/update/<int:update_id>/", methods=['GET', 'POST'])
@admin_login_require
@permission_control
def movie_update(update_id=None):
    movie = Movie.query.get_or_404(int(update_id))
    # print(movie)

    # 给表单赋初始值，文件表单不处理
    form = MovieForm(
        title=movie.title,
        # url=movie.url,  # 上传文件，这样赋初始值无效，在前端可以通过上传路径+movie.url来获取文件的保存路径，显示在页面上
        info=movie.info,
        # logo=movie.logo,  # 上传图片和文件类似
        star=movie.star,
        tag_id=movie.tag_id,
        area=movie.area,
        release_time=movie.release_time,
        length=movie.length,
    )
    # 对于修改数据，电影文件和封面图已存在，可以非必填:按照教程上测试了validators参数，但始终不行，最终修改required的值就可以了
    form.url.validators = []
    # print(form.url)  # <input id="url" name="url" required type="file">
    if form.url.render_kw:
        form.url.render_kw['required'] = False
    else:
        form.url.render_kw = {'required': False}
    # print(form.url)  # <input id="url" name="url" type="file">

    form.logo.validators = []  # 验证列表为空
    form.logo.render_kw = {'required': False}  # 直接修改required为False表明不要求输入

    if form.validate_on_submit():
        data = form.data
        # 提交的片名在数据库中已存在，且不是当前的电影名称
        if Movie.query.filter_by(title=data['title']).count() == 1 and movie.title != data['title']:
            flash('电影片名已存在，请检查', category='err')
            return redirect(url_for('admin.movie_update', update_id=update_id))
        # 以下和直接修改的数据
        movie.title = data['title']
        movie.info = data['info']
        movie.star = data['star']
        movie.tag_id = data['tag_id']
        movie.area = data['area']
        movie.release_time = data['release_time']
        movie.length = data['length']

        # 文件保存路径操作
        file_save_path = app.config['UP_DIR']  # 文件上传保存路径
        if not os.path.exists(file_save_path):
            os.makedirs(file_save_path)  # 如果文件保存路径不存在，则创建一个多级目录
            import stat
            os.chmod(file_save_path, stat.S_IRWXU)  # 授予可读写权限

        print(form.url.data, type(form.url.data))
        # <FileStorage: 'ssh.jpg' ('image/jpeg')> <class 'werkzeug.datastructures.FileStorage'>
        # 处理电影文件逻辑：先从磁盘中删除旧文件，然后保存新文件
        if form.url.data:  # 上传文件不为空，才进行保存
            # 删除以前的文件
            if os.path.exists(os.path.join(file_save_path, movie.url)):
                os.remove(os.path.join(file_save_path, movie.url))
            # 获取上传文件的名称
            file_url = secure_filename(form.url.data.filename)
            # 对上传的文件进行重命名
            movie.url = change_filename(file_url)
            # 保存文件，需要给文件的保存路径+文件名
            form.url.data.save(file_save_path + movie.url)

        # 处理封面图
        if form.logo.data:
            if os.path.exists(os.path.join(file_save_path, movie.logo)):
                os.remove(os.path.join(file_save_path, movie.logo))
            file_logo = secure_filename(form.logo.data.filename)
            movie.logo = change_filename(file_logo)
            form.logo.data.save(file_save_path + movie.logo)
        db.session.merge(movie)  # 调用merge方法，此时Movie实体状态并没有被持久化，但是数据库中的记录被更新了（暂时不明白）
        db.session.commit()
        flash('更新电影成功', 'ok')
        return redirect(url_for('admin.movie_update', update_id=update_id))
    return render_template('admin/movie_update.html', form=form, movie=movie)


# 添加预览
@admin.route("/preview/add/", methods=['GET', 'POST'])
@admin_login_require
@permission_control
def preview_add():
    form = PreviewForm()
    if form.validate_on_submit():
        data = form.data
        if Preview.query.filter_by(title=data['title']).count() == 1:
            flash('预告标题已存在，请检查！', category='err')
            return redirect(url_for('admin.preview_add'))

        file_logo = secure_filename(form.logo.data.filename)  # 获取上传文件名字
        file_save_path = app.config['UP_DIR']  # 文件上传保存路径
        if not os.path.exists(file_save_path):
            os.makedirs(file_save_path)  # 如果文件保存路径不存在，则创建一个多级目录
            import stat
            os.chmod(file_save_path, stat.S_IRWXU)  # 授予可读写权限
        logo = change_filename(file_logo)  # 文件重命名
        form.logo.data.save(file_save_path + logo)  # 保存文件到磁盘中

        preview = Preview(
            title=data['title'],
            logo=logo  # 只在数据库中保存文件名
        )
        db.session.add(preview)
        db.session.commit()
        flash('添加预告成功', 'ok')
        return redirect(url_for('admin.preview_add'))

    return render_template('admin/preview_edit.html', form=form)


# 预览列表
@admin.route("/preview/list/<int:page>/")
@admin_login_require
@permission_control
def preview_list(page=None):
    page_previews = Preview.query.paginate(page=page, per_page=10)
    return render_template('admin/preview_list.html', page_previews=page_previews)


# 删除预览
@admin.route("/preview/delete/<int:delete_id>/", methods=['GET'])
@admin_login_require
@permission_control
def preview_delete(delete_id=None):
    if delete_id:
        preview = Preview.query.filter_by(id=delete_id).first_or_404()
        # 删除同时要从磁盘中删除封面文件
        file_save_path = app.config['UP_DIR']  # 文件上传保存路径
        # 如果存在将进行删除，不判断，如果文件不存在删除会报错
        if os.path.exists(os.path.join(file_save_path, preview.logo)):
            os.remove(os.path.join(file_save_path, preview.logo))

        # 删除数据库，提交修改，注意后面要把与电影有关的评论都要删除
        db.session.delete(preview)
        db.session.commit()
        # 删除后闪现消息
        flash('删除预告成功！', category='ok')
    return redirect(url_for('admin.preview_list', page=1))


# 更新预览
@admin.route("/preview/update/<int:update_id>/", methods=['GET', 'POST'])
@admin_login_require
@permission_control
def preview_update(update_id=None):
    preview = Preview.query.get_or_404(update_id)
    form = PreviewForm(
        title=preview.title,
    )
    # 不验证上传文件
    form.logo.validators = []
    form.logo.render_kw = {'required': False}

    if form.validate_on_submit():
        data = form.data
        if Preview.query.filter_by(title=data['title']).count() == 1 and preview.title != data['title']:
            flash('预告标题已存在，请重新输入', category='err')
            return redirect(url_for('admin.preview_update', update_id=update_id))

        preview.title = data['title']

        print(data['logo'], type(data['logo']), form.logo.data, type(form.logo.data))
        # <FileStorage: 'ssh.jpg' ('image/jpeg')> <class 'werkzeug.datastructures.FileStorage'>
        # <FileStorage: 'ssh.jpg' ('image/jpeg')> <class 'werkzeug.datastructures.FileStorage'>
        # 上面两种方式结果一样

        # 文件保存路径操作
        file_save_path = app.config['UP_DIR']  # 文件上传保存路径
        if not os.path.exists(file_save_path):
            os.makedirs(file_save_path)  # 如果文件保存路径不存在，则创建一个多级目录
            import stat
            os.chmod(file_save_path, stat.S_IRWXU)  # 授予可读写权限
        if form.logo.data:  # 当有上传新的图片
            if os.path.exists(os.path.join(file_save_path, preview.logo)):
                os.remove(os.path.join(file_save_path, preview.logo))  # 删除旧图片
            file_logo_name = form.logo.data.filename
            preview.logo = change_filename(file_logo_name)  # 得到新的文件名，保存到输入局
            form.logo.data.save(file_save_path + preview.logo)
        db.session.add(preview)
        db.session.commit()
        flash('预告信息修改成功！', category='ok')
        return redirect(url_for('admin.preview_update', update_id=update_id))
    return render_template('admin/preview_edit.html', form=form, preview=preview)


# 会员列表
@admin.route("/user/list/<int:page>/")
@admin_login_require
@permission_control
def user_list(page=None):
    if page is None:
        page = 1
    page_users = User.query.paginate(page=page, per_page=10)
    return render_template('admin/user_list.html', page_users=page_users)


# 会员查看
@admin.route("/user/view/<int:user_id>/")
@admin_login_require
@permission_control
def user_view(user_id=None):
    user = User.query.get_or_404(user_id)
    return render_template('admin/user_view.html', user=user)


# 会员删除
@admin.route("/user/delete/<int:delete_id>/")
@admin_login_require
@permission_control
def user_delete(delete_id=None):
    user = User.query.get_or_404(delete_id)
    # 删除同时要从磁盘中删除封面文件
    file_save_path = app.config['USER_IMAGE']  # 头像上传保存路径
    # 如果存在将进行删除，不判断，如果文件不存在删除会报错
    if os.path.exists(os.path.join(file_save_path, user.face)):
        os.remove(os.path.join(file_save_path, user.face))

    # 删除数据库，提交修改
    db.session.delete(user)
    db.session.commit()
    # 删除后闪现消息
    flash('删除会员成功！', category='ok')
    return redirect(url_for('admin.user_list', page=1))


# 评论列表
@admin.route("/comment/list/<int:page>/")
@admin_login_require
@permission_control
def comment_list(page=None):
    if page is None:
        page = 1
    page_comments = Comment.query.join(
        Movie
    ).join(
        User
    ).filter(
        Movie.id == Comment.movie_id,
        User.id == Comment.user_id
    ).order_by(
        Comment.add_time.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/comment_list.html', page_comments=page_comments)


# 删除评论
@admin.route("/comment/delete/<int:delete_id>")
@admin_login_require
@permission_control
def comment_delete(delete_id=None):
    comment = Comment.query.get_or_404(delete_id)
    db.session.delete(comment)
    db.session.commit()
    flash('删除评论成功！', category='ok')
    return redirect(url_for('admin.comment_list', page=1))


# 收藏列表
@admin.route("/collect/list/<int:page>/")
@admin_login_require
@permission_control
def collect_list(page=None):
    if page is None:
        page = 1
    page_moviecollects = MovieCollect.query.join(
        Movie
    ).join(
        User
    ).filter(
        Movie.id == Comment.movie_id,
        User.id == Comment.user_id
    ).order_by(
        Comment.add_time.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/collect_list.html', page_moviecollects=page_moviecollects)


# 删除收藏
@admin.route("/collect/delete/<int:delete_id>")
@admin_login_require
@permission_control
def collect_delete(delete_id=None):
    moviecollect = MovieCollect.query.get_or_404(delete_id)
    db.session.delete(moviecollect)
    db.session.commit()
    flash('删除收藏成功！', category='ok')
    return redirect(url_for('admin.collect_list', page=1))

# 操作日志列表
@admin.route("/logs/operate_log/<int:page>", methods=["GET"])
@admin_login_require
@permission_control
def logs_operate_log(page=None):
    if page is None:
        page = 1
    page_logs_operate_log = OperateLog.query.join(
        Admin
    ).filter(
        Admin.id == OperateLog.admin_id,
    ).order_by(
        OperateLog.add_time.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/logs_operate_log.html', page_logs_operate_log=page_logs_operate_log)


# 管理员登录日志
@admin.route("/logs/admin_log/<int:page>", methods=["GET"])
@admin_login_require
@permission_control
def logs_admin_log(page=None):
    if page is None:
        page = 1
    page_logs_admin_log = AdminLog.query.join(
        Admin
    ).filter(
        Admin.id == AdminLog.admin_id,
    ).order_by(
        AdminLog.add_time.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/logs_admin_log.html', page_logs_admin_log=page_logs_admin_log)


# 会员登陆日志
@admin.route("/logs/user_log/<int:page>", methods=["GET"])
@admin_login_require
@permission_control
def logs_user_log(page=None):
    if page is None:
        page = 1
    page_logs_user_log = UserLog.query.join(
        User
    ).filter(
        User.id == UserLog.user_id,
    ).order_by(
        UserLog.add_time.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/logs_user_log.html', page_logs_user_log=page_logs_user_log)


# 权限添加
@admin.route("/auth/add/", methods=['GET', 'POST'])
@admin_login_require
@permission_control
def auth_add():
    form = AuthForm()
    if form.validate_on_submit():
        data = form.data
        if Auth.query.filter_by(url=data['url']).count() == 1:
            flash('权限链接地址已存在！', category='err')
            return redirect(url_for('admin.auth_add'))
        auth = Auth(
            name=data['name'],
            url=data['url']
        )
        db.session.add(auth)
        db.session.commit()
        flash('权限地址添加成功！', category='ok')
    return render_template('admin/auth_edit.html', form=form)


# 权限列表
@admin.route("/auth/list/<int:page>/")
@admin_login_require
@permission_control
def auth_list(page=None):
    if not page:
        page = 1
    page_auths = Auth.query.order_by(Auth.add_time.asc()).paginate(page=page, per_page=10)
    return render_template('admin/auth_list.html', page_auths=page_auths)


# 权限删除
@admin.route("/auth/delete/<int:delete_id>/")
@admin_login_require
@permission_control
def auth_delete(delete_id=None):
    auth = Auth.query.get_or_404(delete_id)
    db.session.delete(auth)
    db.session.commit()
    flash('删除权限地址成功', category='ok')
    return redirect(url_for('admin.auth_list', page=1))


# 权限更新
@admin.route("/auth/update/<int:update_id>/", methods=['GET', 'POST'])
@admin_login_require
@permission_control
def auth_update(update_id=None):
    auth = Auth.query.get_or_404(update_id)
    form = AuthForm(
        name=auth.name,
        url=auth.url
    )
    if form.validate_on_submit():
        data = form.data
        if Auth.query.filter_by(url=data['url']).count() == 1 and auth.url != data['url']:
            flash('权限链接地址已存在！', category='err')
            return redirect(url_for('admin.auth_update', update_id=update_id))
        auth.name = data['name']
        auth.url = data['url']

        db.session.commit()
        flash('权限地址修改成功！', category='ok')
    return render_template('admin/auth_edit.html', form=form)


# 添加角色
@admin.route("/role/add/", methods=['GET', 'POST'])
@admin_login_require
@permission_control
def role_add():
    form = RoleForm()
    if form.validate_on_submit():
        data = form.data
        # print(data['auths'])  # 权限id列表形式[1, 2]
        role = Role(
            name=data['name'],
            auths=','.join(map(lambda item: str(item), data['auths']))  # 数字转换为字符串形式
        )
        db.session.add(role)
        db.session.commit()
        flash('角色添加成功', category='ok')
    return render_template('admin/role_edit.html', form=form)


# 角色列表
@admin.route("/role/list/<int:page>/")
@admin_login_require
@permission_control
def role_list(page=None):
    if not page:
        page = 1
    page_roles = Role.query.order_by(
        Role.add_time.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/role_list.html', page_roles=page_roles)


# 删除角色
@admin.route("/role/delete/<int:delete_id>/")
@admin_login_require
@permission_control
def role_delete(delete_id=None):
    role = Role.query.get_or_404(delete_id)
    db.session.delete(role)
    db.session.commit()
    flash('角色删除成功', category='ok')
    return redirect(url_for('admin.role_list', page=1))


# 更新角色
@admin.route("/role/update/<int:update_id>/", methods=['GET', 'POST'])
@admin_login_require
@permission_control
def role_update(update_id=None):
    role = Role.query.get_or_404(update_id)
    form = RoleForm(
        name=role.name,
        auths=list(map(lambda item: int(item), role.auths.split(','))) if role.auths else ''  # 换回int型列表
    )
    if form.validate_on_submit():
        data = form.data
        role.name = data['name']
        role.auths = ','.join(map(lambda item: str(item), data['auths']))

        db.session.commit()
        flash('角色修改成功！', category='ok')
    return render_template('admin/role_edit.html', form=form)


# 添加管理员
@admin.route("/admin/add/", methods=['GET', 'POST'])
@admin_login_require
@permission_control
def admin_add():
    form = AdminForm(is_super=1)
    from werkzeug.security import generate_password_hash
    # print(form.data)
    if form.validate_on_submit():
        data = form.data
        if Admin.query.filter_by(name=data['name']).count() == 1:
            flash('管理员已存在！', category='err')
            return redirect(url_for('admin.admin_add'))
        add_admin = Admin(
            name=data['name'],
            pwd=generate_password_hash(data['pwd']),
            role_id=data['role_id'],
            is_super=1
        )
        db.session.add(add_admin)
        db.session.commit()
        flash('管理员添加成功', category='ok')
    return render_template('admin/admin_edit.html', form=form)


# 管理员列表
@admin.route("/admin/list/<int:page>")
@admin_login_require
@permission_control
def admin_list(page=None):
    if not page:
        page = 1
    page_admins = Admin.query.order_by(
        Admin.add_time.desc()
    ).join(
        Role
    ).filter(
        Role.id == Admin.role_id  # 关联查询
    ).paginate(page=page, per_page=10)
    return render_template('admin/admin_list.html', page_admins=page_admins)
