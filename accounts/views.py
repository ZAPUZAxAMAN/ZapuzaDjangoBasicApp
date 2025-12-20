from django.contrib.auth import authenticate, login, logout
from .models import CustomUser
from .forms import RegisterForm
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from basicApp.models import Blogs, BlogComment, BlogReaction

# Create your views here.
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user_obj = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            messages.error(request, 'No account found with this email.')
            return render(request, 'accounts/login.html')

        if not user_obj.is_active:
            messages.error(request, 'Your account is not activated yet. Please check your email.')
            return render(request, 'accounts/login.html')

        user = authenticate(request, username=user_obj.username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, 'Welcome back!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid password.')
            return render(request, 'accounts/login.html')

    return render(request, 'accounts/login.html')

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.set_password(form.cleaned_data['password'])
            user.save()

            send_activation_email(request, user)

            messages.success(request, "Account created! Check your email to activate your account.")
            return redirect('login')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})

@login_required(login_url='/accounts/login/')
def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('login')

@login_required(login_url='/accounts/login/')
def dashboard(request):
    user = request.user

    # Base queryset: blogs created by the user
    user_blogs = Blogs.objects.filter(author=user)

    # ---- Core Stats ----
    total_blogs = user_blogs.count()

    total_views = user_blogs.aggregate(
        total=Sum('views')
    )['total'] or 0

    total_comments = BlogComment.objects.filter(
        blog__author=user
    ).count()

    total_likes = BlogReaction.objects.filter(
        blog__author=user,
        reaction='like'
    ).count()

    # ---- Recent Blogs ----
    recent_blogs = user_blogs.order_by('-created')[:5]

    # ---- Most Viewed Blog ----
    most_viewed_blog = user_blogs.order_by('-views').first()
    most_viewed_count = most_viewed_blog.views if most_viewed_blog else 0

    # ---- Optional / Placeholder Metrics ----
    total_earnings = 0        # you don’t have monetization yet
    total_shares = 0          # no sharing feature yet
    total_drafts = 0          # no draft field in model yet

    context = {
        'total_blogs': total_blogs,
        'total_views': total_views,
        'total_comments': total_comments,
        'total_likes': total_likes,
        'recent_blogs': recent_blogs,
        'most_viewed_count': most_viewed_count,
        'total_earnings': total_earnings,
        'total_shares': total_shares,
        'total_drafts': total_drafts,
    }

    return render(request, 'accounts/dashboard.html', context)



@login_required(login_url='/accounts/login/')
def profile(request):
    if request.method == 'POST':
        # Get the form data
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()

        user = request.user
        user.first_name = first_name
        user.last_name = last_name

        try:
            user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')

        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
            return render(request, 'accounts/profile.html')

    return render(request, 'accounts/profile.html')

@login_required(login_url='/accounts/login/')
def comments(request):
    # Fetch comments on blogs owned by logged-in user
    user_comments = BlogComment.objects.filter(
        blog__author=request.user
    ).select_related('blog', 'user').order_by('-created')
    total_comments = user_comments.count()
    paginator = Paginator(user_comments, 10)  # adjust per page
    page = request.GET.get('page', 1)
    print(user_comments)
    try:
        comments_page = paginator.page(page)
    except:
        comments_page = paginator.page(paginator.num_pages)

    print(comments_page)
    context = {
        'comments': comments_page,
        'total_comments': total_comments,
    }
    return render(request, 'accounts/comments.html', context)

def activate_account(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, CustomUser.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Your account has been activated! You can now log in.")
        return redirect('login')

    messages.error(request, "Activation link is invalid or expired.")
    return redirect('login')


def send_activation_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    activation_link = f"http://{request.get_host()}/accounts/activate/{uid}/{token}/"

    subject = "Activate your account"
    message = f"Hi {user.username}, click the link to activate your account:\n{activation_link}"

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
    )
