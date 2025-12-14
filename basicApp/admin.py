from django.contrib import admin
from .models import Blogs, BlogReaction, BlogComment
# Register your models here.

admin.site.register(Blogs)
admin.site.register(BlogReaction)
admin.site.register(BlogComment)