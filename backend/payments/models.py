"""
Payments Models
Handles token packs, user balances, transactions and payments
"""

from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class TokenPack(models.Model):
    """
    Token packs that users can purchase.
    Admin configures name, credits, and price.
    """
    name = models.CharField(max_length=100, help_text="e.g. Starter, Standard, Pro")
    description = models.TextField(blank=True, help_text="What users get with this pack")
    credits = models.PositiveIntegerField(help_text="Number of credits in this pack")
    price_kes = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in KES")
    is_active = models.BooleanField(default=True, help_text="Show this pack to users")
    is_featured = models.BooleanField(default=False, help_text="Highlight as most popular")
    sort_order = models.PositiveIntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'price_kes']
        verbose_name = "Token Pack"
        verbose_name_plural = "Token Packs"

    def __str__(self):
        return f"{self.name} — {self.credits} credits @ KES {self.price_kes}"


class AIFeatureCost(models.Model):
    """
    How many credits each AI feature costs.
    Admin can adjust costs anytime.
    """
    FEATURE_CHOICES = [
        ('cv_write', 'Write CV from scratch'),
        ('cv_revamp', 'Revamp existing CV'),
        ('cv_customize', 'Customize CV for job'),
        ('cover_letter', 'Write cover letter'),
        ('career_guidance', 'Career guidance (per message)'),
        ('job_match', 'Job matching'),
        ('interview_question', 'Interview question (future)'),
    ]

    feature = models.CharField(max_length=50, choices=FEATURE_CHOICES, unique=True)
    credits_cost = models.PositiveIntegerField(help_text="Credits deducted per use")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI Feature Cost"
        verbose_name_plural = "AI Feature Costs"

    def __str__(self):
        return f"{self.get_feature_display()} — {self.credits_cost} credits"


class UserTokenBalance(models.Model):
    """Each user's current token balance."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='token_balance')
    balance = models.PositiveIntegerField(default=0)
    total_purchased = models.PositiveIntegerField(default=0)
    total_used = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Token Balance"
        verbose_name_plural = "User Token Balances"

    def __str__(self):
        return f"{self.user.email} — {self.balance} credits"

    def has_enough(self, amount: int) -> bool:
        return self.balance >= amount

    def deduct(self, amount: int) -> bool:
        if self.has_enough(amount):
            self.balance -= amount
            self.total_used += amount
            self.save()
            return True
        return False

    def add(self, amount: int):
        self.balance += amount
        self.total_purchased += amount
        self.save()


class TokenTransaction(models.Model):
    """Full history of every credit addition and deduction."""
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('usage', 'AI Feature Usage'),
        ('bonus', 'Bonus / Admin Gift'),
        ('refund', 'Refund'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='token_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    credits = models.IntegerField(help_text="Positive = added, Negative = deducted")
    balance_after = models.PositiveIntegerField()
    description = models.CharField(max_length=255)
    feature = models.CharField(max_length=50, blank=True)
    payment = models.ForeignKey(
        'Payment', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transactions'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Token Transaction"
        verbose_name_plural = "Token Transactions"

    def __str__(self):
        sign = '+' if self.credits > 0 else ''
        return f"{self.user.email} {sign}{self.credits} — {self.description}"


class Payment(models.Model):
    """Payment records for token pack purchases."""
    PAYMENT_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('card', 'Visa/Mastercard (Flutterwave)'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    token_pack = models.ForeignKey(TokenPack, on_delete=models.SET_NULL, null=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    amount_kes = models.DecimalField(max_digits=10, decimal_places=2)
    credits_to_add = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # M-Pesa fields
    mpesa_phone = models.CharField(max_length=20, blank=True)
    mpesa_checkout_request_id = models.CharField(max_length=100, blank=True, db_index=True)
    mpesa_merchant_request_id = models.CharField(max_length=100, blank=True)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True)

    # Flutterwave fields
    flutterwave_tx_ref = models.CharField(max_length=100, blank=True, db_index=True)
    flutterwave_tx_id = models.CharField(max_length=100, blank=True)

    gateway_response = models.JSONField(default=dict, blank=True)
    credits_added = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"{self.user.email} — KES {self.amount_kes} via {self.payment_method} ({self.status})"
