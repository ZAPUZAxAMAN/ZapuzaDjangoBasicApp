from django.urls import path
from .views import home, blogs, scrollView, get_next_blogs, createBlog, manageBlog, editBlog, deleteBlog, blog, toggle_reaction, add_comment, delete_comment

urlpatterns = [
    path('', home, name='home'),
    path('blogs/', blogs, name='blogs'),
    path('scrollView/', scrollView, name='scrollView'),
    path('api/get-next-blogs/', get_next_blogs, name='get_next_blogs'),
    path('blog/<uuid:id>/', blog, name='blog'),
    path('createBlog/', createBlog, name='createBlog'),
    path('manageBlog/', manageBlog, name='manageBlog'),
    path('editBlog/<uuid:id>/', editBlog, name='editBlog'),
    path('deleteBlog/<uuid:id>/', deleteBlog, name='deleteBlog'),
    path('blog/<uuid:id>/reaction/<str:reaction_type>/', toggle_reaction, name='toggle_reaction'),
    path('blog/<str:id>/add-comment/', add_comment, name='add_comment'),
    path('comment/<int:comment_id>/delete/', delete_comment, name='delete_comment'),
]