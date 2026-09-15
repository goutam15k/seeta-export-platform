from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.exceptions import ValidationError # <-- 1. Import ValidationError

class CustomUser(AbstractUser):
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    company_name = models.CharField(max_length=150, blank=True, null=True)
    
    CURRENCY_CHOICES = [
        ('USD', 'USD ($)'),
        ('EUR', 'EUR (€)'),
        ('INR', 'INR (₹)'),
        ('GBP', 'GBP (£)'),
        ('CAD', 'CAD ($)'),
        ('AUD', 'AUD ($)'),
    ]
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    
    address = models.TextField(blank=True, null=True)
    zipcode = models.CharField(max_length=20, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    is_verified = models.BooleanField(
        default=False, 
        help_text="Designates whether this user has been approved/verified by an admin."
    )

    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )
    def save(self, *args, **kwargs):
        # If the user already exists in the database
        if self.pk:
            try:
                original = CustomUser.objects.get(pk=self.pk)
                # If this is our protected primary superadmin, force privileges to remain active
                if original.username == 'admin': # Match your superadmin's username
                    self.is_superuser = True
                    self.is_staff = True
            except CustomUser.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_superuser and self.username == 'admin':
            raise ValueError("Security Error: This primary superadmin account cannot be deleted.")
        super().delete(*args, **kwargs)
        
    # --- 2. Add the conditional validation ---
    def clean(self):
        super().clean()
        
        # If the user is NOT a superuser, enforce the required fields
        if not self.is_superuser:
            if not self.email:
                raise ValidationError({'email': 'Email is required for customer accounts.'})
            if not self.mobile_number:
                raise ValidationError({'mobile_number': 'Mobile number is required for customer accounts.'})

    def __str__(self):
        return f"{self.username} - {self.company_name or self.email}"



# myapp/models.py (Add this to the bottom of the file)

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"

class SubCategory(models.Model):
    # This links the subcategory to a main category
    main_category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.main_category.name} -> {self.name}"
    
    class Meta:
        verbose_name_plural = "Sub Categories"

class Product(models.Model):
    name = models.CharField(max_length=200)
    unique_code = models.CharField(max_length=50, unique=True)
    
    main_category = models.ForeignKey(Category, on_delete=models.CASCADE)
    sub_category = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True)
    
    dimensions = models.CharField(max_length=100, help_text="e.g., 120x60x45 cm")
    cpm = models.DecimalField(max_digits=10, decimal_places=2, help_text="Cost/Cubic Per Meter")
    description = models.TextField()
    
    # --- ADD THIS NEW FIELD ---
    is_active = models.BooleanField(
        default=True, 
        help_text="Uncheck this box to hide the product from the website without deleting it."
    )
    
    # Images
    image_1 = models.ImageField(upload_to='products/')
    image_2 = models.ImageField(upload_to='products/', null=True, blank=True)
    image_3 = models.ImageField(upload_to='products/', null=True, blank=True)
    image_4 = models.ImageField(upload_to='products/', null=True, blank=True)
    image_5 = models.ImageField(upload_to='products/', null=True, blank=True)
    
    def __str__(self):
        return f"{self.unique_code} - {self.name}"
    name = models.CharField(max_length=200)
    unique_code = models.CharField(max_length=50, unique=True)
    
    # Category Links
    main_category = models.ForeignKey(Category, on_delete=models.CASCADE)
    sub_category = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Product Details
    dimensions = models.CharField(max_length=100, help_text="e.g., 120x60x45 cm")
    cpm = models.DecimalField(max_digits=10, decimal_places=2, help_text="Cost/Cubic Per Meter")
    description = models.TextField()
    
    # Images (1st is mandatory, 2-5 are optional)
    image_1 = models.ImageField(upload_to='products/')
    image_2 = models.ImageField(upload_to='products/', null=True, blank=True)
    image_3 = models.ImageField(upload_to='products/', null=True, blank=True)
    image_4 = models.ImageField(upload_to='products/', null=True, blank=True)
    image_5 = models.ImageField(upload_to='products/', null=True, blank=True)
    
    def __str__(self):
        return f"{self.unique_code} - {self.name}"



# Add these at the bottom of myapp/models.py

class Cart(models.Model):
    # One user has exactly one active cart
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart - {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} ({self.cart.user.username})"
    
    @property
    def subtotal(self):
        # Automatically calculates the price based on quantity
        return self.quantity * self.product.cpm



# Add these models at the bottom of myapp/models.py

class Inquiry(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending Review'),
        ('Quoted', 'Quote Sent'),
        ('Closed', 'Closed'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='inquiries')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    admin_notes = models.TextField(blank=True, null=True, help_text="Internal notes for the sales team.")

    def __str__(self):
        return f"Inquiry #{self.id} - {self.user.username} ({self.status})"
    
    class Meta:
        verbose_name_plural = "Inquiries"

class InquiryItem(models.Model):
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name_snapshot = models.CharField(max_length=200, help_text="Saved in case product is modified later.")
    product_code_snapshot = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity}x {self.product_name_snapshot} (Inquiry #{self.inquiry.id})"


# Make sure these are placed in myapp/models.py

class Inquiry(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending Review'),
        ('Quoted', 'Quote Sent'),
        ('Closed', 'Closed'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='inquiries')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    admin_notes = models.TextField(blank=True, null=True, help_text="Internal notes for the sales team.")

    def __str__(self):
        return f"Inquiry #{self.id} - {self.user.username} ({self.status})"
    
    @property
    def total_quoted_price(self):
        total = sum(item.quoted_price * item.quantity for item in self.items.all() if item.quoted_price)
        return total

    class Meta:
        verbose_name_plural = "Inquiries"


class InquiryItem(models.Model):
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name_snapshot = models.CharField(max_length=200, help_text="Saved in case product is modified later.")
    product_code_snapshot = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField(default=1)
    quoted_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True, 
        help_text="Custom price set by admin for this inquiry item."
    )

    def __str__(self):
        return f"{self.quantity}x {self.product_name_snapshot} (Inquiry #{self.inquiry.id})"