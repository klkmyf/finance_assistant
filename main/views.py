from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Sum
from .models import UserProfile, Transaction
from datetime import date, timedelta

def index(request): 
    return render(request, 'index.html')

def statistics(request):
    telegram_id = request.GET.get("telegram_id")
    period = request.GET.get("period", "all")

    if not telegram_id:
        return JsonResponse({"error": "Пользователь не найден"}, status=400)

    try:
        user = UserProfile.objects.get(telegram_id=telegram_id)
    except UserProfile.DoesNotExist:
        return JsonResponse({
            "expenses": [],
            "incomes": []
        })

    transactions = Transaction.objects.filter(user=user)

    if period == "today":
        transactions = transactions.filter(date=date.today())
        
    elif period == "week":
        transactions = transactions.filter(
            date__gte=date.today() - timedelta(days=6),
            date__lte=date.today()
        )
        
    elif period == "month":
        transactions = transactions.filter(
            date__gte=date.today().replace(day=1),
            date__lte=date.today()
        )
        
    elif period == "year":
        transactions = transactions.filter(
            date__gte=date.today().replace(month=1, day=1),
            date__lte=date.today()
        )

    elif period == "custom":
        date_from_str = request.GET.get("date_from")
        date_to_str = request.GET.get("date_to")

        transactions = transactions.filter(
            date__gte=date_from_str,
            date__lte=date_to_str
        )

    expenses = (
        transactions
        .filter(transaction_type="expense")
        .values("category__name")
        .annotate(amount=Sum("amount"))
        .order_by("-amount")
    )
    
    incomes = (
        transactions
        .filter(transaction_type="income")
        .values("category__name")
        .annotate(amount=Sum("amount"))
        .order_by("-amount")
    )
    
    return JsonResponse({
        "expenses": [
            {
                "category": x["category__name"] or "Без категории",
                "amount": x["amount"]
            }
            for x in expenses
        ],
        "incomes": [
            {
                "category": x["category__name"] or "Без категории",
                "amount": x["amount"]
            }
            for x in incomes
        ]
    })
