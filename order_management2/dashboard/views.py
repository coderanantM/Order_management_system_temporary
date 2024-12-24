import logging
import math
import csv
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from fuzzywuzzy import process
from datetime import datetime
from datetime import date
logger = logging.getLogger(__name__)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, F, Value
from .forms import SellerRegistrationForm, PartProductionForm, PartListingForm, LoginForm
from .models import Part, Seller, Buyer, ProductionUpdate
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
    today = datetime.today().date()  # Ensure today is a date object
    first_day_of_month = today.replace(day=1)
    total_days_in_month = 26  # Assuming 26 days in a month for calculation

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
        production_data = ProductionUpdate.objects.filter(part=selected_part).order_by('production_date')

        # Initialize the schedule list for the part
        remaining_quantity = open_order

        # Add the open order as the first entry
        selected_part_schedule.append({
            'date': first_day_of_month,
            'additional_order': open_order,
            'quantity_dispatched': 0,
            'remaining_quantity': remaining_quantity,
            'balance_days': total_days_in_month,
            'balance_rate_per_day': math.ceil(remaining_quantity / total_days_in_month) if total_days_in_month > 0 else 0,
        })

        for daily_data in production_data:
            additional_order = daily_data.additional_order or 0
            quantity_dispatched = daily_data.quantity_dispatched or 0
            remaining_quantity = remaining_quantity + additional_order - quantity_dispatched

            # Calculate balance days and balance rate per day
            days_passed = (daily_data.production_date - first_day_of_month).days + 1
            balance_days = total_days_in_month - days_passed
            balance_rate_per_day = math.ceil(remaining_quantity / balance_days) if balance_days > 0 else 0

            # Append the daily schedule to the list
            selected_part_schedule.append({
                'date': daily_data.production_date,
                'additional_order': additional_order,
                'quantity_dispatched': quantity_dispatched,
                'remaining_quantity': remaining_quantity,
                'balance_days': balance_days,
                'balance_rate_per_day': balance_rate_per_day,
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

            # Extract data from the form
            production_date = form.cleaned_data['date']
            additional_order = form.cleaned_data.get('additional_order', 0)
            quantity_dispatched = form.cleaned_data['quantity_dispatched']

            # Create or update the production update entry
            ProductionUpdate.objects.update_or_create(
                part=part,
                production_date=production_date,
                defaults={
                    'additional_order': additional_order,
                    'quantity_dispatched': quantity_dispatched,
                }
            )

            messages.success(request, 'Production updated successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Error updating production. Please correct the errors.')
    else:
        form = PartProductionForm()

    return render(request, 'dashboard/update_production.html', {'form': form})

def export_schedule_to_csv(request, part_code):
    part = get_object_or_404(Part, part_code=part_code)
    production_data = ProductionUpdate.objects.filter(part=part).order_by('production_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="schedule_{part_code}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Additional Order', 'Quantity Dispatched', 'Remaining Quantity', 'Balance Days', 'Balance Rate per Day'])

    today = datetime.today().date()
    first_day_of_month = today.replace(day=1)
    total_days_in_month = 26  # Assuming 26 days in a month for calculation
    remaining_quantity = part.open_order

    # Add the open order as the first entry
    writer.writerow([first_day_of_month, part.open_order, 0, remaining_quantity, total_days_in_month, math.ceil(remaining_quantity / total_days_in_month) if total_days_in_month > 0 else 0])

    for daily_data in production_data:
        additional_order = daily_data.additional_order or 0
        quantity_dispatched = daily_data.quantity_dispatched or 0
        remaining_quantity = remaining_quantity + additional_order - quantity_dispatched

        # Calculate balance days and balance rate per day
        days_passed = (daily_data.production_date - first_day_of_month).days + 1
        balance_days = total_days_in_month - days_passed
        balance_rate_per_day = math.ceil(remaining_quantity / balance_days) if balance_days > 0 else 0

        writer.writerow([daily_data.production_date, additional_order, quantity_dispatched, remaining_quantity, balance_days, balance_rate_per_day])

    return response

def export_schedule_for_date_to_csv(request, part_code, date):
    part = get_object_or_404(Part, part_code=part_code)
    production_data = ProductionUpdate.objects.filter(part=part, production_date=parse_date(date))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="schedule_{part_code}_{date}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Additional Order', 'Quantity Dispatched', 'Remaining Quantity'])

    for daily_data in production_data:
        writer.writerow([
            daily_data.production_date,
            daily_data.additional_order,
            daily_data.quantity_dispatched,
            daily_data.remaining_quantity
        ])

    return response