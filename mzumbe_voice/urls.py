from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from voice import views

urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),
    
    # Public pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('health/', views.health_check, name='health_check'),   # health check for uptime monitoring
    path('qr-code/', views.generate_qr_code, name='qr_code'),   # QR code generator
    
    # Staff login (shared for all staff: VC, director, HOD, admin)
    path('staff/login/', views.staff_login, name='staff_login'),
    
    # Student pages
    path('student/login/', views.student_login, name='student_login'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/submit/', views.submit_suggestion, name='submit_suggestion'),
    path('student/lock/', views.student_lock, name='student_lock'),
    path('student/new-suggestion/', views.new_suggestion, name='new_suggestion'),
    path('student/logout/', views.student_logout, name='student_logout'),
    
    # Vice Chancellor pages
    path('vc/dashboard/', views.vice_dashboard, name='vice_dashboard'),
    path('vc/suggestions/', views.vice_suggestions, name='vice_suggestions'),
    path('vc/edit/<int:sug_id>/', views.vice_edit_suggestion, name='vice_edit_suggestion'),
    path('vc/update/<int:sug_id>/', views.vice_update_suggestion, name='vice_update_suggestion'),
    path('vc/delete/<int:sug_id>/', views.vice_delete_suggestion, name='vice_delete'),
    path('vc/forward/<int:sug_id>/', views.vc_forward_suggestion, name='vc_forward'),
    path('vc/resolve/<int:sug_id>/', views.vc_resolve_suggestion, name='vc_resolve'),
    path('vc/feedback/<int:sug_id>/', views.vc_feedback_suggestion, name='vc_feedback'),
    
    # Director pages
    path('director/dashboard/<str:faculty_name>/', views.director_dashboard, name='director_dashboard'),
    path('director/forward/<int:sug_id>/', views.director_forward_suggestion, name='director_forward'),
    path('director/resolve/<int:sug_id>/', views.director_resolve_suggestion, name='director_resolve'),
    path('director/feedback/<int:sug_id>/', views.director_feedback_suggestion, name='director_feedback'),
    path('director/suggestions/<str:faculty_name>/', views.director_suggestions, name='director_suggestions'),
    path('director/edit/<str:faculty_name>/<int:sug_id>/', views.director_edit_suggestion, name='director_edit_suggestion'),
    path('director/update/<str:faculty_name>/<int:sug_id>/', views.director_update_suggestion, name='director_update_suggestion'),
    path('director/delete/<int:sug_id>/', views.director_delete_suggestion, name='director_delete'),
    path('director/generic/', views.director_generic, name='director_generic'),
    
    # HOD pages
    path('hod/dashboard/<str:faculty_name>/', views.hod_dashboard, name='hod_dashboard'),
    path('hod/forward/<int:sug_id>/', views.hod_forward_suggestion, name='hod_forward'),
    path('hod/resolve/<int:sug_id>/', views.hod_resolve_suggestion, name='hod_resolve'),
    path('hod/feedback/<int:sug_id>/', views.hod_feedback_suggestion, name='hod_feedback'),
    path('hod/suggestions/<str:faculty_name>/', views.hod_suggestions, name='hod_suggestions'),
    path('hod/edit/<str:faculty_name>/<int:sug_id>/', views.hod_edit_suggestion, name='hod_edit_suggestion'),
    path('hod/update/<str:faculty_name>/<int:sug_id>/', views.hod_update_suggestion, name='hod_update_suggestion'),
    path('hod/delete/<int:sug_id>/', views.hod_delete_suggestion, name='hod_delete'),
    path('hod/generic/', views.hod_generic, name='hod_generic'),
    
    # Accommodation director pages
    path('accommodation/dashboard/', views.accommodation_dashboard, name='accommodation_dashboard'),
    path('accommodation/suggestions/', views.accommodation_suggestions, name='accommodation_suggestions'),
    path('accommodation/forward/<int:sug_id>/', views.accommodation_forward_suggestion, name='accommodation_forward'),
    path('accommodation/resolve/<int:sug_id>/', views.accommodation_resolve_suggestion, name='accommodation_resolve'),
    path('accommodation/feedback/<int:sug_id>/', views.accommodation_feedback_suggestion, name='accommodation_feedback'),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)