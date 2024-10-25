from django.contrib import admin
from .models import Element, Decay, Element_Decay

admin.site.register(Element)
admin.site.register(Decay)
admin.site.register(Element_Decay)