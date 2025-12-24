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
                    When(interaction_type='view', then=3),
                    When(interaction_type='like', then=1),
                    When(interaction_type='comment', then=2),
                    When(interaction_type='dislike', then=-4),
                    output_field=IntegerField()
                )
            )
        )
        .order_by('-score')
    )

    top_categories = [i['blog__category'] for i in interactions if i['score'] > 0][:2]

    return Blogs.objects.filter(
        category__in=top_categories
    ).exclude(id=exclude_blog_id)[:9]

def get_guest_recommendations(session_key, exclude_blog_id):
    recent = BlogInteraction.objects.filter(
        session_key=session_key,
        interaction_type='view'
    ).order_by('-created')[:9]

    if not recent:
        return Blogs.objects.exclude(id=exclude_blog_id).order_by('-views')[:9]

    categories = [i.blog.category for i in recent]

    return Blogs.objects.filter(
        category__in=categories
    ).exclude(id=exclude_blog_id)[:9]

def home(request):
    return render(request, 'basicApp/home.html')

def blogs(request):
    if not request.session.session_key:
        request.session.create()

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

    preferred_categories = list(set(preferred_categories))

    if preferred_categories:
        all_blogs = Blogs.objects.annotate(
            priority=Case(
                When(category__in=preferred_categories, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ).order_by('-priority', '-views', '-likes_count', '-created')
    else:
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

from django.http import JsonResponse
from django.db.models import Q, Count, Sum, Case, When, IntegerField, F
from django.views.decorators.http import require_http_methods
from collections import Counter
import random

@require_http_methods(["GET"])
def get_next_blogs(request):
    """
    Returns next 5 blogs based on user behavior with category diversity
    """
    current_blog_id = request.GET.get('current_blog_id')
    offset = int(request.GET.get('offset', 0))
    
    if not current_blog_id:
        return JsonResponse({'error': 'current_blog_id is required'}, status=400)
    
    if not request.session.session_key:
        request.session.create()
    
    # Get recommendations based on user type
    if request.user.is_authenticated:
        recommended_blogs = get_scroll_recommendations_user(
            request.user, 
            current_blog_id, 
            offset
        )
        user_reaction = get_user_reactions(request.user, recommended_blogs)
    else:
        recommended_blogs = get_scroll_recommendations_guest(
            request.session.session_key,
            current_blog_id,
            offset
        )
        user_reaction = {}
    
    # Format response
    blogs_data = []
    for blog in recommended_blogs:
        blogs_data.append({
            'id': str(blog.id),
            'title': blog.title,
            'category': blog.category,
            'featureImage': blog.featureImage.url if blog.featureImage else '',
            'content': blog.content,
            'tags': blog.tags,
            'created': blog.created.strftime('%B %d, %Y'),
            'author': blog.author.username if blog.author else 'Anonymous',
            'views': blog.views,
            'likes_count': blog.likes_count,
            'dislikes_count': blog.dislikes_count,
            'comments_count': blog.comments_count,
            'user_reaction': user_reaction.get(str(blog.id)),
        })
    
    return JsonResponse({
        'success': True,
        'blogs': blogs_data,
        'has_more': len(blogs_data) == 5
    })


def get_scroll_recommendations_user(user, exclude_blog_id, offset):
    """
    Smart recommendations for logged-in users with category diversity
    """
    # Get user's interaction history with weighted scores
    interactions = (
        BlogInteraction.objects
        .filter(user=user)
        .values('blog__category')
        .annotate(
            score=Sum(
                Case(
                    When(interaction_type='view', then=3),
                    When(interaction_type='like', then=5),
                    When(interaction_type='comment', then=4),
                    When(interaction_type='dislike', then=-6),
                    output_field=IntegerField()
                )
            )
        )
        .order_by('-score')
    )
    
    # Get top preferred categories (positive scores only)
    preferred_categories = [
        i['blog__category'] for i in interactions if i['score'] > 0
    ]
    
    # Get recently viewed categories to add diversity
    recent_views = BlogInteraction.objects.filter(
        user=user,
        interaction_type='view'
    ).order_by('-created')[:10].values_list('blog__category', flat=True)
    
    recent_category_counts = Counter(recent_views)
    
    # Identify overrepresented categories (viewed more than 3 times recently)
    overrepresented = {cat for cat, count in recent_category_counts.items() if count > 3}
    
    # Get all available categories
    all_categories = [choice[0] for choice in Blogs.CATEGORY]
    
    # Ensure at least one diverse category (not in top preferences or overrepresented)
    diverse_categories = [
        cat for cat in all_categories 
        if cat not in preferred_categories[:2] and cat not in overrepresented
    ]
    
    # If no diverse categories available, use less preferred ones
    if not diverse_categories:
        diverse_categories = [
            cat for cat in all_categories 
            if cat not in preferred_categories[:1]
        ]
    
    # Build the query with weighted distribution
    # 60% from preferred categories, 40% from diverse categories
    if preferred_categories:
        preferred_blogs = Blogs.objects.filter(
            category__in=preferred_categories[:3]
        ).exclude(id=exclude_blog_id).order_by('-views', '-likes_count')
        
        diverse_blogs = Blogs.objects.filter(
            category__in=diverse_categories[:2]
        ).exclude(id=exclude_blog_id).order_by('-views', '-likes_count')
        
        # Take 3 from preferred and 2 from diverse
        blogs_list = list(preferred_blogs[offset:offset+3]) + list(diverse_blogs[offset:offset+2])
        
        # Shuffle to mix them
        random.shuffle(blogs_list)
        
        return blogs_list[:5]
    else:
        # New user - return trending with diversity
        return Blogs.objects.exclude(
            id=exclude_blog_id
        ).order_by('-views', '-likes_count')[offset:offset+5]


def get_scroll_recommendations_guest(session_key, exclude_blog_id, offset):
    """
    Smart recommendations for guest users with category diversity
    """
    # Get recent interactions
    recent_interactions = BlogInteraction.objects.filter(
        session_key=session_key
    ).order_by('-created')[:15]
    
    if not recent_interactions:
        # New guest - return trending blogs with diverse categories
        return get_diverse_trending_blogs(exclude_blog_id, offset)
    
    # Analyze guest preferences
    category_scores = {}
    for interaction in recent_interactions:
        cat = interaction.blog.category
        if cat not in category_scores:
            category_scores[cat] = 0
        
        if interaction.interaction_type == 'view':
            category_scores[cat] += 3
        elif interaction.interaction_type == 'like':
            category_scores[cat] += 5
        elif interaction.interaction_type == 'comment':
            category_scores[cat] += 4
        elif interaction.interaction_type == 'dislike':
            category_scores[cat] -= 6
    
    # Get top categories
    sorted_categories = sorted(
        category_scores.items(), 
        key=lambda x: x[1], 
        reverse=True
    )
    preferred_categories = [cat for cat, score in sorted_categories if score > 0][:3]
    
    # Get recent view categories for diversity check
    recent_views = [
        i.blog.category for i in recent_interactions 
        if i.interaction_type == 'view'
    ][:8]
    recent_category_counts = Counter(recent_views)
    overrepresented = {cat for cat, count in recent_category_counts.items() if count > 2}
    
    # Get diverse categories
    all_categories = [choice[0] for choice in Blogs.CATEGORY]
    diverse_categories = [
        cat for cat in all_categories 
        if cat not in preferred_categories[:2] and cat not in overrepresented
    ]
    
    if not diverse_categories:
        diverse_categories = [
            cat for cat in all_categories 
            if cat not in preferred_categories[:1]
        ]
    
    # Build mixed query
    if preferred_categories:
        preferred_blogs = Blogs.objects.filter(
            category__in=preferred_categories
        ).exclude(id=exclude_blog_id).order_by('-views', '-likes_count')
        
        diverse_blogs = Blogs.objects.filter(
            category__in=diverse_categories[:2]
        ).exclude(id=exclude_blog_id).order_by('-views')
        
        blogs_list = list(preferred_blogs[offset:offset+3]) + list(diverse_blogs[offset:offset+2])
        random.shuffle(blogs_list)
        
        return blogs_list[:5]
    else:
        return get_diverse_trending_blogs(exclude_blog_id, offset)


def get_diverse_trending_blogs(exclude_blog_id, offset):
    """
    Get trending blogs ensuring category diversity
    """
    all_categories = [choice[0] for choice in Blogs.CATEGORY]
    blogs = []
    
    for category in all_categories:
        blog = Blogs.objects.filter(
            category=category
        ).exclude(id=exclude_blog_id).order_by('-views', '-likes_count').first()
        
        if blog:
            blogs.append(blog)
        
        if len(blogs) >= 5:
            break
    
    # If not enough diverse blogs, fill with trending
    if len(blogs) < 5:
        additional = Blogs.objects.exclude(
            id__in=[b.id for b in blogs]
        ).exclude(id=exclude_blog_id).order_by('-views')[:5-len(blogs)]
        blogs.extend(additional)
    
    return blogs[offset:offset+5]


def get_user_reactions(user, blogs):
    """
    Get user's reactions for a list of blogs
    """
    blog_ids = [blog.id for blog in blogs]
    reactions = BlogReaction.objects.filter(
        user=user,
        blog_id__in=blog_ids
    ).values('blog_id', 'reaction')
    
    return {str(r['blog_id']): r['reaction'] for r in reactions}

def scrollView(request):
    """
    Render the scroll view page with initial blog
    """
    # Get initial blog based on user preferences
    if request.user.is_authenticated:
        # Get user's most preferred category
        interactions = (
            BlogInteraction.objects
            .filter(user=request.user)
            .values('blog__category')
            .annotate(
                score=Sum(
                    Case(
                        When(interaction_type='view', then=3),
                        When(interaction_type='like', then=5),
                        When(interaction_type='comment', then=4),
                        When(interaction_type='dislike', then=-6),
                        output_field=IntegerField()
                    )
                )
            )
            .order_by('-score')
            .first()
        )
        
        if interactions and interactions['score'] > 0:
            initial_blog = Blogs.objects.filter(
                category=interactions['blog__category']
            ).order_by('-views').first()
        else:
            initial_blog = Blogs.objects.order_by('-views').first()
    else:
        # Guest user - show trending
        initial_blog = Blogs.objects.order_by('-views').first()
    
    return render(request, 'basicApp/scrollBlog.html', {
        'initial_blog_id': str(initial_blog.id) if initial_blog else ''
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
                tags=tags,
                author=request.user,
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
    
