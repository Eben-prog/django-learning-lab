from django.contrib import admin

from tickets.models import Comment, Ticket


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    raw_id_fields = ("author",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "priority", "created_by", "assigned_to", "created_at")
    list_filter = ("status", "priority")
    search_fields = ("title", "description", "created_by__username")
    raw_id_fields = ("created_by", "assigned_to", "updated_by")
    inlines = [CommentInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "author", "is_internal", "is_system", "created_at")
    list_filter = ("is_internal", "is_system")
    raw_id_fields = ("ticket", "author")
