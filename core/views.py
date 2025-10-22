from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction

from .paychangu import (
    mobile_initialize_payment,
    card_initialize_payment,
    verify_paychangu_payment,
)
import uuid

from .models import (
    Client, ContactMessage, WithdrawalRequest,
    ExternalLink, Product, Order, OrderItem, PaymentAttempt,Gallery,Client
)


# -----------------------------------
# REGISTER VIEW
# -----------------------------------
@csrf_protect
def register_view(request):
    """
    Handles customer registration.
    Expected form fields:
        username, email, password, confirm_password, first_name, last_name
    """
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")
        first_name = request.POST.get("first_name", "")
        last_name = request.POST.get("last_name", "")

        # basic validation
        if not username or not password:
            return render(request, "core/register.html", {"error": "Username and password are required."})
        if password != confirm:
            return render(request, "core/register.html", {"error": "Passwords do not match."})
        if User.objects.filter(username=username).exists():
            return render(request, "core/register.html", {"error": "Username already exists."})

        user = User.objects.create_user(username=username, email=email, password=password)
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        # Client profile is auto-created via signal, but ensure it exists
        Client.objects.get_or_create(user=user)

        # auto-login after registration
        login(request, user)

        if user.is_superuser:
            return redirect("/")
        return redirect(reverse("/"))

    return render(request, "core/register.html")

@csrf_protect
def login_view(request):

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if user.is_superuser:
                return redirect("admin_dashboard")
            else:
                return redirect(reverse("/"))
        else:
            return render(request, "core/login.html", {"error": "Invalid username or password."})

    return render(request, "core/login.html")


@login_required
def admin_dashboard(request):
    return render(request, 'core/admin.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('index')


def index(request):
	context = {}
	context['products'] = Product.objects.all()[:3]
	context['gallery_items'] = Gallery.objects.all().order_by('id')[:3]
	return render(request,'core/home.html',context)

def about(request):
	return render(request,'core/about.html')

def services(request):
	return render(request,'core/service.html')

def contact(request):
	return render(request,'core/contact.html')

def gallery(request):
	context = {}
	context['gallery_items'] = Gallery.objects.all().order_by('-uploaded_at')[:12]
	return render(request,'core/gallery.html',context)

@login_required
def product_create(request):
    if request.method == 'POST':
        # Get data from form
        title = request.POST.get('item-title')
        price = request.POST.get('item-price')
        category = request.POST.get('item-category')
        description = request.POST.get('item-description')
        key_features = request.POST.get('item-features')
        technologies_used = request.POST.get('item-technologies')
        demo_url = request.POST.get('item-demo')  # optional
        preview_gradient = request.POST.get('item-gradient')
        file_url = request.POST.get('item-file-url')  # add a hidden input or field for file URL
        booked = False  # default
        views = 0
        sold_count = 0
        
        # Handle image upload
        image = request.FILES.get('item-image')  # <input type="file" name="item-image">

        # Create product
        product = Product.objects.create(
            title=title,
            price=price,
            category=category,
            description=description,
            key_features=key_features,
            technologies_used=technologies_used,
            demo_url=demo_url,
            preview_gradient='Purple Blue',
            file_url=file_url,
            image=image,
            views=views,
            sold_count=sold_count,
            booked=booked,
        )

        return redirect('product_detail', pk=product.pk)

    return render(request, 'products/product_form.html')


def marketplace(request):
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', 'all')
    page_number = request.GET.get('page', 1)

    products = Product.objects.all()

    if category_filter != 'all':
        products = products.filter(category__iexact=category_filter)

    if search_query:
        products = products.filter(title__icontains=search_query)

    paginator = Paginator(products, 8)  # 8 products per page
    page_obj = paginator.get_page(page_number)

    # Handle AJAX request (for lazy loading or search)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        products_data = []
        for product in page_obj:
            products_data.append({
                'id': product.id,
                'title': product.title,
                'price': str(product.price),
                'description': product.description[:100],
                'rating': product.views,
                'views': product.views,
                'category': product.category,
                'image': product.image.url if product.image else '',
            })
        return JsonResponse({
            'products': products_data,
            'has_next': page_obj.has_next(),
        })

    context = {
        'products': page_obj,
        'search_query': search_query,
        'category_filter': category_filter,
    }
    return render(request, 'core/marketplace.html', context)

# views.py
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.views += 1
    product.save()

    # Split technologies for template
    technologies = [tech.strip() for tech in product.technologies_used.split(',')]

    return render(request, 'core/product_detail.html', {
        'product': product,
        'technologies': technologies,
    })


# ----------------------------------------------------------
# 🟢 CREATE OR GET USER ORDER
# ----------------------------------------------------------
@login_required
def get_or_create_order(client):
    """Helper to get or create a pending order for client."""
    order, created = Order.objects.get_or_create(client=client, paid=False)
    return order


# ----------------------------------------------------------
# 💰 MOBILE MONEY PAYMENT
# ----------------------------------------------------------
@csrf_exempt
@login_required
def mobile_money_payment(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        return JsonResponse({"status": "failed", "message": "No client record found."}, status=400)

    if request.method == "POST":
        phone = request.POST.get("phone-number")
        provider = request.POST.get("provider") or request.POST.get("operator")
        email = request.user.email or "ikpixels.py@gmail.com"

        if not phone or not provider:
            return JsonResponse({"status": "failed", "message": "Missing phone or provider"}, status=400)

        # Create order if not exists
        order = get_or_create_order(client)
        order_item, _ = OrderItem.objects.get_or_create(
            order=order, product=product, defaults={"price": product.price, "qty": 1}
        )

        # Initialize payment with PayChangu
        result = mobile_initialize_payment(
            mobile=phone,
            operator=provider,
            amount=float(product.price),
            email=email,
        )

        print(result)

        if result.get("init_status") != "success":
            return JsonResponse({
                "status": "failed",
                "message": result.get("init_message", "Payment init failed."),
            }, status=400)

        tx_ref = result["charge_id"]

        # Record attempt
        PaymentAttempt.objects.create(
            order=order,
            tx_ref=tx_ref,
            payment_type="airtel" if "airtel" in provider.lower() else "mpamba",
            amount=product.price,
            email=email,
            metadata={"mobile": phone, "operator": provider},
            status="pending",
            raw_response=result,
        )

        return JsonResponse({
            "status": "success",
            "tx_ref": tx_ref,
            "message": result.get("message", "Awaiting mobile confirmation."),
        })

    # Always return JSON, even for GET requests
    return JsonResponse({
        "status": "failed",
        "message": "Invalid request method, POST required."
    }, status=400)

# ----------------------------------------------------------
# 💳 CARD (VISA/MASTERCARD) PAYMENT
# ----------------------------------------------------------
@csrf_exempt
@login_required
def card_payment(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    client = get_object_or_404(Client, user=request.user)

    if request.method == "POST":
        card_number = request.POST.get("card-number")
        expiry = request.POST.get("expiry")
        cvv = request.POST.get("cvv")
        cardholder_name = request.POST.get("cardholder-name")
        email = request.user.email or "guest@ikpixels.com"

        if not all([card_number, expiry, cvv, cardholder_name]):
            return JsonResponse({"error": "All fields are required"}, status=400)

        order = get_or_create_order(client)
        OrderItem.objects.get_or_create(
            order=order, product=product, defaults={"price": product.price, "qty": 1}
        )

        redirect_url = request.build_absolute_uri("/pay/verify/")

        result = card_initialize_payment(
            card_number=card_number,
            expiry=expiry,
            cvv=cvv,
            cardholder_name=cardholder_name,
            amount=float(product.price),
            currency="MWK",
            email=email,
            redirect_url=redirect_url,
        )

        if result.get("init_status") != "success":
            return JsonResponse(
                {
                    "status": "failed",
                    "message": result.get("init_message", "Card payment failed."),
                },
                status=400,
            )

        tx_ref = result["charge_id"]

        PaymentAttempt.objects.create(
            order=order,
            tx_ref=tx_ref,
            payment_type="visa",
            amount=product.price,
            email=email,
            metadata={"cardholder": cardholder_name},
            status="pending",
            raw_response=result,
        )

        return JsonResponse(
            {
                "status": "success",
                "tx_ref": tx_ref,
                "redirect_url": redirect_url,
                "message": result.get("message", "Card payment initialized."),
            }
        )

    return render(request, "payments/visa_payment_form.html", {"product": product})


# ----------------------------------------------------------
# 🔍 VERIFY PAYMENT
# ----------------------------------------------------------
@login_required
@csrf_exempt
def verify_payment(request, tx_ref):
    payment_type = request.POST.get("type", "card")

    if not tx_ref:
        return JsonResponse({"error": "Missing tx_ref"}, status=400)

    attempt = PaymentAttempt.objects.filter(tx_ref=tx_ref).first()
    if not attempt:
        return JsonResponse({"error": "Payment attempt not found"}, status=404)

    result = verify_paychangu_payment(tx_ref, payment_type=payment_type)
    status = result.get("status")

    attempt.raw_response = result
    attempt.status = "success" if status == "success" else "failed"
    attempt.save()

    if status == "success":
        order = attempt.order
        order.paid = True
        order.total = attempt.amount
        order.save()

        for item in order.items.all():
            item.product.mark_sold(1)

        return JsonResponse({"status": "success", "message": "Payment verified."})
    else:
        return JsonResponse({"status": "failed", "message": "Verification failed."})
