from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core import validators  # <-- added for custom validator
from django.conf import settings

# ==============================
# 1. Faculties (lookup table)
# ==============================
class Faculty(models.Model):
    faculty_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=20, unique=True, help_text="SOB, SOPAM, FOL, FSS, FST, IDS")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'faculties'
        indexes = [models.Index(fields=['name'], name='idx_faculties_name')]
        ordering = ['name']

    def __str__(self):
        return self.name


# ==============================
# 2. Custom User (extends Django's AbstractUser)
# ==============================
class User(AbstractUser):
    # Override username to allow slash (/) and other safe characters
    username = models.CharField(
        max_length=150,
        unique=True,
        help_text='Required. Letters, digits, slash (/), dot (.), underscore (_), and hyphen (-) only.',
        validators=[
            validators.RegexValidator(
                regex=r'^[\w./-]+$',   # allows letters, digits, underscore, slash, dot, hyphen
                message='Username can only contain letters, digits, slash (/), dot (.), underscore (_), and hyphen (-).',
                code='invalid'
            )
        ],
        error_messages={
            'unique': "A user with that username already exists.",
        }
    )

    ROLE_CHOICES = [
        ('student', 'Student'),
        ('admin', 'Admin'),
        ('vc', 'Vice Chancellor'),
        ('director', 'Director'),
        ('hod', 'Head of Department'),
        ('technician', 'Technician'),
        ('accommodation_director', 'Director of Accommodation'),
    ]
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='student')
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['username'], name='idx_users_username'),
            models.Index(fields=['role'], name='idx_users_role'),
            models.Index(fields=['faculty'], name='idx_users_faculty'),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


# ==============================
# 3. Proxy Models for Role‑specific Admin Sections
# ==============================
class Student(User):
    class Meta:
        proxy = True
        verbose_name = 'Student'
        verbose_name_plural = 'Students'


class ViceChancellor(User):
    class Meta:
        proxy = True
        verbose_name = 'Vice Chancellor'
        verbose_name_plural = 'Vice Chancellors'


class Director(User):
    class Meta:
        proxy = True
        verbose_name = 'Director'
        verbose_name_plural = 'Directors'


class HOD(User):
    class Meta:
        proxy = True
        verbose_name = 'Head of Department'
        verbose_name_plural = 'Heads of Department'


class AccommodationDirector(User):
    class Meta:
        proxy = True
        verbose_name = 'Director of Accommodation'
        verbose_name_plural = 'Directors of Accommodation'


# ==============================
# 4. Suggestions (main table)
# ==============================
class Suggestion(models.Model):
    CATEGORY_CHOICES = [
        ('welfare', 'Welfare'),
        ('gender', 'Gender Issue'),
        ('academic', 'Academic'),
        ('technical', 'Technical'),
        ('other', 'Other'),
        ('accommodation', 'Accommodation'),
    ]
    VISIBILITY_CHOICES = [
        ('confidential', 'Confidential'),
        ('open', 'Open'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('forwarded', 'Forwarded'),
        ('resolved', 'Resolved'),
    ]

    suggestion_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='suggestions')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    visibility = models.CharField(max_length=15, choices=VISIBILITY_CHOICES)
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True)
    attachment = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    current_handler = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_suggestions')
    feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'suggestions'
        indexes = [
            models.Index(fields=['student'], name='idx_suggestions_student'),
            models.Index(fields=['status'], name='idx_suggestions_status'),
            models.Index(fields=['current_handler'], name='idx_suggestions_handler'),
            models.Index(fields=['visibility'], name='idx_suggestions_visibility'),
            models.Index(fields=['faculty'], name='idx_suggestions_faculty'),
            models.Index(fields=['created_at'], name='idx_suggestions_created'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Suggestion #{self.suggestion_id} - {self.student.username}"


# ==============================
# 5. Suggestion Chain (forwarding history)
# ==============================
class SuggestionChain(models.Model):
    ACTION_CHOICES = [
        ('forwarded', 'Forwarded'),
        ('resolved', 'Resolved'),
    ]

    chain_id = models.AutoField(primary_key=True)
    suggestion = models.ForeignKey(Suggestion, on_delete=models.CASCADE, related_name='chain_entries')
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='forwarded_from')
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='forwarded_to')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'suggestion_chain'
        indexes = [
            models.Index(fields=['suggestion'], name='idx_chain_suggestion'),
            models.Index(fields=['from_user'], name='idx_chain_from_user'),
            models.Index(fields=['to_user'], name='idx_chain_to_user'),
        ]
        ordering = ['created_at']

    def __str__(self):
        return f"Chain #{self.chain_id} for Suggestion {self.suggestion.suggestion_id}"


# ==============================
# 6. Communications (internal notes)
# ==============================
class Communication(models.Model):
    comm_id = models.AutoField(primary_key=True)
    suggestion = models.ForeignKey(Suggestion, on_delete=models.CASCADE, related_name='communications')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='communications')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'communications'
        indexes = [
            models.Index(fields=['suggestion'], name='idx_comm_suggestion'),
            models.Index(fields=['user'], name='idx_comm_user'),
        ]
        ordering = ['created_at']

    def __str__(self):
        return f"Comm on Suggestion {self.suggestion.suggestion_id} by {self.user.username}"


# ==============================
# 7. User Sessions (optional)
# ==============================
class UserSession(models.Model):
    session_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sessions')
    token = models.CharField(max_length=255, unique=True, blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['user'], name='idx_sessions_user'),
            models.Index(fields=['token'], name='idx_sessions_token'),
        ]

    def __str__(self):
        return f"Session for {self.user.username}"