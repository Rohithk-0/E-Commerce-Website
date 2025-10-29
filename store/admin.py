from django.contrib import admin
from .models import Category, Product, Cart, Order, OrderItem, Wishlist, Rating

# Register Category so it appears in admin
admin.site.register(Category)

# You can also register Product (probably already done)
admin.site.register(Product)

# Optional: register other models if you want to manage them via admin
admin.site.register(Cart)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Wishlist)
admin.site.register(Rating)
