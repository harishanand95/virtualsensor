# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


# Create your models here.
class User(models.Model):
    token = models.CharField(max_length=100, primary_key=True)
    api_key = models.CharField(max_length=100)
    subscription_queue = models.CharField(max_length=100)
    resourceID = models.CharField(max_length=100)