from django.contrib import admin
from .models import Event, Exclusion

admin.site.register(Event) #Event model so we can see it in /admin
admin.site.register(Exclusion)

# Register your models here.
