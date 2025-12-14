from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import BlogReaction, Blogs
from .models import BlogComment

@receiver(post_save, sender=BlogReaction)
def update_reaction_counts(sender, instance, created, **kwargs):
    blog = instance.blog
    blog.likes_count = blog.reactions.filter(reaction="like").count()
    blog.dislikes_count = blog.reactions.filter(reaction="dislike").count()
    blog.save(update_fields=["likes_count", "dislikes_count"])

@receiver(post_delete, sender=BlogReaction)
def update_reaction_counts_on_delete(sender, instance, **kwargs):
    blog = instance.blog
    blog.likes_count = blog.reactions.filter(reaction="like").count()
    blog.dislikes_count = blog.reactions.filter(reaction="dislike").count()
    blog.save(update_fields=["likes_count", "dislikes_count"])


@receiver(post_save, sender=BlogComment)
def update_comment_count(sender, instance, created, **kwargs):
    if created:
        blog = instance.blog
        blog.comments_count += 1
        blog.save(update_fields=["comments_count"])

@receiver(post_delete, sender=BlogComment)
def reduce_comment_count(sender, instance, **kwargs):
    blog = instance.blog
    blog.comments_count -= 1
    blog.save(update_fields=["comments_count"])
