from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator, EmptyPage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Blogs, BlogReaction, BlogComment
from django.http import JsonResponse
from django.db.models import F


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

    # Increment views
    Blogs.objects.filter(id=id).update(views=F('views') + 1)
    blog_post.refresh_from_db()

    # Get related blogs
    related_blogs = Blogs.objects.filter(
        category=blog_post.category
    ).exclude(id=id).order_by('-created')[:3]

    # Get all comments for this blog
    comments = BlogComment.objects.filter(blog=blog_post).order_by('-created')

    # Check user's reaction if authenticated
    user_reaction = None
    if request.user.is_authenticated:
        reaction = BlogReaction.objects.filter(user=request.user, blog=blog_post).first()
        if reaction:
            user_reaction = reaction.reaction

    return render(request, 'basicApp/blog.html', {
        'blog': blog_post,
        'related_blogs': related_blogs,
        'comments': comments,
        'user_reaction': user_reaction,
    })


@login_required(login_url='/accounts/login/')
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


@login_required(login_url='/accounts/login/')
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


@login_required(login_url='/accounts/login/')
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


@login_required(login_url='/accounts/login/')
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


@login_required(login_url='/accounts/login/')
def toggle_reaction(request, id, reaction_type):
    """Handle like/dislike via AJAX"""
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid request method"}, status=400)

    blog = get_object_or_404(Blogs, id=id)
    user = request.user

    try:
        existing = BlogReaction.objects.filter(user=user, blog=blog).first()

        if existing:
            if existing.reaction == reaction_type:
                # Remove reaction if clicking same button
                existing.delete()
                user_reaction = None
            else:
                # Switch like <-> dislike
                existing.reaction = reaction_type
                existing.save()
                user_reaction = reaction_type
        else:
            # Create new reaction
            BlogReaction.objects.create(user=user, blog=blog, reaction=reaction_type)
            user_reaction = reaction_type

        blog.refresh_from_db()

        return JsonResponse({
            "success": True,
            "likes": blog.likes_count,
            "dislikes": blog.dislikes_count,
            "user_reaction": user_reaction,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required(login_url='/accounts/login/')
def add_comment(request, id):
    """Handle comment submission via AJAX"""
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid request method"}, status=400)

    blog = get_object_or_404(Blogs, id=id)
    comment_text = request.POST.get('comment_text', '').strip()

    if not comment_text:
        return JsonResponse({"error": "Comment cannot be empty"}, status=400)

    try:
        comment = BlogComment.objects.create(
            user=request.user,
            blog=blog,
            text=comment_text
        )

        return JsonResponse({
            "success": True,
            "comment": {
                "id": comment.id,
                "user": comment.user.username,
                "text": comment.text,
                "created": comment.created.strftime("%B %d, %Y at %I:%M %p"),
            },
            "comments_count": blog.comments_count,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required(login_url='/accounts/login/')
def delete_comment(request, comment_id):
    """Handle comment deletion via AJAX"""
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid request method"}, status=400)

    try:
        comment = get_object_or_404(BlogComment, id=comment_id)

        # Only allow user to delete their own comment
        if comment.user != request.user:
            return JsonResponse({"error": "Unauthorized"}, status=403)

        blog = comment.blog
        comment.delete()

        blog.refresh_from_db()

        return JsonResponse({
            "success": True,
            "comments_count": blog.comments_count,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)