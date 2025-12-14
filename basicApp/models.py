from django.core.checks import Tags
from django.db import models
import uuid
from django.utils import timezone
from accounts.models import CustomUser

# Create your models here.
class Blogs(models.Model):
    CATEGORY = [
        ('Technology','Technology'),
        ('Lifestyle','Lifestyle'),
        ('Travel','Travel'),
        ('Food','Food'),
        ('Health','Health'),
        ('Business','Business'),
        ('Education','Education'),
        ('Entertainment','Entertainment'),
        ('Other','Other'),
    ]
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    title = models.CharField(max_length=256)
    category = models.CharField(max_length=100,choices=CATEGORY)
    featureImage = models.ImageField(upload_to='images/',default='default.png')
    content = models.TextField()
    tags = models.CharField(max_length=256)
    created = models.DateTimeField(default=timezone.now)

    views = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    dislikes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

class BlogReaction(models.Model):
    LIKE = "like"
    DISLIKE = "dislike"

    REACTION_CHOICES = [
        (LIKE, "Like"),
        (DISLIKE, "Dislike"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    blog = models.ForeignKey(Blogs, on_delete=models.CASCADE, related_name="reactions")
    reaction = models.CharField(max_length=10, choices=REACTION_CHOICES)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'blog')  # one reaction per user

class BlogComment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    blog = models.ForeignKey(Blogs, on_delete=models.CASCADE, related_name="comments")
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} on {self.blog}"
