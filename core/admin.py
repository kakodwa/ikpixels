from django.contrib import admin
from .models import (
    Client, ContactMessage, WithdrawalRequest,
    ExternalLink, Product, Order, OrderItem, PaymentAttempt,Gallery
)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "district", "is_verified", "join_date")
    search_fields = ("user__username", "user__email", "phone")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("email", "subject", "created_at", "handled")
    readonly_fields = ("created_at",)


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ("client", "amount", "method", "status", "created_at")
    list_filter = ("method", "status")


@admin.register(ExternalLink)
class ExternalLinkAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "created_at", "created_by")
    search_fields = ("title", "url", "category")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "created_at")
    #prepopulated_fields = {"slug": ("title",)}

@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ('title', 'media_type', 'uploaded_at', 'is_active')
    list_filter = ('media_type', 'is_active', 'uploaded_at')
    search_fields = ('title', 'description')
    readonly_fields = ('uploaded_at',)
    ordering = ('-uploaded_at',)



admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(PaymentAttempt)
