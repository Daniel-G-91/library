"""
URL configuration for library project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from library_db.views import home_view, sign_up, log_in, library_view, return_book, extend_book, borrow_book, log_out

urlpatterns = [
    path("admin/", admin.site.urls),
    path('library/', home_view, name='home'),
    path('library/signup/', sign_up, name="sign-up"),
    path('library/login/', log_in, name="login"),
    path('library/app/', library_view, name='library'),
    path('library/app/borrow/', borrow_book, name="borrow"),
    path('library/app/extend/', extend_book, name="extend"),
    path('library/app/return/', return_book, name="return"),
    path('library/app/logout/', log_out, name="logout")

]
