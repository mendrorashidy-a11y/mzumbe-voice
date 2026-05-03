from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Faculty, User, Suggestion, SuggestionChain, Communication, UserSession
from .models import Student, ViceChancellor, Director, HOD, AccommodationDirector  # proxy models

# ==================================================
# Faculty Admin
# ==================================================
@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('faculty_id', 'name', 'description', 'created_at')
    list_display_links = ('name',)
    search_fields = ('name', 'description')
    ordering = ('name',)


# ==================================================
# Custom User Admin (extends Django's UserAdmin)
# This remains unchanged and manages all users.
# ==================================================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'faculty', 'is_staff')
    list_filter = ('role', 'faculty', 'is_staff', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'faculty')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('role', 'faculty')}),
    )


# ==================================================
# Role‑specific Proxy Admins (with Add/Change buttons)
# ==================================================
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'faculty', 'is_active')
    list_filter = ('is_active', 'faculty')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role='student')

    def save_model(self, request, obj, form, change):
        obj.role = 'student'
        obj.is_staff = False
        super().save_model(request, obj, form, change)


@admin.register(ViceChancellor)
class ViceChancellorAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role='vc')

    def save_model(self, request, obj, form, change):
        obj.role = 'vc'
        obj.is_staff = True
        super().save_model(request, obj, form, change)


@admin.register(Director)
class DirectorAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'faculty', 'is_active')
    list_filter = ('faculty', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role='director')

    def save_model(self, request, obj, form, change):
        obj.role = 'director'
        obj.is_staff = True
        super().save_model(request, obj, form, change)


@admin.register(HOD)
class HODAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'faculty', 'is_active')
    list_filter = ('faculty', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role='hod')

    def save_model(self, request, obj, form, change):
        obj.role = 'hod'
        obj.is_staff = True
        super().save_model(request, obj, form, change)


@admin.register(AccommodationDirector)
class AccommodationDirectorAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role='accommodation_director')

    def save_model(self, request, obj, form, change):
        obj.role = 'accommodation_director'
        obj.is_staff = True
        super().save_model(request, obj, form, change)


# ==================================================
# Inlines for Suggestion
# ==================================================
class CommunicationInline(admin.TabularInline):
    model = Communication
    extra = 1
    fields = ('user', 'message', 'created_at')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user',)


class SuggestionChainInline(admin.TabularInline):
    model = SuggestionChain
    extra = 1
    fields = ('from_user', 'to_user', 'action', 'notes', 'created_at')
    readonly_fields = ('created_at',)
    raw_id_fields = ('from_user', 'to_user')


# ==================================================
# Suggestion Admin
# ==================================================
@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ('suggestion_id', 'student', 'category', 'visibility', 'faculty', 'status', 'current_handler', 'created_at')
    list_filter = ('status', 'category', 'visibility', 'faculty', 'created_at')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'description', 'feedback')
    raw_id_fields = ('student', 'current_handler', 'faculty')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    fieldsets = (
        ('Suggestion Details', {
            'fields': ('student', 'category', 'description', 'visibility', 'faculty', 'attachment')
        }),
        ('Workflow', {
            'fields': ('status', 'current_handler', 'feedback')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [CommunicationInline, SuggestionChainInline]


# ==================================================
# SuggestionChain Admin
# ==================================================
@admin.register(SuggestionChain)
class SuggestionChainAdmin(admin.ModelAdmin):
    list_display = ('chain_id', 'suggestion', 'from_user', 'to_user', 'action', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('suggestion__description', 'from_user__username', 'to_user__username')
    raw_id_fields = ('suggestion', 'from_user', 'to_user')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


# ==================================================
# Communication Admin
# ==================================================
@admin.register(Communication)
class CommunicationAdmin(admin.ModelAdmin):
    list_display = ('comm_id', 'suggestion', 'user', 'message_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('message', 'user__username', 'suggestion__description')
    raw_id_fields = ('suggestion', 'user')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message (preview)'


# ==================================================
# UserSession Admin (optional)
# ==================================================
@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'token', 'expires_at', 'created_at')
    list_filter = ('created_at', 'expires_at')
    search_fields = ('user__username', 'token')
    raw_id_fields = ('user',)
    ordering = ('-created_at',)