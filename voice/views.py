from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse   # Added HttpResponse
from django.db import models
from django.utils import timezone
import json
import os

from .models import Suggestion, Faculty, User
from django.core.files.storage import default_storage
from django.conf import settings

# ========== Public pages ==========
def home(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

# ========== Staff / Admin / Director / HOD / VC / Accommodation login ==========
def staff_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            if user.role == 'vc':
                return redirect('vice_dashboard')
            elif user.role == 'director':
                if user.faculty:
                    return redirect('director_dashboard', faculty_name=user.faculty.name.lower())
                else:
                    return redirect('director_generic')
            elif user.role == 'hod':
                if user.faculty:
                    return redirect('hod_dashboard', faculty_name=user.faculty.name.lower())
                else:
                    return redirect('hod_generic')
            elif user.role == 'accommodation_director':
                return redirect('accommodation_dashboard')
            else:
                return redirect('/admin/')
        else:
            return render(request, 'staff_login.html', {'error': 'Invalid staff credentials.'})
    return render(request, 'staff_login.html')

# ========== Student views ==========
def student_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and not user.is_staff:
            login(request, user)
            return redirect('student_dashboard')
        else:
            return render(request, 'student/student_login.html', {'error': 'Invalid student credentials.'})
    return render(request, 'student/student_login.html')

@login_required(login_url='student_login')
def student_dashboard(request):
    if request.user.is_staff:
        return redirect('staff_login')
    suggestions = Suggestion.objects.filter(student=request.user).order_by('-created_at')
    total_submitted = suggestions.count()
    resolved_count = suggestions.filter(status='resolved').count()
    pending_count = suggestions.filter(status='pending').count()
    context = {
        'suggestions': suggestions,
        'total_submitted': total_submitted,
        'resolved_count': resolved_count,
        'pending_count': pending_count,
    }
    return render(request, 'student/student_dashboard.html', context)

@login_required(login_url='student_login')
def new_suggestion(request):
    if request.user.is_staff:
        return redirect('staff_login')
    return render(request, 'student/new_suggestion.html')

@login_required
def submit_suggestion(request):
    if request.method == 'POST' and not request.user.is_staff:
        category = request.POST.get('category')
        description = request.POST.get('description')
        visibility = request.POST.get('visibility')
        faculty_name = request.POST.get('faculty') if visibility == 'open' else None
        attachment = request.FILES.get('attachment')
        faculty_obj = None
        if faculty_name:
            faculty_obj, _ = Faculty.objects.get_or_create(name=faculty_name)

        # Determine current_handler
        current_handler = None
        if category == 'accommodation':
            # Assign to the first accommodation director
            acc_dir = User.objects.filter(role='accommodation_director').first()
            if acc_dir:
                current_handler = acc_dir

        sug = Suggestion.objects.create(
            student=request.user,
            category=category,
            description=description,
            visibility=visibility,
            faculty=faculty_obj,
            status='pending',
            current_handler=current_handler,
        )
        if attachment:
            path = default_storage.save(f'suggestions/{request.user.id}_{attachment.name}', attachment)
            sug.attachment = path
            sug.save()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': 'Suggestion submitted!'})
        messages.success(request, 'Suggestion submitted.')
        return redirect('student_dashboard')
    return redirect('student_dashboard')

@login_required
def student_lock(request):
    logout(request)
    messages.info(request, 'Your account has been locked. Please log in again.')
    return redirect('student_login')

@login_required
def student_logout(request):
    logout(request)
    return redirect('home')

# ========== Vice Chancellor views ==========
def is_vc(user):
    return user.is_authenticated and user.role == 'vc'

@login_required
@user_passes_test(is_vc)
def vice_dashboard(request):
    """VC dashboard – only statistics (no suggestion list)"""
    suggestions_queryset = Suggestion.objects.filter(
        models.Q(visibility='confidential') | models.Q(current_handler=request.user)
    )
    total_confidential = suggestions_queryset.filter(visibility='confidential').count()
    pending_count = suggestions_queryset.filter(status='pending').count()
    forwarded_count = suggestions_queryset.filter(status='forwarded').count()
    resolved_count = suggestions_queryset.filter(status='resolved').count()
    context = {
        'total_confidential': total_confidential,
        'pending_count': pending_count,
        'forwarded_count': forwarded_count,
        'resolved_count': resolved_count,
    }
    return render(request, 'vice/vice_dashboard.html', context)

@login_required
@user_passes_test(is_vc)
def vice_suggestions(request):
    """List all suggestions that the VC can see (confidential + assigned to VC)"""
    suggestions = Suggestion.objects.filter(
        models.Q(visibility='confidential') | models.Q(current_handler=request.user)
    ).order_by('-created_at')
    forward_targets = User.objects.filter(role__in=['director', 'hod']).select_related('faculty')
    context = {
        'suggestions': suggestions,
        'forward_targets': forward_targets,
    }
    return render(request, 'vice/vice_suggestion.html', context)

@login_required
@user_passes_test(is_vc)
def vc_forward_suggestion(request, sug_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            target_id = data.get('target_user_id')
            suggestion = Suggestion.objects.get(pk=sug_id)
            target_user = User.objects.get(pk=target_id)
            suggestion.status = 'forwarded'
            suggestion.current_handler = target_user
            suggestion.feedback = f"Forwarded to {target_user.get_full_name() or target_user.username} on {timezone.now()}"
            suggestion.save()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

@login_required
@user_passes_test(is_vc)
def vc_resolve_suggestion(request, sug_id):
    if request.method == 'POST':
        try:
            suggestion = Suggestion.objects.get(pk=sug_id)
            suggestion.status = 'resolved'
            suggestion.feedback = f"Resolved by VC on {timezone.now()}"
            suggestion.save()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

@login_required
@user_passes_test(is_vc)
def vc_feedback_suggestion(request, sug_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            feedback_text = data.get('feedback')
            suggestion = Suggestion.objects.get(pk=sug_id)
            suggestion.feedback = feedback_text
            suggestion.save()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

# ========== Director views ==========
def is_director(user):
    return user.is_authenticated and user.role == 'director'

@login_required
@user_passes_test(is_director)
def director_dashboard(request, faculty_name):
    suggestions = Suggestion.objects.filter(
        models.Q(current_handler=request.user) |
        models.Q(visibility='open', faculty=request.user.faculty)
    ).order_by('-created_at')
    total_assigned = suggestions.count()
    pending_count = suggestions.filter(status='pending').count()
    forwarded_count = suggestions.filter(status='forwarded').count()
    resolved_count = suggestions.filter(status='resolved').count()
    vc_user = User.objects.filter(role='vc').first()
    hod_user = User.objects.filter(role='hod', faculty=request.user.faculty).first()
    forward_targets = []
    if vc_user:
        forward_targets.append(vc_user)
    if hod_user:
        forward_targets.append(hod_user)
    context = {
        'suggestions': suggestions,
        'total_assigned': total_assigned,
        'pending_count': pending_count,
        'forwarded_count': forwarded_count,
        'resolved_count': resolved_count,
        'forward_targets': forward_targets,
        'faculty': request.user.faculty,
        'faculty_name': faculty_name,
        'user': request.user,
    }
    return render(request, 'director/director_dashboard.html', context)

@login_required
@user_passes_test(is_director)
def director_forward_suggestion(request, sug_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            target_id = data.get('target_user_id')
            suggestion = Suggestion.objects.get(pk=sug_id)
            if not (suggestion.current_handler == request.user or
                    (suggestion.visibility == 'open' and suggestion.faculty == request.user.faculty)):
                return JsonResponse({'ok': False, 'error': 'Permission denied'}, status=403)
            target_user = User.objects.get(pk=target_id)
            suggestion.status = 'forwarded'
            suggestion.current_handler = target_user
            suggestion.feedback = f"Forwarded to {target_user.get_full_name() or target_user.username} on {timezone.now()}"
            suggestion.save()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

@login_required
@user_passes_test(is_director)
def director_resolve_suggestion(request, sug_id):
    if request.method == 'POST':
        try:
            suggestion = Suggestion.objects.get(pk=sug_id)
            if not (suggestion.current_handler == request.user or
                    (suggestion.visibility == 'open' and suggestion.faculty == request.user.faculty)):
                return JsonResponse({'ok': False, 'error': 'Permission denied'}, status=403)
            suggestion.status = 'resolved'
            suggestion.feedback = f"Resolved by Director {request.user.get_full_name() or request.user.username} on {timezone.now()}"
            suggestion.save()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

@login_required
@user_passes_test(is_director)
def director_feedback_suggestion(request, sug_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            feedback_text = data.get('feedback')
            suggestion = Suggestion.objects.get(pk=sug_id)
            if not (suggestion.current_handler == request.user or
                    (suggestion.visibility == 'open' and suggestion.faculty == request.user.faculty)):
                return JsonResponse({'ok': False, 'error': 'Permission denied'}, status=403)
            suggestion.feedback = feedback_text
            suggestion.save()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

@login_required
@user_passes_test(is_director)
def director_suggestions(request, faculty_name):
    suggestions = Suggestion.objects.filter(
        models.Q(current_handler=request.user) |
        models.Q(visibility='open', faculty=request.user.faculty)
    ).order_by('-created_at')
    vc_user = User.objects.filter(role='vc').first()
    hod_user = User.objects.filter(role='hod', faculty=request.user.faculty).first()
    forward_targets = []
    if vc_user:
        forward_targets.append(vc_user)
    if hod_user:
        forward_targets.append(hod_user)
    context = {
        'suggestions': suggestions,
        'forward_targets': forward_targets,
        'faculty': request.user.faculty,
        'faculty_name': faculty_name,
        'user': request.user,
    }
    return render(request, 'director/director_suggestion.html', context)

@login_required
@user_passes_test(is_director)
def director_edit_suggestion(request, faculty_name, sug_id):
    suggestion = get_object_or_404(Suggestion, pk=sug_id)
    if not (suggestion.current_handler == request.user or
            (suggestion.visibility == 'open' and suggestion.faculty == request.user.faculty)):
        messages.error(request, 'You do not have permission to edit this suggestion.')
        return redirect('director_suggestions', faculty_name=faculty_name)
    faculties = Faculty.objects.all()
    context = {
        'suggestion': suggestion,
        'faculties': faculties,
        'faculty': request.user.faculty,
        'faculty_name': faculty_name,
    }
    return render(request, 'director/director_edit_suggestion.html', context)

@login_required
@user_passes_test(is_director)
def director_update_suggestion(request, faculty_name, sug_id):
    if request.method == 'POST':
        suggestion = get_object_or_404(Suggestion, pk=sug_id)
        if not (suggestion.current_handler == request.user or
                (suggestion.visibility == 'open' and suggestion.faculty == request.user.faculty)):
            messages.error(request, 'Permission denied.')
            return redirect('director_suggestions', faculty_name=faculty_name)
        suggestion.category = request.POST.get('category')
        suggestion.description = request.POST.get('description')
        suggestion.visibility = request.POST.get('visibility')
        suggestion.feedback = request.POST.get('feedback')
        suggestion.status = request.POST.get('status')
        faculty_id = request.POST.get('faculty')
        if faculty_id:
            suggestion.faculty = Faculty.objects.get(pk=faculty_id)
        else:
            suggestion.faculty = None
        suggestion.save()
        messages.success(request, 'Suggestion updated successfully.')
        return redirect('director_suggestions', faculty_name=faculty_name)
    return redirect('director_suggestions', faculty_name=faculty_name)

@login_required
@user_passes_test(is_director)
def director_delete_suggestion(request, sug_id):
    if request.method == 'POST':
        try:
            suggestion = Suggestion.objects.get(pk=sug_id)
            if not (suggestion.current_handler == request.user or
                    (suggestion.visibility == 'open' and suggestion.faculty == request.user.faculty)):
                return JsonResponse({'ok': False, 'error': 'Permission denied'}, status=403)
            suggestion.delete()
            return JsonResponse({'ok': True})
        except Suggestion.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Suggestion not found'})
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

def director_generic(request):
    return render(request, 'director/director_generic.html')

# ========== HOD views ==========
def is_hod(user):
    return user.is_authenticated and user.role == 'hod'

@login_required
@user_passes_test(is_hod)
def hod_dashboard(request, faculty_name):
    suggestions = Suggestion.objects.filter(current_handler=request.user).order_by('-created_at')
    total_assigned = suggestions.count()
    pending_count = suggestions.filter(status='pending').count()
    forwarded_count = suggestions.filter(status='forwarded').count()
    resolved_count = suggestions.filter(status='resolved').count()
    vc_user = User.objects.filter(role='vc').first()
    dir_user = User.objects.filter(role='director', faculty=request.user.faculty).first()
    forward_targets = []
    if vc_user:
        forward_targets.append(vc_user)
    if dir_user:
        forward_targets.append(dir_user)
    context = {
        'suggestions': suggestions,
        'total_assigned': total_assigned,
        'pending_count': pending_count,
        'forwarded_count': forwarded_count,
        'resolved_count': resolved_count,
        'forward_targets': forward_targets,
        'faculty': request.user.faculty,
        'faculty_name': faculty_name,
        'user': request.user,
    }
    return render(request, 'hod/hod_dashboard.html', context)

@login_required
@user_passes_test(is_hod)
def hod_forward_suggestion(request, sug_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            target_id = data.get('target_user_id')
            suggestion = Suggestion.objects.get(pk=sug_id)
            target_user = User.objects.get(pk=target_id)
            suggestion.status = 'forwarded'
            suggestion.current_handler = target_user
            suggestion.feedback = f"Forwarded to {target_user.get_full_name() or target_user.username} on {timezone.now()}"
            suggestion.save()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

@login_required
@user_passes_test(is_hod)
def hod_resolve_suggestion(request, sug_id):
    if request.method == 'POST':
        try:
            suggestion = Suggestion.objects.get(pk=sug_id)
            suggestion.status = 'resolved'
            suggestion.feedback = f"Resolved by HOD {request.user.get_full_name() or request.user.username} on {timezone.now()}"
            suggestion.save()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

@login_required
@user_passes_test(is_hod)
def hod_feedback_suggestion(request, sug_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            feedback_text = data.get('feedback')
            suggestion = Suggestion.objects.get(pk=sug_id)
            suggestion.feedback = feedback_text
            suggestion.save()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

@login_required
@user_passes_test(is_hod)
def hod_suggestions(request, faculty_name):
    suggestions = Suggestion.objects.filter(current_handler=request.user).order_by('-created_at')
    vc_user = User.objects.filter(role='vc').first()
    dir_user = User.objects.filter(role='director', faculty=request.user.faculty).first()
    forward_targets = []
    if vc_user:
        forward_targets.append(vc_user)
    if dir_user:
        forward_targets.append(dir_user)
    context = {
        'suggestions': suggestions,
        'forward_targets': forward_targets,
        'faculty': request.user.faculty,
        'faculty_name': faculty_name,
        'user': request.user,
    }
    return render(request, 'hod/hod_suggestion.html', context)

@login_required
@user_passes_test(is_hod)
def hod_edit_suggestion(request, faculty_name, sug_id):
    suggestion = get_object_or_404(Suggestion, pk=sug_id, current_handler=request.user)
    faculties = Faculty.objects.all()
    context = {
        'suggestion': suggestion,
        'faculties': faculties,
        'faculty': request.user.faculty,
        'faculty_name': faculty_name,
    }
    return render(request, 'hod/hod_edit_suggestion.html', context)

@login_required
@user_passes_test(is_hod)
def hod_update_suggestion(request, faculty_name, sug_id):
    if request.method == 'POST':
        suggestion = get_object_or_404(Suggestion, pk=sug_id, current_handler=request.user)
        suggestion.category = request.POST.get('category')
        suggestion.description = request.POST.get('description')
        suggestion.visibility = request.POST.get('visibility')
        suggestion.feedback = request.POST.get('feedback')
        suggestion.status = request.POST.get('status')
        faculty_id = request.POST.get('faculty')
        if faculty_id:
            suggestion.faculty = Faculty.objects.get(pk=faculty_id)
        else:
            suggestion.faculty = None
        suggestion.save()
        messages.success(request, 'Suggestion updated successfully.')
        return redirect('hod_suggestions', faculty_name=faculty_name)
    return redirect('hod_suggestions', faculty_name=faculty_name)

@login_required
@user_passes_test(is_hod)
def hod_delete_suggestion(request, sug_id):
    if request.method == 'POST':
        try:
            suggestion = Suggestion.objects.get(pk=sug_id, current_handler=request.user)
            suggestion.delete()
            return JsonResponse({'ok': True})
        except Suggestion.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Suggestion not found'})
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

def hod_generic(request):
    return render(request, 'hod/hod_generic.html')

# ========== Accommodation director views ==========
def is_accommodation_director(user):
    return user.is_authenticated and user.role == 'accommodation_director'

@login_required
@user_passes_test(is_accommodation_director)
def accommodation_dashboard(request):
    """Dashboard for accommodation director – shows stats only (uses dedicated template)."""
    suggestions = Suggestion.objects.filter(
        current_handler=request.user,
        category='accommodation'
    ).order_by('-created_at')
    total_assigned = suggestions.count()
    pending_count = suggestions.filter(status='pending').count()
    forwarded_count = suggestions.filter(status='forwarded').count()
    resolved_count = suggestions.filter(status='resolved').count()
    context = {
        'total_assigned': total_assigned,
        'pending_count': pending_count,
        'forwarded_count': forwarded_count,
        'resolved_count': resolved_count,
    }
    return render(request, 'accomodation/accommodation_dashboard.html', context)

@login_required
@user_passes_test(is_accommodation_director)
def accommodation_suggestions(request):
    """List accommodation suggestions assigned to this director."""
    suggestions = Suggestion.objects.filter(
        current_handler=request.user,
        category='accommodation'
    ).order_by('-created_at')
    # Forward targets: only VC
    vc_user = User.objects.filter(role='vc').first()
    forward_targets = [vc_user] if vc_user else []
    context = {
        'suggestions': suggestions,
        'forward_targets': forward_targets,
    }
    return render(request, 'accomodation/accommodation_suggestion.html', context)

@login_required
@user_passes_test(is_accommodation_director)
def accommodation_forward_suggestion(request, sug_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            target_id = data.get('target_user_id')
            suggestion = Suggestion.objects.get(
                pk=sug_id,
                category='accommodation',
                current_handler=request.user
            )
            target_user = User.objects.get(pk=target_id)
            suggestion.status = 'forwarded'
            suggestion.current_handler = target_user
            suggestion.feedback = f"Forwarded to {target_user.get_full_name() or target_user.username} on {timezone.now()}"
            suggestion.save()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

@login_required
@user_passes_test(is_accommodation_director)
def accommodation_resolve_suggestion(request, sug_id):
    if request.method == 'POST':
        try:
            suggestion = Suggestion.objects.get(
                pk=sug_id,
                category='accommodation',
                current_handler=request.user
            )
            suggestion.status = 'resolved'
            suggestion.feedback = f"Resolved by Accommodation Director on {timezone.now()}"
            suggestion.save()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

@login_required
@user_passes_test(is_accommodation_director)
def accommodation_feedback_suggestion(request, sug_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            feedback_text = data.get('feedback')
            suggestion = Suggestion.objects.get(
                pk=sug_id,
                category='accommodation',
                current_handler=request.user
            )
            suggestion.feedback = feedback_text
            suggestion.save()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

# ========== VC Edit, Update, Delete views (added) ==========
@login_required
@user_passes_test(is_vc)
def vice_edit_suggestion(request, sug_id):
    """Edit suggestion form for VC."""
    suggestion = get_object_or_404(Suggestion, pk=sug_id)
    faculties = Faculty.objects.all()
    context = {
        'suggestion': suggestion,
        'faculties': faculties,
    }
    return render(request, 'vice/vice_edit_suggestion.html', context)

@login_required
@user_passes_test(is_vc)
def vice_update_suggestion(request, sug_id):
    """Update suggestion – VC can edit any suggestion they have access to."""
    if request.method == 'POST':
        suggestion = get_object_or_404(Suggestion, pk=sug_id)
        suggestion.category = request.POST.get('category')
        suggestion.description = request.POST.get('description')
        suggestion.visibility = request.POST.get('visibility')
        suggestion.feedback = request.POST.get('feedback')
        suggestion.status = request.POST.get('status')
        faculty_id = request.POST.get('faculty')
        if faculty_id:
            suggestion.faculty = Faculty.objects.get(pk=faculty_id)
        else:
            suggestion.faculty = None
        suggestion.save()
        messages.success(request, 'Suggestion updated successfully.')
        return redirect('vice_suggestions')
    return redirect('vice_suggestions')

@login_required
@user_passes_test(is_vc)
def vice_delete_suggestion(request, sug_id):
    """Delete suggestion – VC can delete any suggestion they have access to."""
    if request.method == 'POST':
        try:
            suggestion = Suggestion.objects.get(pk=sug_id)
            suggestion.delete()
            return JsonResponse({'ok': True})
        except Suggestion.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Suggestion not found'})
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

# ========== Health check endpoint (for uptime monitoring) ==========
def health_check(request):
    """Simple health check endpoint for uptime monitoring."""
    return HttpResponse("OK", content_type="text/plain")