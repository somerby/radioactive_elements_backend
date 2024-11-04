"""
URL configuration for radioactive_elements project.

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
from radioactive_elements_app import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/elements', views.elementsMethods.as_view(), name = 'elements'),
    path('api/elements/<int:element_id>', views.elementMethods.as_view(), name = 'element'),
    path('api/elements/<int:element_id>/add_img', views.elementAddImg, name = 'elementAddImg'),

    path('api/decays', views.decaysMethods.as_view(), name = 'decays'),
    path('api/decay/<int:decay_id>', views.decayMethods.as_view(), name = 'decay'),
    path('api/decay/<int:decay_id>/forming', views.formingDecay.as_view(), name = 'decayForm'),
    path('api/decay/<int:decay_id>/moderate', views.moderateDecay.as_view(), name = 'decayForm'),

    path('api/element_decay/<int:element_id>/<int:decay_id>', views.elementDecayMethods.as_view(), name='element_decay'),

    path('api/user/registration', views.userRegistration, name='userRegistration'),
    path('api/user/account/<str:username>', views.userAccount, name='userAccount'),
    path('api/user/authentication', views.userAuthentication, name='userAuthentication'),
    path('api/user/deauthentication', views.userDeauthentication, name='userDauthentication')
]