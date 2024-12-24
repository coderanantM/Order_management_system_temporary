from fuzzywuzzy import process
from datetime import datetime
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, F, Value
from .forms import SellerRegistrationForm, PartProductionForm, PartListingForm, LoginForm
from .models import Part, Seller, Buyer
from django.contrib.auth import authenticate, login

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'You have successfully logged in!')
                next_url = request.GET.get('next', 'list_new_part')  # Default to 'dashboard' if no next URL
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password')
    else:
        form = LoginForm()
    return render(request, 'dashboard/login.html', {'form': form})

def register_seller(request):
    if request.method == 'POST':
        form = SellerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()  # Save the User instance
            # Check if a Seller already exists for this user
            if not Seller.objects.filter(user=user).exists():
                Seller.objects.create(
                    user=user,
                    name=form.cleaned_data.get('name'),
                    contact_number=form.cleaned_data.get('contact_number')
                )  # Create the Seller instance
                login(request, user)  # Log in the user
                messages.success(request, 'You have successfully registered!')
                return redirect('dashboard')  # Redirect to dashboard
            else:
                messages.error(request, 'A seller is already registered for this user.')
                return redirect('register_seller')  # Redirect back to the registration page
        else:
            # If the form is invalid, re-render the page with error messages
            messages.error(request, 'Please correct the errors below.')
            return render(request, 'dashboard/register.html', {'form': form})
    else:
        # Handle GET request by displaying the registration form
        form = SellerRegistrationForm()
        return render(request, 'dashboard/register.html', {'form': form})

def seller_dashboard(request):
    today = datetime.today()
    first_day_of_month = today.replace(day=1)

    # Fetch all parts
    parts = Part.objects.all()

    selected_part_code = request.GET.get('part_code')
    selected_part_schedule = []
    open_order = None

    if selected_part_code:
        selected_part = get_object_or_404(Part, part_code=selected_part_code)

        # Fetch the open order from the selected part
        open_order = selected_part.open_order

        # Fetch the production data for the selected part
        production_data = Part.objects.filter(part_code=selected_part_code, production_date__month=today.month).order_by('production_date')

        # Initialize the schedule list for the part
        remaining_quantity = open_order

        # Add the open order as the first entry
        selected_part_schedule.append({
            'date': first_day_of_month,
            'additional_order': open_order,
            'quantity_dispatched': 0,
            'remaining_quantity': remaining_quantity,
        })

        for daily_data in production_data:
            additional_order = daily_data.additional_order or 0
            quantity_dispatched = daily_data.quantity_dispatched or 0
            remaining_quantity = remaining_quantity + additional_order - quantity_dispatched

            # Append the daily schedule to the list
            selected_part_schedule.append({
                'date': daily_data.production_date,
                'additional_order': additional_order,
                'quantity_dispatched': quantity_dispatched,
                'remaining_quantity': remaining_quantity,
            })

    return render(request, 'dashboard/dashboard.html', {
        'parts': parts,
        'selected_part_code': selected_part_code,
        'selected_part_schedule': selected_part_schedule,
        'open_order': open_order,
    })

@login_required
def list_new_part(request):
    if request.method == 'POST':
        form = PartListingForm(request.POST)
        if form.is_valid():
            form.save()  # Save the new part to the database
            messages.success(request, 'New part listed successfully!')
            return redirect('dashboard')  # Redirect to the dashboard after successful form submission
        else:
            messages.error(request, 'Error listing new part. Please correct the errors.')
    else:
        form = PartListingForm()

    return render(request, 'dashboard/list_new_part.html', {'form': form})



def get_part_details(request, part_code):
    part = get_object_or_404(Part, part_code=part_code)
    data = {
        'part_name': part.part_name,
        'schedule': part.schedule,
        'remaining_quantity': part.remaining_quantity,
    }
    return JsonResponse(data)

def update_daily_production(request):
    if request.method == 'POST':
        form = PartProductionForm(request.POST)
        if form.is_valid():
            part_code = form.cleaned_data['part_code']
            part = get_object_or_404(Part, part_code=part_code)

            # Create a new record for the production update
            new_part = Part(
                part_code=part.part_code,
                part_name=part.part_name,
                price=part.price,
                schedule=part.schedule,
                open_order=part.open_order,
                buyer=part.buyer,
                additional_order=form.cleaned_data['additional_order'],
                quantity_dispatched=form.cleaned_data['quantity_dispatched'],
                order_date=form.cleaned_data['order_date'],  # Use user-defined date for order_date
                production_date=form.cleaned_data['production_date']  # Use user-defined date for production_date
            )
            new_part.update_remaining(new_part.additional_order, new_part.quantity_dispatched)
            new_part.save()  # Ensure the new part is saved

            messages.success(request, 'Production updated successfully!')
            return redirect('dashboard')  # Redirect to the dashboard after updating
        else:
            messages.error(request, 'Error updating production. Please correct the errors.')
    else:
        part_code = request.GET.get('part_code')
        part = get_object_or_404(Part, part_code=part_code) if part_code else None
        initial_data = {
            'part_name': part.part_name if part else '',
            'open_order': part.remaining_quantity if part else 0,
        }
        form = PartProductionForm(initial=initial_data)

    return render(request, 'dashboard/update_production.html', {'form': form})

