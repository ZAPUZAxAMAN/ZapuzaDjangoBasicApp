from django.shortcuts import render

# Create your views here.

def home(request):
    return render(request, 'basicApp/home.html')

def blogs(request):
    return render(request, 'basicApp/blogs.html')

def createBlog(request):
    return render(request, 'basicApp/createBlog.html')

def manageBlog(request):
    return render(request, 'basicApp/manageBlog.html')
