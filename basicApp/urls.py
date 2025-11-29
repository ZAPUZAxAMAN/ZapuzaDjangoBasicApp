from django.urls import path
from .views import home, blogs, createBlog, manageBlog, editBlog, deleteBlog, blog

urlpatterns = [
    path('', home, name='home'),
    path('blogs/', blogs, name='blogs'),
    path('blog/<uuid:id>/', blog, name='blog'),
    path('createBlog/', createBlog, name='createBlog'),
    path('manageBlog/', manageBlog, name='manageBlog'),
    path('editBlog/<uuid:id>/', editBlog, name='editBlog'),
    path('deleteBlog/<uuid:id>/', deleteBlog, name='deleteBlog'),
]