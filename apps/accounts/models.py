# apps/accounts/models.py
from django.db import models

class FinancialAccount(models.Model):
    """
    Represents a specific ledger account (e.g. 'Tuition Income', 'Bank A', 'Petty Cash').
    Satisfies the 'Control' aspect of 'Finance / Accounts'.
    """
    TYPE_CHOICES = (
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('income', 'Income'),
        ('expense', 'Expense'),
    )
    
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class AccountSetting(models.Model):
    """
    Fine-grained Access Control & Configuration.
    Stores toggles, school-specific configs, and feature flags.
    """
    key = models.CharField(max_length=50, unique=True, help_text="Config Key (e.g. 'ALLOW_GUEST_PORTAL')")
    value = models.CharField(max_length=255, help_text="Value (True/False, or specific string)")
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.key}: {self.value}"

