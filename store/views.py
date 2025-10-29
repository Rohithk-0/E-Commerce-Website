from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def home(request):
    return render(request, 'store/home.html')

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm = request.POST['confirm']
        if password == confirm:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()
                messages.success(request, 'Registration successful! Please login.')
                return redirect('login')
        else:
            messages.error(request, 'Passwords do not match')
    return render(request, 'store/register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'store/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Product



# Utility: check if user is staff/admin
def is_admin(user):
    return user.is_staff or user.is_superuser


@login_required
def dashboard(request):
    # Only admin should see all products & CRUD options
    if request.user.is_staff or request.user.is_superuser:
        products = Product.objects.all().order_by('-created_at')
        return render(request, 'store/dashboard.html', {'products': products})
    else:
        # Normal user sees only store page
        products = Product.objects.all()
        return render(request, 'store/user_dashboard.html', {'products': products})


# === ADMIN-ONLY PRODUCT CRUD ===

@user_passes_test(is_admin)
def add_product(request):
    if request.method == 'POST':
        name = request.POST['name']
        category = request.POST['category']
        description = request.POST['description']
        price = request.POST['price']
        image = request.FILES.get('image')
        Product.objects.create(
            name=name, category=category, description=description,
            price=price, image=image
        )
        messages.success(request, 'Product added successfully!')
        return redirect('dashboard')
    return render(request, 'store/add_product.html')


@user_passes_test(is_admin)
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.name = request.POST['name']
        product.category = request.POST['category']
        product.description = request.POST['description']
        product.price = request.POST['price']
        if request.FILES.get('image'):
            product.image = request.FILES['image']
        product.save()
        messages.success(request, 'Product updated successfully!')
        return redirect('dashboard')
    return render(request, 'store/edit_product.html', {'product': product})


@user_passes_test(is_admin)
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, 'Product deleted successfully!')
    return redirect('dashboard')

from .models import Product, Cart, Order, OrderItem
from decimal import Decimal
from django.db.models import Sum

# === CART VIEWS ===

@login_required
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    messages.success(request, f"{product.name} added to your cart.")
    return redirect('shop')

@login_required
def view_cart(request):
    cart_items = Cart.objects.filter(user=request.user)
    total = sum(item.total_price() for item in cart_items)
    return render(request, 'store/cart.html', {'cart_items': cart_items, 'total': total})

@login_required
def remove_from_cart(request, pk):
    cart_item = get_object_or_404(Cart, pk=pk, user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from your cart.")
    return redirect('view_cart')


# === ORDER VIEWS ===

@login_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user)
    if not cart_items:
        messages.warning(request, "Your cart is empty!")
        return redirect('shop')  # or 'dashboard'

    total = sum(item.total_price() for item in cart_items)

    # Create Order with correct field name
    order = Order.objects.create(user=request.user, total_price=total)

    # Create OrderItems
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price
        )

    cart_items.delete()
    messages.success(request, f"Order #{order.id} placed successfully!")
    return redirect('order_history')



@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/orders.html', {'orders': orders})


from django.db.models import Q
from .models import Product, Category, Rating, Wishlist

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'store/product_detail.html', {'product': product})


def shop(request):
    query = request.GET.get('q')
    category_slug = request.GET.get('category')

    products = Product.objects.all()
    categories = Category.objects.all()

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    if category_slug:
        products = products.filter(category__slug=category_slug)

    context = {
        'products': products,
        'categories': categories,
        'selected_category': category_slug,
        'query': query
    }
    return render(request, 'store/shop.html', context)

from django.db.models import Sum, Count
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def analytics_dashboard(request):
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_products = Product.objects.count()

    top_products = (
        Order.objects.values('product__name')
        .annotate(total_sold=Count('product'))
        .order_by('-total_sold')[:5]
    )

    daily_sales = (
        Order.objects.extra(select={'day': 'date(created_at)'})
        .values('day')
        .annotate(revenue=Sum('total_price'))
        .order_by('day')
    )

    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_products': total_products,
        'top_products': top_products,
        'daily_sales': daily_sales,
    }

    return render(request, 'store/admin_analytics.html', context)

@login_required
def add_to_wishlist(request, pk):
    product = get_object_or_404(Product, pk=pk)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    messages.success(request, 'Added to wishlist ❤️')
    return redirect('shop')


@login_required
def view_wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'store/wishlist.html', {'wishlist': wishlist_items})


@login_required
def add_rating(request, pk):
    product = get_object_or_404(Product, pk=pk)
    stars = int(request.POST.get('stars', 0))
    rating, created = Rating.objects.update_or_create(
        user=request.user, product=product, defaults={'stars': stars}
    )
    messages.success(request, f'You rated {stars}⭐ for {product.name}')
    return redirect('product_detail', pk=pk)


def about(request):
    return render(request, 'store/about.html')

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        # Here you can save to database or send email later
        from django.contrib import messages
        messages.success(request, "Thank you for contacting us! We'll get back to you soon.")
        return redirect('contact')
    return render(request, 'store/contact.html')
