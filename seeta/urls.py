from django.contrib import admin
from django.urls import path, re_path
from myapp import views 
from django.conf import settings 
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Main pages
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('contact/', views.contact, name='contact'),
    path('cart/', views.cart, name='cart'),
    path('cart/add/<str:unique_code>/', views.add_to_cart, name='add_to_cart'),
    path('product/<str:unique_code>/', views.product_detail, name='product_detail'),
    path('cart/inquiry/', views.send_inquiry, name='send_inquiry'),
    path('profile/inquiries/', views.client_inquiries, name='client_inquiries'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # Auth pages
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
]


urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]


# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)