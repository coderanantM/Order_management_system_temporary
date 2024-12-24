from django.db import models
from django.contrib.auth.models import User
from datetime import date, datetime

from jsonschema import ValidationError

class Seller(models.Model):
    """
    Represents a seller in the order management system.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=15)
    contact_info = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.user.username

class Buyer(models.Model):
    """
    Represents a buyer (automobile company) in the order management system.
    """
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255)
    email = models.EmailField()

    def __str__(self):
        return self.name

class Part(models.Model):
    part_code = models.CharField(max_length=255, unique=True, null=False, primary_key=True)
    part_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    schedule = models.IntegerField(null=True, blank=True)
    open_order = models.IntegerField(null=False, help_text="Open order quantity defined at the start of the month")
    quantity_dispatched = models.IntegerField(default=0, null=True, blank=True)
    remaining_quantity = models.IntegerField(default=0)
    buyer = models.ForeignKey('Buyer', on_delete=models.CASCADE)
    additional_order = models.IntegerField(null=True, blank=True)
    order_date = models.DateField(null=True, blank=True, help_text="User-defined order date")
    production_date = models.DateField(null=True, blank=True, help_text="User-defined production date")

    def update_remaining(self, additional_order, quantity_dispatched):
        self.remaining_quantity = self.open_order + (additional_order or 0) - quantity_dispatched
        self.quantity_dispatched = quantity_dispatched
        self.additional_order = additional_order
        self.save()

    def __str__(self):
        return f"{self.part_name} ({self.part_code})"

