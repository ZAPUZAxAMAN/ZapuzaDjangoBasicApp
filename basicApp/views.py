from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator, EmptyPage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Blogs, BlogReaction, BlogComment, BlogInteraction
from django.http import JsonResponse
from django.db.models import F
from django.db.models import Case, When, IntegerField, Sum, Value

def get_user_feed(user):
    interactions = (
        BlogInteraction.objects
        .filter(user=user)
        .values('blog__category')
        .annotate(
            score=Sum(
                Case(
                    When(interaction_type='view', then=1),
                    When(interaction_type='like', then=3),
                    When(interaction_type='comment', then=4),
                    When(interaction_type='dislike', then=-2),
                    output_field=IntegerField()
                )
            )
        )
        .order_by('-score')
    )

    top_categories = [i['blog__category'] for i in interactions if i['score'] > 0][:3]

    if not top_categories:
        return Blogs.objects.order_by('-views', '-likes_count')

    return Blogs.objects.filter(
        category__in=top_categories
    ).order_by('-views', '-likes_count')


def get_guest_feed(session_key):
    recent = BlogInteraction.objects.filter(
        session_key=session_key,
        interaction_type='view'
    ).order_by('-created')[:5]

    if not recent:
        return Blogs.objects.order_by('-views', '-likes_count')

    categories = [i.blog.category for i in recent]

    return Blogs.objects.filter(
        category__in=categories
    ).order_by('-views', '-likes_count')

def get_user_recommendations(user, exclude_blog_id):
    interactions = (
        BlogInteraction.objects
        .filter(user=user)
        .values('blog__category')
        .annotate(
            score=Sum(
                Case(
                    When(interaction_type='view', then=1),
                    When(interaction_type='like', then=3),
                    When(interaction_type='comment', then=4),
                    When(interaction_type='dislike', then=-2),
                    output_field=IntegerField()
                )
            )
        )
        .order_by('-score')
    )

    top_categories = [i['blog__category'] for i in interactions if i['score'] > 0][:2]

    return Blogs.objects.filter(
        category__in=top_categories
    ).exclude(id=exclude_blog_id)[:5]

def get_guest_recommendations(session_key, exclude_blog_id):
    recent = BlogInteraction.objects.filter(
        session_key=session_key,
        interaction_type='view'
    ).order_by('-created')[:5]

    if not recent:
        return Blogs.objects.exclude(id=exclude_blog_id).order_by('-views')[:5]

    categories = [i.blog.category for i in recent]

    return Blogs.objects.filter(
        category__in=categories
    ).exclude(id=exclude_blog_id)[:5]

def mix_categories(primary_qs, secondary_qs, limit=36, primary_ratio=0.7):
    primary_limit = int(limit * primary_ratio)
    secondary_limit = limit - primary_limit

    primary_items = list(primary_qs[:primary_limit])
    secondary_items = list(
        secondary_qs.exclude(id__in=[b.id for b in primary_items])[:secondary_limit]
    )

    return primary_items + secondary_items

def home(request):
    return render(request, 'basicApp/home.html')


def blogs(request):
    if not request.session.session_key:
        request.session.create()

    # Get preferred categories
    if request.user.is_authenticated:
        preferred_categories = list(
            BlogInteraction.objects
            .filter(user=request.user)
            .values_list('blog__category', flat=True)
        )
    else:
        preferred_categories = list(
            BlogInteraction.objects
            .filter(
                session_key=request.session.session_key,
                interaction_type='view'
            )
            .values_list('blog__category', flat=True)
        )

    # Remove duplicates
    preferred_categories = list(set(preferred_categories))

    # Soft boost preferred categories, NOT filtering others out
    if preferred_categories:
        all_blogs = Blogs.objects.annotate(
            priority=Case(
                When(category__in=preferred_categories, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ).order_by('-priority', '-views', '-likes_count', '-created')
    else:
        # Cold start
        all_blogs = Blogs.objects.order_by('-views', '-likes_count', '-created')

    paginator = Paginator(all_blogs, 9)
    page = request.GET.get('page', 1)

    try:
        blogs_page = paginator.page(page)
    except EmptyPage:
        blogs_page = paginator.page(paginator.num_pages)

    return render(request, 'basicApp/blogs.html', {
        'blogs': blogs_page,
        'paginator': paginator,
    })



def blog(request, id):
    blog_post = get_object_or_404(Blogs, id=id)

    if not request.session.session_key:
        request.session.create()

    Blogs.objects.filter(id=id).update(views=F('views') + 1)

    BlogInteraction.objects.create(
        user=request.user if request.user.is_authenticated else None,
        session_key=None if request.user.is_authenticated else request.session.session_key,
        blog=blog_post,
        interaction_type='view'
    )

    blog_post.refresh_from_db()

    # RECOMMENDATIONS (this is the point of all this work)
    if request.user.is_authenticated:
        related_blogs = get_user_recommendations(request.user, blog_post.id)
    else:
        related_blogs = get_guest_recommendations(
            request.session.session_key,
            blog_post.id
        )

    comments = BlogComment.objects.filter(blog=blog_post).order_by('-created')

    user_reaction = None
    if request.user.is_authenticated:
        reaction = BlogReaction.objects.filter(
            user=request.user,
            blog=blog_post
        ).first()
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
    all_blogs = Blogs.objects.filter(
        author=request.user
    ).order_by('-created')

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

        BlogInteraction.objects.create(
            user=user,
            blog=blog,
            interaction_type=reaction_type
        )

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
        BlogInteraction.objects.create(
            user=request.user,
            blog=blog,
            interaction_type='comment'
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