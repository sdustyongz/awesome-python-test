#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

'''
Models for user, blog, comment.
'''

import time, uuid

from transwarp.db import next_id
from transwarp.orm import Model, StringField, BooleanField, FloatField, TextField,IntegerField

def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(updatable=False, ddl='varchar(50)')
    password = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(updatable=False, default=time.time)

class TestCaseGroup(Model):
    __table__ = 't_group'
    id = IntegerField(primary_key=True)
    name = StringField(updatable=False, ddl='varchar(50)',name="name")
    isDelete=IntegerField(name="is_delete")
    addTime = FloatField(updatable=False, default=time.time,name="add_time")
class TestCaseDetail(Model):
    __table__ = 't_detail'
    id = IntegerField(primary_key=True)
    name = StringField(updatable=False, ddl='varchar(50)',name="name")
    serviceUrl = StringField(updatable=False, ddl='varchar(50)',name="service_url")
    serviceType = IntegerField(updatable=False,name="service_type")
    parameter = StringField(updatable=False,name="parameter")
    groupId = IntegerField(updatable=False,name="group_id")
    isDelete=IntegerField(name="is_delete")
    addTime = FloatField(updatable=False, default=time.time,name="add_time")




