from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator, EmptyPage
from django.contrib import messages
from .models import Blogs


def home(request):
    return render(request, 'basicApp/home.html')


def blogs(request):
    all_blogs = Blogs.objects.all().order_by('-created')

    paginator = Paginator(all_blogs, 3)
    page = request.GET.get('page', 1)

    try:
        blogs_page = paginator.page(page)
    except EmptyPage:
        blogs_page = paginator.page(paginator.num_pages)

    context = {
        'blogs': blogs_page,
        'paginator': paginator,
    }
    return render(request, 'basicApp/blogs.html', context)

def blog(request, id):
    blog_post = get_object_or_404(Blogs, id=id)

    related_blogs = Blogs.objects.filter(
        category=blog_post.category
    ).exclude(id=id).order_by('-created')[:3]

    context = {
        'blog': blog_post,
        'related_blogs': related_blogs
    }
    return render(request, 'basicApp/blog.html', context)

def createBlog(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        category = request.POST.get('category')
        featureImage = request.FILES.get('featureImage')
        content = request.POST.get('content')
        tags = request.POST.get('tags', '')

        try:
            blog = Blogs.objects.create(
                title=title,
                category=category,
                featureImage=featureImage,
                content=content,
                tags=tags
            )
            messages.success(request, 'Blog created successfully!')
        except Exception as e:
            messages.error(request, f'Error creating blog: {str(e)}')

    return render(request, 'basicApp/createBlog.html')


def manageBlog(request):
    all_blogs = Blogs.objects.all().order_by('-created')

    paginator = Paginator(all_blogs, 3)
    page = request.GET.get('page', 1)

    try:
        blogs_page = paginator.page(page)
    except EmptyPage:
        blogs_page = paginator.page(paginator.num_pages)

    context = {
        'blogs': blogs_page,
        'paginator': paginator,
    }
    return render(request, 'basicApp/manageBlog.html', context)


def editBlog(request, id):
    blog = get_object_or_404(Blogs, id=id)

    if request.method == 'POST':
        try:
            blog.title = request.POST.get('title')
            blog.category = request.POST.get('category')
            blog.content = request.POST.get('content')
            blog.tags = request.POST.get('tags', '')

            # Only update image if a new one is uploaded
            if request.FILES.get('featureImage'):
                blog.featureImage = request.FILES.get('featureImage')

            blog.save()
            messages.success(request, 'Blog updated successfully!')
            return redirect('manageBlog')
        except Exception as e:
            messages.error(request, f'Error updating blog: {str(e)}')

    context = {
        'blog': blog
    }
    return render(request, 'basicApp/editBlog.html', context)


def deleteBlog(request, id):
    if request.method == 'POST':
        try:
            blog = Blogs.objects.get(id=id)
            blog.delete()
            messages.success(request, 'Blog deleted successfully!')
        except Blogs.DoesNotExist:
            messages.error(request, 'Blog not found!')
        except Exception as e:
            messages.error(request, f'Error deleting blog: {str(e)}')

    return redirect('manageBlog')