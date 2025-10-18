from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from cloudinary.models import CloudinaryField


User = get_user_model()

class Client(models.Model):
    """Extended profile for authenticated customers."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="client_profile")
    phone = models.CharField(max_length=32, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    join_date = models.DateTimeField(default=timezone.now)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.user.get_username()

    @property
    def full_name(self):
        fn = f"{self.user.first_name} {self.user.last_name}".strip()
        return fn or self.user.get_username()


class ContactMessage(models.Model):
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField(max_length=120, blank=True)
    last_name  = models.CharField(max_length=120, blank=True)
    email      = models.EmailField()
    subject    = models.CharField(max_length=255, blank=True)
    message    = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    handled    = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} - {self.subject or 'Contact'}"


class WithdrawalRequest(models.Model):
    METHOD_CHOICES = [
        ("bank", "Bank Transfer"),
        ("airtel", "Airtel Money"),
        ("mpamba", "TNM Mpamba"),
        ("paypal", "PayPal"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processed", "Processed"),
        ("failed", "Failed"),
    ]

    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    account_info = models.CharField(max_length=255, help_text="Account number / phone / email")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Withdrawal {self.pk} - {self.client or 'Anonymous'}"


class ExternalLink(models.Model):
    title = models.CharField(max_length=255)
    url = models.URLField()
    category = models.CharField(max_length=120, blank=True)
    reason = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.title


class Product(models.Model):

    CATEGORY_CHOICES = [
        ('code', 'Source Code'),
        ('apps', 'Mobile Apps'),
        ('websites', 'Websites'),
        ('templates', 'Templates'),
    ]

    GRADIENT_CHOICES = [
        ('linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 'Purple Blue'),
        ('linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', 'Pink Red'),
        ('linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', 'Blue Cyan'),
        ('linear-gradient(135deg, #fa709a 0%, #fee140 100%)', 'Pink Yellow'),
        ('linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)', 'Mint Pink'),
        ('linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)', 'Orange Peach'),
        ('linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 'Indigo Purple'),
    ]

    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField()
    key_features = models.TextField(help_text="Enter each feature on a new line starting with •")
    technologies_used = models.CharField(max_length=255, help_text="Separate technologies with commas")
    demo_url = models.URLField(blank=True, null=True)
    preview_gradient = models.CharField(max_length=255, choices=GRADIENT_CHOICES)
    
    image = CloudinaryField('image', blank=True, null=True)
    file_url = models.URLField(help_text="URL to download product/file")
    
    # New tracking fields
    views = models.PositiveIntegerField(default=0)
    sold_count = models.PositiveIntegerField(default=0)
    booked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def mark_sold(self, quantity=1):
        """Call this when the product is sold"""
        self.sold_count += quantity
        if self.sold_count > 0:
            self.booked = True
        self.save()

    def __str__(self):
        return self.title


class Order(models.Model):
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    paid = models.BooleanField(default=False)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Order #{self.pk} - {self.client or 'Guest'}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    qty = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    def subtotal(self):
        return self.qty * self.price

    def __str__(self):
        return f"{self.product} x {self.qty}"


class PaymentAttempt(models.Model):
    PAYMENT_TYPES = [("visa", "Card/Visa"), ("airtel", "Airtel"), ("mpamba", "TNM Mpamba")]
    STATUS = [("pending", "Pending"), ("success", "Success"), ("failed", "Failed")]

    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    tx_ref = models.CharField(max_length=255, unique=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    email = models.EmailField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    raw_response = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.tx_ref} - {self.payment_type} - {self.status}"

class Gallery(models.Model):
    MEDIA_TYPE_CHOICES = (
        ('image', 'Image'),
        ('video', 'Video'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    media = CloudinaryField('image', blank=True, null=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='image')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

