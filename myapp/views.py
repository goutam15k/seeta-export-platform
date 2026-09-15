from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.exceptions import ValidationError

from seeta import settings
from .models import CustomUser, Product, Cart, CartItem, Category, Inquiry, InquiryItem
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Q

# --- Existing Views ---
def home(request):
    return render(request, 'index.html')

# Add this to your existing imports at the top

# Add this import at the top of your file
from django.db.models import Q
from .models import CustomUser, Product, Cart, CartItem, Category 

# ... [Your other views] ...

def shop(request):
    # 1. Start with all active products and all categories
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.all()
    
    # 2. Capture the search and category parameters from the URL (e.g., ?q=chair&category=2)
    search_query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    
    # 3. Apply the Search Filter
    if search_query:
        # This searches for the query inside the product name OR the unique code
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(unique_code__icontains=search_query)
        )
        
    # 4. Apply the Category Filter
    if category_id:
        products = products.filter(main_category_id=category_id)
        
    # 5. Send everything to the template
    context = {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'category_id': category_id,
    }
    
    return render(request, 'shop.html', context)

def about(request):
    return render(request, 'about.html')

def services(request):
    return render(request, 'services.html')

def contact(request):
    return render(request, 'contact.html')

# Make sure to add this import at the top if you haven't already:
# from django.contrib.auth.decorators import login_required

@login_required(login_url='login')
def cart(request):
    cart_obj, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart_obj.items.all()
    
    # Process quantity updates if the user clicks "Update Quantities"
    if request.method == 'POST':
        for item in cart_items:
            # Capture the specific quantity input for this item ID
            new_quantity = request.POST.get(f'quantity_{item.id}')
            if new_quantity and new_quantity.isdigit() and int(new_quantity) > 0:
                item.quantity = int(new_quantity)
                item.save()
        messages.success(request, "Cart quantities updated.")
        return redirect('cart')
        
    context = {
        'cart_items': cart_items,
    }
    return render(request, 'cart.html', context)

@login_required(login_url='login')
def remove_from_cart(request, item_id):
    # Ensure the item exists and securely belongs to the logged-in user
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, f"{cart_item.product.name} removed from cart.")
    return redirect('cart')
# --- New Authentication Views ---
def register_view(request):
    if request.method == 'POST':
        # 1. Grab data from the HTML form
        username = request.POST.get('username')
        email = request.POST.get('email')
        mobile_number = request.POST.get('mobile_number')
        company_name = request.POST.get('company_name')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # 2. Basic Validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect('register')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken!")
            return redirect('register')

        # 3. Create the user
        try:
            user = CustomUser(
                username=username,
                email=email,
                mobile_number=mobile_number,
                company_name=company_name
            )
            user.set_password(password) # This securely hashes the password
            user.full_clean() # This triggers the required email/phone rules we wrote earlier!
            user.save()
            
            messages.success(request, "Account created successfully! Please log in.")
            return redirect('login')
            
        except ValidationError as e:
            # If the clean() method fails, show the errors
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
            return redirect('register')

    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Django checks if the username and password match
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # 1. Check if the admin has approved/verified the account yet
            if not user.is_verified:
                messages.warning(request, "You have to wait while admin will approve your request.")
                return redirect('login')
            
            # 2. Check if the admin has disabled their access via is_active
            if not user.is_active:
                messages.error(request, "This account has been disabled.")
                return redirect('login')
                
            # 3. If verified and active, log them in!
            login(request, user)
            return redirect('home')
            
        else:
            messages.error(request, "Invalid username or password.")
            
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')

def forgot_password_view(request):
    if request.method == 'POST':
        # Placeholder logic: you need an email server configured to actually send emails!
        messages.success(request, "If that email exists in our system, a reset link has been sent.")
        return redirect('login')
    return render(request, 'forgot_password.html')





@login_required(login_url='login')
def profile_view(request):
    if request.method == 'POST':
        # Grab the updated data from the form
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.mobile_number = request.POST.get('mobile_number', '')
        request.user.company_name = request.POST.get('company_name', '')
        request.user.address = request.POST.get('address', '')
        request.user.zipcode = request.POST.get('zipcode', '')
        request.user.state = request.POST.get('state', '')
        request.user.country = request.POST.get('country', '')
        
        # Save the changes to the database
        request.user.save()
        
        messages.success(request, "Your profile has been updated successfully!")
        return redirect('profile')
        
    return render(request, 'profile.html')


def product_detail(request, unique_code):
    # Fetch the product using its unique code. Ensure it is active!
    product = get_object_or_404(Product, unique_code=unique_code, is_active=True)
    
    return render(request, 'product_detail.html', {'product': product})


# Add this new function to your views.py
@login_required(login_url='login')
def add_to_cart(request, unique_code):
    # 1. Get the specific product they clicked on
    product = get_object_or_404(Product, unique_code=unique_code, is_active=True)
    
    # 2. Get the current logged-in user's cart (or create an empty one)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # 3. Check if this exact product is already in their cart
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not item_created:
        # If it's already in the cart, just increase the quantity by 1
        cart_item.quantity += 1
        cart_item.save()
        messages.success(request, f"Added another {product.name} to your cart.")
    else:
        # If it is a new item, it defaults to a quantity of 1
        messages.success(request, f"{product.name} was added to your cart.")
        
    # --- THIS IS THE ONLY LINE THAT CHANGES ---
    # Send the user back to the page they just came from, or default to 'shop' just in case!
    return redirect(request.META.get('HTTP_REFERER', 'shop'))
    # 1. Get the specific product they clicked on
    product = get_object_or_404(Product, unique_code=unique_code, is_active=True)
    
    # 2. Get the current logged-in user's cart (or create an empty one if it doesn't exist)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # 3. Check if this exact product is already in their cart
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not item_created:
        # If it's already in the cart, just increase the quantity by 1
        cart_item.quantity += 1
        cart_item.save()
        messages.success(request, f"Added another {product.name} to your cart.")
    else:
        # If it is a new item, it defaults to a quantity of 1
        messages.success(request, f"{product.name} was added to your cart.")
        
    # 4. Redirect them to the cart page so they can see it!
    return redirect('cart')


@login_required(login_url='login')
def cart(request):
    cart_obj, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart_obj.items.all()
    
    # We removed the cart_total calculation here!
    
    context = {
        'cart_items': cart_items,
    }
    return render(request, 'cart.html', context)

# @login_required(login_url='login')
# def send_inquiry(request):
#     cart_obj, created = Cart.objects.get_or_create(user=request.user)
#     cart_items = cart_obj.items.all()
    
#     if not cart_items.exists():
#         messages.warning(request, "Your cart is empty.")
#         return redirect('cart')
        
#     # 1. CREATE THE DATABASE INQUIRY RECORD
#     inquiry = Inquiry.objects.create(user=request.user)
    
#     # Build text for the email and save snapshots of the products
#     email_items_text = ""
#     for item in cart_items:
#         # Save snapshot into InquiryItem table
#         InquiryItem.objects.create(
#             inquiry=inquiry,
#             product=item.product,
#             product_name_snapshot=item.product.name,
#             product_code_snapshot=item.product.unique_code,
#             quantity=item.quantity
#         )
#         email_items_text += f"• {item.product.name} (Code: {item.product.unique_code}) | Quantity: {item.quantity}\n"

#     # 2. BUILD THE EMAIL MESSAGE
#     subject = f"New Product Inquiry #{inquiry.id} from {request.user.username}"
#     message = f"Hello {request.user.first_name or request.user.username},\n\n"
#     message += f"Thank you for your inquiry (Reference ID: #{inquiry.id})! Here are the details of the products you requested. Our team will review the material specifications and follow up with a custom quote shortly.\n\n"
#     message += "--- INQUIRY DETAILS ---\n"
#     message += email_items_text
#     message += "\n-----------------------\n"
#     message += f"Customer Email: {request.user.email}\n"
#     message += f"Mobile: {request.user.mobile_number}\n"
#     message += f"Company: {request.user.company_name}\n"
    
#     # 3. SEND THE EMAIL & CLEAR CART
#     try:
#         send_mail(
#             subject,
#             message,
#             'sales@yourcompany.com',
#             [request.user.email, 'sales@yourcompany.com'],
#             fail_silently=False,
#         )
        
#         # Clear the cart now that inquiry is safely logged
#         cart_items.delete()
#         messages.success(request, f"Inquiry #{inquiry.id} sent successfully! Check your terminal for a copy.")
        
#     except Exception as e:
#         messages.error(request, "There was an error sending your inquiry. Please try again later.")
        
#     return redirect('cart')
#     # 1. Get the user's cart
#     cart_obj, created = Cart.objects.get_or_create(user=request.user)
#     cart_items = cart_obj.items.all()
    
#     if not cart_items.exists():
#         messages.warning(request, "Your cart is empty.")
#         return redirect('cart')
        
#     # 2. Build the email message
#     subject = f"New Product Inquiry from {request.user.username}"
#     message = f"Hello {request.user.first_name or request.user.username},\n\n"
#     message += "Thank you for your interest! Here are the details of the products you wish to inquire about. We will review the material requirements and get back to you with the final pricing.\n\n"
#     message += "--- INQUIRY DETAILS ---\n"
    
#     for item in cart_items:
#         message += f"• {item.product.name} (Code: {item.product.unique_code}) | Quantity: {item.quantity}\n"
        
#     message += "\n-----------------------\n"
#     message += f"Customer Email: {request.user.email}\n"
#     message += f"Mobile: {request.user.mobile_number}\n"
#     message += f"Company: {request.user.company_name}\n"
    
#     # 3. Send the email
#     try:
#         send_mail(
#             subject,
#             message,
#             'sales@yourcompany.com', # From (Your company)
#             [request.user.email, 'sales@yourcompany.com'], # To (The user AND your company)
#             fail_silently=False,
#         )
        
#         # 4. Clear the cart after sending the email
#         cart_items.delete()
#         messages.success(request, "Your inquiry has been sent successfully! Check your email for a copy.")
        
#     except Exception as e:
#         messages.error(request, "There was an error sending your inquiry. Please try again later.")
        
#     return redirect('cart')

@login_required(login_url='login')
def send_inquiry(request):
    cart_obj, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart_obj.items.all()
    
    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('cart')
        
    # 1. CREATE THE DATABASE INQUIRY RECORD
    inquiry = Inquiry.objects.create(user=request.user)
    
    # Build text for the email and save snapshots of the products
    email_items_text = ""
    for item in cart_items:
        InquiryItem.objects.create(
            inquiry=inquiry,
            product=item.product,
            product_name_snapshot=item.product.name,
            product_code_snapshot=item.product.unique_code,
            quantity=item.quantity
        )
        email_items_text += f"• {item.product.name} (Code: {item.product.unique_code}) | Quantity: {item.quantity}\n"

    # 2. BUILD THE EMAIL MESSAGE
    subject = f"New Product Inquiry #{inquiry.id} from {request.user.username}"
    message = f"Hello {request.user.first_name or request.user.username},\n\n"
    message += f"Thank you for your inquiry (Reference ID: #{inquiry.id})! Here are the details of the products you requested. Our team will review the material specifications and follow up with a custom quote shortly.\n\n"
    message += "--- INQUIRY DETAILS ---\n"
    message += email_items_text
    message += "\n-----------------------\n"
    message += f"Customer Email: {request.user.email}\n"
    message += f"Mobile: {request.user.mobile_number}\n"
    message += f"Company: {request.user.company_name}\n"
    
    # 3. SEND THE EMAIL VIA GMAIL & CLEAR CART
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [request.user.email, settings.DEFAULT_FROM_EMAIL],
            fail_silently=False,
        )
        
        cart_items.delete()
        messages.success(request, f"Inquiry #{inquiry.id} sent successfully!")
        
    except Exception as e:
        messages.error(request, "There was an error sending your inquiry. Please try again later.")
        
    return redirect('cart')


@login_required(login_url='login')
def client_inquiries(request):
    # Fetch all inquiries made by this specific user, newest first
    inquiries = Inquiry.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'inquiries': inquiries,
    }
    return render(request, 'client_inquiries.html', context)