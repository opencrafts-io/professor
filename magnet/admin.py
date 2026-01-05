from django.contrib import admin
from .models import MagnetScrappingCommand


class MagnetScrappingCommandAdmin(admin.ModelAdmin):
    list_display = [
        "institution",
        "command_id",
        "name",
        "description",
        "requires_interaction",
        "created_at",
    ]

    list_filter = [
        "institution",
        "command_id",
        "name",
        "requires_interaction",
        "created_at",
    ]


admin.site.register(
    MagnetScrappingCommand,
    MagnetScrappingCommandAdmin,
)
