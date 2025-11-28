from django.contrib import admin
from django.urls import path
from .views import home, blogs, createBlog, manageBlog

urlpatterns = [
    path('', home, name='home'),
    path('blogs/', blogs, name='blogs'),
    path('createBlog/', createBlog, name='createBlog'),
    path('manageBlog/', manageBlog, name='manageBlog'),
]