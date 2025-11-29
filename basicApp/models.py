from django.core.checks import Tags
from django.db import models
import uuid
from django.utils import timezone
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


    def __str__(self):
        return self.title