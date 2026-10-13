from django.db import models

class UserProfile(models.Model):
    telegram_id = models.BigIntegerField(unique=True, verbose_name="Telegram ID")
    username = models.CharField(max_length=150, blank=True, null=True, verbose_name="Имя пользователя")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"User {self.telegram_id} ({self.username or 'No Name'})"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название категории")
    
    # is_custom = models.BooleanField(default=False, verbose_name="Кастомная категория") 

    def __str__(self):
        return self.name

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('income', 'Доход'),
        ('expense', 'Расход'),
    ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=7, choices=TRANSACTION_TYPES, verbose_name="Тип")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Категория")
    
    raw_text = models.TextField(blank=True, null=True, verbose_name="Исходный текст пользователя")
    
    date = models.DateField(verbose_name="Дата операции")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.telegram_id} | {self.get_transaction_type_display()}: {self.amount} ."


# class Credit(models.Model):
#     """Кредиты и напоминания по ним"""
#     user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='credits')
#     name = models.CharField(max_length=50, verbose_name="Название кредита")
#     total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Общая сумма кредита")
#     monthly_payment = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ежемесячный платеж")
    
#     payment_day = models.IntegerField(verbose_name="День платежа (число месяца)")
    
    
#     reminded_this_month = models.BooleanField(default=False, verbose_name="Напомнили в этом месяце")

#     def __str__(self):
#         return f"{self.name} — {self.monthly_payment}  (каждого {self.payment_day} числа)"
 