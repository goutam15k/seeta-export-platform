from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import send_mail
from .models import CustomUser, Category, SubCategory, Product, Cart, CartItem, Inquiry, InquiryItem

# --- CATEGORY & SUBCATEGORY ---
admin.site.register(Category)
admin.site.register(SubCategory)


# --- PRODUCT ADMIN & ACTIONS ---
@admin.action(description="Hide selected products")
def hide_products(modeladmin, request, queryset):
    queryset.update(is_active=False)

@admin.action(description="Show selected products")
def show_products(modeladmin, request, queryset):
    queryset.update(is_active=True)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'name', 'unique_code', 'main_category', 'sub_category', 'cpm', 'is_active')
    
    # --- ADD THIS LINE ---
    # This allows you to edit prices and active status directly from the table view!
    list_editable = ('cpm', 'is_active')
    
    list_filter = ('is_active', 'main_category', 'sub_category')
    search_fields = ('name', 'unique_code')
    actions = [hide_products, show_products]

    def image_preview(self, obj):
        if obj.image_1:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />', obj.image_1.url)
        return "No Image"
    image_preview.short_description = 'Main Image'

# --- SHOPPING CART ADMIN ---
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__username', 'user__email')
    inlines = [CartItemInline]


# --- INQUIRY & QUOTE MANAGEMENT ADMIN ---
class InquiryItemInline(admin.TabularInline):
    model = InquiryItem
    extra = 0
    readonly_fields = ('product', 'product_name_snapshot', 'product_code_snapshot', 'quantity')
    fields = ('product_name_snapshot', 'product_code_snapshot', 'quantity', 'quoted_price')

@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'get_company', 'get_email', 'status', 'created_at')
    list_editable = ('status',)
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__company_name', 'id')
    readonly_fields = ('user', 'created_at')
    inlines = [InquiryItemInline]
    
    def get_company(self, obj):
        return obj.user.company_name or "N/A"
    get_company.short_description = 'Company'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    fieldsets = (
        ('Client Information', {
            'fields': ('user', 'created_at')
        }),
        ('Quote Status', {
            'fields': ('status', 'admin_notes')
        }),
    )

    # Custom URL endpoint for the "Send Quotation" button action
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/send-quote/',
                self.admin_site.admin_view(self.send_quotation_view),
                name='myapp_inquiry_send_quote',
            ),
        ]
        return custom_urls + urls

    # View logic for sending the quote email and updating status
    def send_quotation_view(self, request, object_id):
        inquiry = get_object_or_404(Inquiry, pk=object_id)
        
        # 1. Build the formal quotation message with itemized custom prices
        subject = f"Official Quotation for Inquiry #{inquiry.id}"
        message = f"Hello {inquiry.user.first_name or inquiry.user.username},\n\n"
        message += f"Here is the official quotation for your inquiry reference #{inquiry.id}:\n\n"
        message += "--- QUOTATION DETAILS ---\n"
        
        total_estimate = 0
        for item in inquiry.items.all():
            price_str = f"${item.quoted_price}" if item.quoted_price else "Custom/Pending"
            message += f"• {item.product_name_snapshot} (Code: {item.product_code_snapshot}) | Qty: {item.quantity} | Unit Price: {price_str}\n"
            if item.quoted_price:
                total_estimate += item.quoted_price * item.quantity
                
        if total_estimate > 0:
            message += f"\nEstimated Total: ${total_estimate}\n"
            
        message += "\n-----------------------\n"
        message += "Thank you for choosing Seeta Are & Export. Please reply to this email to confirm your order.\n"

        # 2. Dispatch via Gmail and update the database status automatically
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [inquiry.user.email, settings.DEFAULT_FROM_EMAIL],
                fail_silently=False,
            )
            
            inquiry.status = 'Quoted'
            inquiry.save()
            
            messages.success(request, f"Quotation for Inquiry #{inquiry.id} sent successfully, and status updated to 'Quoted'.")
            
        except Exception as e:
            messages.error(request, f"Failed to send email: {e}")
            
        return redirect('admin:myapp_inquiry_change', object_id)


# --- USER ADMIN CONFIGURATION ---
from django.conf import settings
from django.core.mail import send_mail

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'company_name', 'mobile_number', 'is_verified', 'is_staff')
    list_editable = ('is_verified',)  # Allows direct approval toggle from the list view!
    list_filter = ('is_verified', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'company_name', 'mobile_number')
    readonly_fields = ('date_joined', 'last_login')

    # --- MAKE PRIVILEGES READ-ONLY FOR THE PRIMARY ADMIN IN UI ---
    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        # If editing the protected primary superadmin, lock down their access toggles
        if obj and obj.username == 'admin': # Match your superadmin's username
            readonly.extend(['is_superuser', 'is_staff'])
        return readonly

    # --- BLOCK DELETION IN ADMIN ---
    def has_delete_permission(self, request, obj=None):
        if obj and obj.username == 'admin':
            return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        # Check if this is an existing user being updated
        if change:
            try:
                # Fetch the previous state from the database
                old_obj = CustomUser.objects.get(pk=obj.pk)
                
                # Check if 'is_verified' just flipped from False to True
                if not old_obj.is_verified and obj.is_verified:
                    subject = "Your B2B Account Has Been Approved - Seeta Are & Export"
                    message = f"Hello {obj.first_name or obj.username},\n\n"
                    message += "Great news! Your B2B account has been verified and approved by our administration team.\n"
                    message += "You can now log in to view custom product pricing, submit quote inquiries, and manage your orders.\n\n"
                    message += "Log in here: http://127.0.0.1:8000/login/\n\n"
                    message += "Thank you for choosing Seeta Are & Export.\n"
                    
                    try:
                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            [obj.email],
                            fail_silently=False,
                        )
                        messages.success(request, f"Account approval email successfully sent to {obj.email}.")
                    except Exception as e:
                        messages.error(request, f"Failed to send approval email: {e}")
                        
            except CustomUser.DoesNotExist:
                pass
                
        super().save_model(request, obj, form, change)


# Add this at the very bottom of your myapp/admin.py file

from .models import Product, Inquiry, CustomUser

# Save Django's original admin site index method
original_admin_index = admin.site.index

def custom_admin_index(request, extra_context=None):
    extra_context = extra_context or {}
    
    # Calculate key metrics
    extra_context['total_active_products'] = Product.objects.filter(is_active=True).count()
    extra_context['pending_inquiries'] = Inquiry.objects.filter(status='Pending').count()
    extra_context['unverified_users'] = CustomUser.objects.filter(is_verified=False).count()
    
    return original_admin_index(request, extra_context=extra_context)

# Override the default index with our custom data wrapper
admin.site.index = custom_admin_index