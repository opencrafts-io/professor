from django.contrib import admin
from .models import CustomUser, Administrator

admin.site.register(CustomUser)
admin.site.register(Administrator)
