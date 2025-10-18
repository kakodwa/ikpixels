from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse

from .models import (
    Client, ContactMessage, WithdrawalRequest,
    ExternalLink, Product, Order, OrderItem, PaymentAttempt,Gallery
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
    return redirect(reverse("/"))


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
