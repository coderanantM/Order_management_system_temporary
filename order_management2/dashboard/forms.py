from django import forms
from .models import Seller, Part, Buyer, ProductionUpdate
from django.contrib.auth.models import User

class LoginForm(forms.Form):
    username = forms.CharField(max_length=255, label="Username")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise forms.ValidationError('Username cannot be empty.')
        return username

class SellerRegistrationForm(forms.ModelForm):
    name = forms.CharField(max_length=255, required=True, label="Full Name")
    contact_number = forms.CharField(max_length=15, required=True, label="Contact Number")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])  # Hash the password
        if commit:
            user.save()
        return user

class PartProductionForm(forms.Form):
    part_code = forms.ChoiceField(choices=[], required=True, label="Select Part Code")
    part_name = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    open_order = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'readonly': 'readonly'}), label="Open Order (Previous Balance)")
    date = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))
    additional_order = forms.IntegerField(required=False, label="Additional Order (Optional)", widget=forms.NumberInput(attrs={'placeholder': 'Enter additional order'}))
    quantity_dispatched = forms.IntegerField(required=True, label="Quantity Dispatched", widget=forms.NumberInput(attrs={'placeholder': 'Enter quantity dispatched'}))
    remaining_quantity = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'readonly': 'readonly'}), label="Remaining Quantity (Balance)")

    def __init__(self, *args, **kwargs):
        # Part object should be passed in kwargs to prepopulate open order
        part = kwargs.pop('part', None)
        super().__init__(*args, **kwargs)

        # Dynamically populate part_code choices
        self.fields['part_code'].choices = [(part.part_code, f"{part.part_code} - {part.part_name}") for part in Part.objects.all()]


        # Prepopulate open_order if part is provided
        if part:
            self.fields['open_order'].initial = part.open_order
            self.fields['part_name'].initial = part.part_name

    def update_remaining(self, part):
        """
        Update remaining quantity dynamically based on user input and previous balance.
        """
        if not part:
            raise ValueError("Part instance is required to calculate remaining quantity.")

        additional_order = self.cleaned_data.get('additional_order', 0) or 0
        quantity_dispatched = self.cleaned_data.get('quantity_dispatched', 0) or 0

        # Fetch the most recent production update for the part
        previous_update = ProductionUpdate.objects.filter(part=part).order_by('-production_date').first()
        previous_balance = previous_update.remaining_quantity if previous_update else part.open_order

        # Calculate remaining quantity
        remaining_quantity = previous_balance + additional_order - quantity_dispatched
        self.cleaned_data['remaining_quantity'] = remaining_quantity

        # Save to ProductionUpdate instead of Part
        ProductionUpdate.objects.create(
            part=part,
            production_date=self.cleaned_data['date'],
            additional_order=additional_order,
            quantity_dispatched=quantity_dispatched,
            remaining_quantity=remaining_quantity
        )

        return remaining_quantity

class PartListingForm(forms.ModelForm):
    buyer_name = forms.CharField(max_length=255, required=True, label="Buyer's Company Name")
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True, label="Date")
    open_order = forms.IntegerField(required=True, label="Open Order")
    
    class Meta:
        model = Part
        fields = ['part_code', 'part_name', 'open_order', 'price', 'date']

    def clean_part_code(self):
        part_code = self.cleaned_data.get('part_code')
        if not part_code:
            raise forms.ValidationError('Part code cannot be empty.')
        return part_code

    def clean_schedule(self):
        schedule = self.cleaned_data.get('schedule')
        if schedule <= 0:
            raise forms.ValidationError('Schedule must be greater than 0.')
        return schedule

    def save(self, commit=True):
        # Get the buyer_name from the cleaned data
        buyer_name = self.cleaned_data.get('buyer_name')

        # Create or get the Buyer instance based on the buyer_name
        buyer, created = Buyer.objects.get_or_create(name=buyer_name)

        # Create the Part instance and assign the buyer to it
        part = super().save(commit=False)
        part.buyer = buyer  # Assign the buyer to the part

        if commit:
            part.save()  # Save the part instance

        return part
