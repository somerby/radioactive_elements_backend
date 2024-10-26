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
    path('', views.getServices, name = 'home'),
    path('element/<int:element_id>/', views.getService, name = 'ElementID'),
    path('decay/<int:decay_id>/', views.getDecay, name = 'decay'),
    path('add_element_to_decay/', views.addElementToDecay, name = 'add_element_to_decay'),
    path('delete_decay/', views.deleteDecay, name = 'delete_decay')
]