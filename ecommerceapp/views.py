from django.shortcuts import render,redirect, get_object_or_404
from ecommerceapp.models import Contact,RoomType,OrderUpdate,Orders, Rating
from django.contrib import messages
from math import ceil
from django.contrib.auth.decorators import login_required
from .forms import RatingForm
from django.db.models import Avg, Sum
from django.shortcuts import redirect
from datetime import datetime
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count


# Create your views here.
def index(request):
    room_names = RoomType.objects.values_list('room_name', flat=True).distinct()
    categories = RoomType.objects.values_list('category', flat=True).distinct()
    subcategories = RoomType.objects.values_list('subcategory', flat=True).distinct()


    selected_room_name = request.GET.get('room_name')
    selected_category = request.GET.get('category')
    selected_subcategory = request.GET.get('subcategory')

    rooms = RoomType.objects.all()

    if selected_room_name:
        rooms = rooms.filter(room_name=selected_room_name)

    if selected_category:
        rooms = rooms.filter(category=selected_category)

    if selected_subcategory:
        rooms = rooms.filter(subcategory=selected_subcategory)

   
    allRooms = []
    room_category = rooms.values('category', 'id')
    categories = {item['category'] for item in room_category}

    for cat in categories:
        prod = rooms.filter(category=cat)
        n = len(prod)
        nSlides = n // 4 + ceil((n / 4) - (n // 4))
        allRooms.append([prod, range(1, nSlides), nSlides])

    params = {
        'allRooms': allRooms,
        'room_names': room_names,
        'categories': categories,
        'subcategories': subcategories,
        'selected_room_name': selected_room_name,
        'selected_category': selected_category,
        'selected_subcategory': selected_subcategory, 
    }

    return render(request, "index.html", params)

def room_detail(request, room_id):
    room = get_object_or_404(RoomType, id=room_id)
    return render(request, 'room_detail.html', {'room': room})
    
def contact(request):
    if request.method=="POST":
        name=request.POST.get("name")
        email=request.POST.get("email")
        desc=request.POST.get("desc")
        pnumber=request.POST.get("pnumber")
        myquery=Contact(name=name,email=email,desc=desc,phonenumber=pnumber)
        myquery.save()
        messages.info(request,"we will get back to you soon..")
        return render(request,"contact.html")

    return render(request,"contact.html")

def about(request):
    return render(request,"about.html")


def checkout(request):
    if not request.user.is_authenticated:
        messages.warning(request,"Login & Try Again")
        return redirect('/auth/login')

    if request.method=="POST":
        items_json = request.POST.get('itemsJson', '')
        name = request.POST.get('name', '')
        amount = request.POST.get('amt')
        email = request.POST.get('email', '')
        address1 = request.POST.get('address1', '')
        address2 = request.POST.get('address2','')
        city = request.POST.get('city', '')
        state = request.POST.get('state', '')
        zip_code = request.POST.get('zip_code', '')
        phone = request.POST.get('phone', '')
        Order = Orders(items_json=items_json,name=name,amount=amount, email=email, address1=address1,address2=address2,city=city,state=state,zip_code=zip_code,phone=phone)
        print(amount)
        Order.save()
        update = OrderUpdate(order_id=Order.order_id,update_desc="Room has been Confirmed")
        update.save()
        thank = True
        return redirect('https://rzp.io/l/svCKVZETSh')
    
    return render(request, 'checkout.html')


@login_required
def room_detail(request, room_id):
    room = get_object_or_404(RoomType, id=room_id)
    user_rating = Rating.objects.filter(room=room, user=request.user).first()

    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            rating = form.cleaned_data['rating']
            comment = form.cleaned_data['comment']

            if user_rating:
                user_rating.rating = rating
                user_rating.comment = comment
            else:
                user_rating = Rating.objects.create(
                    room=room,
                    user=request.user,
                    rating=rating,
                    comment=comment,
                )
            user_rating.save()
            return redirect('/')

    else:
        form = RatingForm()

    ratings = Rating.objects.filter(room=room).exclude(user=request.user)

    average_rating = Rating.objects.filter(room=room).aggregate(Avg('rating'))['rating__avg'] or 0

    if request.method == 'POST' and 'delete_rating' in request.POST:
        if user_rating:
            user_rating.delete()
            return redirect('room_detail', room_id=room_id)

    return render(request, 'room_detail.html', {'room': room, 'ratings': ratings, 'user_rating': user_rating, 'form': form, 'average_rating': average_rating})


def delete_booking(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Orders, order_id=order_id)

        if order.email == request.user.email:
            order.delete()
            messages.success(request, 'Booking deleted successfully.')
        else:
            messages.error(request, 'You do not have permission to delete this booking.')

    return redirect('/auth/profile/')


def update_appointment_date(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Orders, order_id=order_id)

        if order.email == request.user.email:
            appointment_date_str = request.POST.get('appointment_date')

            try:
                appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d').date()
                order.appointment_date = appointment_date
                order.updated_appointment_date = appointment_date  
                order.save()
                messages.success(request, 'Appointment date set successfully.')
            except ValueError:
                messages.error(request, 'Invalid date format. Please use YYYY-MM-DD format.')
        else:
            messages.error(request, 'You do not have permission to set the appointment date.')

    return redirect('/auth/profile/')

def is_admin(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(is_admin)
def dashboard(request):
    
    total_users = User.objects.count()
    total_reviews = Rating.objects.count()
    average_ratings = Rating.objects.aggregate(total=Avg('rating'))['total']

    total_bookings = Orders.objects.count()
    total_revenue = Orders.objects.aggregate(total=Sum('amount'))['total']

    locations_highest_booking = RoomType.objects.values('category').annotate(num_bookings=Count('category')).order_by('-num_bookings')[:5]

    room_types_highest_booking = RoomType.objects.values('subcategory').annotate(num_bookings=Count('subcategory')).order_by('-num_bookings')[:5]

    locations_more_sales = RoomType.objects.values('category').annotate(total_sales=Sum('price')).order_by('-total_sales')[:5]

    room_types_more_sales = RoomType.objects.values('subcategory').annotate(total_sales=Sum('price')).order_by('-total_sales')[:5]

    context = {
        'total_users': total_users,
        'total_reviews': total_reviews,
        'average_ratings': average_ratings,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'locations_highest_booking': locations_highest_booking,
        'room_types_highest_booking': room_types_highest_booking,
        'locations_more_sales': locations_more_sales,
        'room_types_more_sales': room_types_more_sales,
    }

    return render(request, 'dashboard.html', context)

