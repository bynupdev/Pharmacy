from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import Patient, Allergy
from prescriptions.models import Prescription
from .forms import PatientForm, AllergyForm

@login_required
def patient_list(request):
    """List all patients"""
    patients = Patient.objects.all().order_by('last_name', 'first_name')
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        patients = patients.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(patients, 20)
    page = request.GET.get('page')
    patients_page = paginator.get_page(page)
    
    context = {
        'patients': patients_page,
        'search_query': search_query
    }
    return render(request, 'patients/list.html', context)

@login_required
def patient_detail(request, pk):
    """View patient details"""
    patient = get_object_or_404(Patient, pk=pk)
    prescriptions = patient.prescriptions.all().order_by('-created_at')[:5]
    allergies = patient.allergy_list.all()
    
    context = {
        'patient': patient,
        'prescriptions': prescriptions,
        'allergies': allergies,
        'prescription_count': patient.prescriptions.count()
    }
    return render(request, 'patients/detail.html', context)

@login_required
def patient_add(request):
    """Add new patient"""
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.created_by = request.user
            patient.save()
            messages.success(request, f'Patient {patient.full_name} added successfully.')
            return redirect('patients:detail', pk=patient.pk)
    else:
        form = PatientForm()
    
    return render(request, 'patients/add_edit.html', {'form': form, 'edit_mode': False})

@login_required
def patient_edit(request, pk):
    """Edit patient details"""
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Patient information updated successfully.')
            return redirect('patients:detail', pk=patient.pk)
    else:
        form = PatientForm(instance=patient)
    
    return render(request, 'patients/add_edit.html', {
        'form': form,
        'patient': patient,
        'edit_mode': True
    })

@login_required
def patient_delete(request, pk):
    """Delete patient"""
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        patient.delete()
        messages.success(request, 'Patient deleted successfully.')
        return redirect('patients:list')
    return render(request, 'patients/confirm_delete.html', {'patient': patient})

@login_required
def patient_prescriptions(request, pk):
    """View patient's prescription history"""
    patient = get_object_or_404(Patient, pk=pk)
    prescriptions = patient.prescriptions.select_related('pharmacist').all().order_by('-created_at')
    
    paginator = Paginator(prescriptions, 10)
    page = request.GET.get('page')
    prescriptions_page = paginator.get_page(page)
    
    context = {
        'patient': patient,
        'prescriptions': prescriptions_page
    }
    return render(request, 'patients/prescriptions.html', context)

@login_required
def add_allergy(request, pk):
    """Add allergy to patient"""
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = AllergyForm(request.POST)
        if form.is_valid():
            allergy = form.save(commit=False)
            allergy.patient = patient
            allergy.save()
            
            # Update patient's allergies text field
            if patient.allergies:
                patient.allergies += f", {allergy.allergen}"
            else:
                patient.allergies = allergy.allergen
            patient.save()
            
            messages.success(request, f'Allergy {allergy.allergen} added successfully.')
            return redirect('patients:detail', pk=patient.pk)
    else:
        form = AllergyForm()
    
    return render(request, 'patients/add_allergy.html', {
        'form': form,
        'patient': patient
    })

@login_required
def patient_search(request):
    """Search patients (JSON response for autocomplete)"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    patients = Patient.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(phone__icontains=query)
    )[:10]
    
    results = [{
        'id': p.id,
        'text': f"{p.full_name} - {p.phone}",
        'name': p.full_name,
        'dob': p.date_of_birth.strftime('%Y-%m-%d'),
        'age': p.age,
        'phone': p.phone
    } for p in patients]
    
    return JsonResponse({'results': results})

@login_required
def api_search_patients(request):
    """API endpoint for patient search"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'patients': []})
    
    patients = Patient.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(phone__icontains=query)
    )[:10]
    
    data = [{
        'id': p.id,
        'name': p.full_name,
        'age': p.age,
        'phone': p.phone,
        'allergies': p.allergies
    } for p in patients]
    
    return JsonResponse({'patients': data})