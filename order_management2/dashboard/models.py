import logging

logger = logging.getLogger(__name__)
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
    part_code = models.CharField(
        max_length=255, unique=True, null=False, primary_key=True
    )
    part_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    schedule = models.IntegerField(null=True, blank=True)
    open_order = models.IntegerField(
        null=False, help_text="Open order quantity defined at the start of the month"
    )
    quantity_dispatched = models.IntegerField(default=0, null=True, blank=True)
    remaining_quantity = models.IntegerField(default=0)
    buyer = models.ForeignKey("Buyer", on_delete=models.CASCADE)
    additional_order = models.IntegerField(null=True, blank=True)
    order_date = models.DateField(
        null=True, blank=True, help_text="User-defined order date"
    )
    production_date = models.DateField(
        null=True, blank=True, help_text="User-defined production date"
    )

    def update_remaining(self, additional_order, quantity_dispatched):
        self.remaining_quantity = (
            self.open_order + (additional_order or 0) - quantity_dispatched
        )
        self.quantity_dispatched = quantity_dispatched
        self.additional_order = additional_order
        self.save()

    def __str__(self):
        return f"{self.part_name} ({self.part_code})"


class ProductionUpdate(models.Model):
    """
    Represents a daily production update for a part.
    """

    part = models.ForeignKey(
        "Part", on_delete=models.CASCADE, related_name="production_updates"
    )
    production_date = models.DateField()  # Date of production update
    additional_order = models.IntegerField(
        default=0,
        null=True,  # Allow database to store NULL for this field
        blank=True,  # Allow forms to leave this field blank
        help_text="Additional order for the day (optional)",
    )
    quantity_dispatched = models.IntegerField(
        default=0, help_text="Quantity dispatched for the day"
    )
    remaining_quantity = models.IntegerField(
        default=0, help_text="Remaining balance after production update"
    )

    def save(self, *args, **kwargs):
    # Fetch the previous day's balance
        previous_update = ProductionUpdate.objects.filter(
            part=self.part, production_date__lt=self.production_date
        ).order_by('-production_date').first()

    # Log previous update
        if previous_update:
            logger.info(f"Previous Update Found: Date = {previous_update.production_date}, "
                f"Remaining Quantity = {previous_update.remaining_quantity}")
        else:
            logger.info("No Previous Update Found. Using part's open order.")

    # Get the previous day's remaining quantity or default to the part's open order
        previous_balance = previous_update.remaining_quantity if previous_update else self.part.open_order

    # Ensure additional_order is treated as 0 if None
        additional_order = self.additional_order or 0

    # Log intermediate values
        logger.info(f"Calculating Remaining Quantity: "
                    f"Previous Balance = {previous_balance}, "
                    f"Additional Order = {additional_order}, "
                    f"Quantity Dispatched = {self.quantity_dispatched}")

    # Calculate the remaining quantity
        self.remaining_quantity = previous_balance + additional_order - self.quantity_dispatched

    # Log final result
        logger.info(f"Remaining Quantity Calculated: {self.remaining_quantity}")

    # Save the update
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.part.part_code} - {self.production_date}"
