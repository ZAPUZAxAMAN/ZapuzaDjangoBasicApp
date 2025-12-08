from django.urls import path, include
from .views import dashboard, login_view, logout_view, register_view, activate_account

urlpatterns = [
    path('login/', login_view, name='login' ),
    path('register/', register_view, name='register' ),
    path('logout/', logout_view, name='logout' ),
    path('dashboard/', dashboard, name='dashboard' ),
    path('activate/<uidb64>/<token>/', activate_account, name='activate'),

]