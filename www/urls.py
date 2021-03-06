#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

import os, re, time, base64, hashlib, logging

import markdown2

from transwarp.web import get, post, ctx, view, interceptor, seeother, notfound

from apis import api, Page, APIError, APIValueError, APIPermissionError, APIResourceNotFoundError
from models import User,TestCaseDetail,TestCaseGroup
from config import configs
from pyhessian.client import HessianProxy
import json

_COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

def _get_page_index():
    page_index = 1
    try:
        page_index = int(ctx.request.get('page', '1'))
    except ValueError:
        pass
    return page_index

def make_signed_cookie(id, password, max_age):
    # build cookie string by: id-expires-md5
    expires = str(int(time.time() + (max_age or 86400)))
    L = [id, expires, hashlib.md5('%s-%s-%s-%s' % (id, password, expires, _COOKIE_KEY)).hexdigest()]
    return '-'.join(L)

def parse_signed_cookie(cookie_str):
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        id, expires, md5 = L
        if int(expires) < time.time():
            return None
        user = User.get(id)
        if user is None:
            return None
        if md5 != hashlib.md5('%s-%s-%s-%s' % (id, user.password, expires, _COOKIE_KEY)).hexdigest():
            return None
        return user
    except:
        return None

def check_admin():
    user = ctx.request.user
    if user and user.admin:
        return
    raise APIPermissionError('No permission.')

@interceptor('/')
def user_interceptor(next):
    logging.info('try to bind user from session cookie...')
    user = None
    cookie = ctx.request.cookies.get(_COOKIE_NAME)
    if cookie:
        logging.info('parse session cookie...')
        user = parse_signed_cookie(cookie)
        if user:
            logging.info('bind user <%s> to session...' % user.email)
    ctx.request.user = user
    return next()

@interceptor('/manage/')
def manage_interceptor(next):
    user = ctx.request.user
    if user and user.admin:
        return next()
    raise seeother('/signin')





@view('signin.html')
@get('/signin')
def signin():
    return dict()

@get('/signout')
def signout():
    ctx.response.delete_cookie(_COOKIE_NAME)
    raise seeother('/')

@api
@post('/api/authenticate')
def authenticate():
    i = ctx.request.input(remember='')
    email = i.email.strip().lower()
    password = i.password
    remember = i.remember
    user = User.find_first('where email=?', email)
    if user is None:
        raise APIError('auth:failed', 'email', 'Invalid email.')
    elif user.password != password:
        raise APIError('auth:failed', 'password', 'Invalid password.')
    # make session cookie:
    max_age = 604800 if remember=='true' else None
    cookie = make_signed_cookie(user.id, user.password, max_age)
    ctx.response.set_cookie(_COOKIE_NAME, cookie, max_age=max_age)
    user.password = '******'
    return user

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_MD5 = re.compile(r'^[0-9a-f]{32}$')

@api
@post('/api/users')
def register_user():
    i = ctx.request.input(name='', email='', password='')
    name = i.name.strip()
    email = i.email.strip().lower()
    password = i.password
    if not name:
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not password or not _RE_MD5.match(password):
        raise APIValueError('password')
    user = User.find_first('where email=?', email)
    if user:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    user = User(name=name, email=email, password=password, image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email).hexdigest())
    user.insert()
    # make session cookie:
    cookie = make_signed_cookie(user.id, user.password, None)
    ctx.response.set_cookie(_COOKIE_NAME, cookie)
    return user

@view('register.html')
@get('/register')
def register():
    return dict()



@get('/manage/')
def manage_index():
    raise seeother('/manage/comments')

@view('manage_comment_list.html')
@get('/manage/comments')
def manage_comments():
    return dict(page_index=_get_page_index(), user=ctx.request.user)

@view('manage_blog_list.html')
@get('/manage/blogs')
def manage_blogs():
    return dict(page_index=_get_page_index(), user=ctx.request.user)

@view('manage_blog_edit.html')
@get('/manage/blogs/create')
def manage_blogs_create():
    return dict(id=None, action='/api/blogs', redirect='/manage/blogs', user=ctx.request.user)


@view('manage_user_list.html')
@get('/manage/users')
def manage_users():
    return dict(page_index=_get_page_index(), user=ctx.request.user)



@api
@get('/api/users')
def api_get_users():
    total = User.count_all()
    page = Page(total, _get_page_index())
    users = User.find_by('order by created_at desc limit ?,?', page.offset, page.limit)
    for u in users:
        u.password = '******'
    return dict(users=users, page=page)





@view('services.html')
@post('/service/create')
def addservice():
     i = ctx.request.input(name='', serviceType=1, serviceUrl='',parameter="")
     name = i.name.strip()
     serviceType = i.serviceType.strip()
     serviceUrl = i.serviceUrl.strip()
     parameter=i.parameter.strip()
     tc=TestCaseDetail(name=name,serviceType=serviceType,serviceUrl=serviceUrl,parameter=parameter)
     tc.insert()
     results=TestCaseDetail.find_by(" where is_delete!=1 ")
     return dict(services=results)



@api
@get('/api/services')
def services():
    format = ctx.request.get('format', '')
    blogs, page = _get_services_by_page()
    if format=='html':
        for blog in blogs:
            blog.content = markdown2.markdown(blog.content)
    return dict(services=blogs, page=page)

@api
@get('/api/services/:serviceId/delete')
def delService(serviceId):
    testcase = TestCaseDetail.get(serviceId)
    if testcase is None:
        raise APIResourceNotFoundError('Blog')
    testcase.delete()
    return dict(id=serviceId)

@view('services.html')
@get('/services/list')
def serviceList():
    return dict(page_index=_get_page_index(), user=ctx.request.user)

@api
@post('/service/run/:serviceId')
def serviceRun(serviceId):
    testcase = TestCaseDetail.get(serviceId)
    if testcase is None:
        raise APIResourceNotFoundError('Blog')
    rs= dict()
    if testcase.service_type==1:
        service = HessianProxy(testcase.service_url)
        #reqParam = eval(testcase.parameter)
        parameter=testcase.parameter
        result=''
        result=eval("service."+testcase.name+"(parameter)")
        print result
        rs.update(result.__dict__)
        return json.dumps(rs)

@view('service_edit.html')
@get('/service/create')
def service_create():
    return dict(id=None, action='/api/blogs', redirect='/services/list', user=ctx.request.user)


@view('groups.html')
@get('/group/list')
def grouplist():
    return dict(page_index=_get_page_index(), user=ctx.request.user)


@api
@get('/api/groups')
def groups():
    format = ctx.request.get('format', '')
    blogs, page = _get_groups_by_page()
    if format=='html':
        for blog in blogs:
            blog.content = markdown2.markdown(blog.content)
    return dict(groups=blogs, page=page)

@view('group_edit.html')
@get('/group/create')
def group_create():
    return dict(id=None,action='/group/add', redirect='/group/list', user=ctx.request.user)

@api
@post('/group/add')
def addservice():
     i = ctx.request.input(name='', domianUrl='')
     name = i.name.strip()
     domainUrl = i.domianUrl.strip()
     tc=TestCaseGroup(name=name,domain_url=domainUrl)
     tc.insert()
     return tc

@api
@post('/api/group/:groupId')
def group_detail(groupId):
    tg=TestCaseGroup.get(groupId)
    if tg:
        return tg
    raise APIResourceNotFoundError('Blog')


def _get_services_by_page():
    total = TestCaseDetail.count_by(" where is_delete!=1 ")
    page = Page(total, _get_page_index())
    servies = TestCaseDetail.find_by('where is_delete!=1 limit ?,?', page.offset, page.limit)
    return servies, page

def _get_groups_by_page():
    total = TestCaseGroup.count_by(" where is_delete!=1 ")
    page = Page(total, _get_page_index())
    servies = TestCaseGroup.find_by('where is_delete!=1 limit ?,?', page.offset, page.limit)
    return servies, page
