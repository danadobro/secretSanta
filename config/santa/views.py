from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Event, Participant

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Invalid email")
            return redirect("login")

        user = authenticate(request, username=user_obj.username, password=password)

        if user is None:
            messages.error(request, "Invalid password")
            return redirect("login")

        login(request, user)
        return redirect("home")

    
    return render(request, 'login.html') # if the user did not submit the form and is just visiting login, show login page


def signup_view(request):
    if request.method == "POST":
        name = request.POST.get('first_name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        #check if the email is already in use
        if User.objects.filter(email=email).exists():
            messages.info(request, "Email already has an account")
            return redirect("signup")
        
        # Create new user and use email as username
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name
        )
        
        # Display an information message indicating successful account creation
        messages.info(request, "Account created Successfully! Please Login")
        return redirect("login")
    
    return render(request, 'signup.html')



def home(request):
    return render(request, 'home.html')

def logout_view(request):
    logout(request)
    return redirect("home")

@login_required
def create_event(request):
    organizer_name = request.user.first_name
    organizer_email = request.user.email
    if request.method == "POST":
        # collect participants 1-30
        participants = []

        for i in range(1, 31):
            name = (request.POST.get(f"p{i}", "") or "").strip()
            email = (request.POST.get(f"p{i}_email", "") or "").strip()

            # If both are empty, user didn't fill this slot, skip it
            if not name and not email:
                continue

            # If one is filled but the other isn't, error
            if not name or not email:
                return render(request, "santa/create_event.html", {
                    "organizer_name": organizer_name,
                    "organizer_email": organizer_email,
                    "extra_range": range(5, 31),
                    "error": f"Participant {i}: please enter BOTH a name and an email."
                })

            participants.append((name, email))
        #the return if the error is the participant amount
        if not (4 <= len(participants) <= 30):
                return render(request, "santa/create_event.html", {
                    "organizer_name": organizer_name,
                    "organizer_email": organizer_email,
                    "extra_range": range(5, 31),
                    "error": "Add between 4 and 30 participants."
                })
        #prevent duplicates
         #the return if the error is the duplicates
        lowered = [name.lower() for name, email in participants]
        if len(lowered) != len(set(lowered)):
            return render(request, "santa/create_event.html", {
                "organizer_name": organizer_name,
                "organizer_email": organizer_email,
                "extra_range": range(5, 31),
                "error": "Names must be unique."
                })
        


        event_name = (request.POST.get("event_name", "") or "").strip()
        event_date = (request.POST.get("event_date", "") or "").strip()
        event_time = (request.POST.get("event_time", "") or "").strip()
        event_location = (request.POST.get("event_location", "") or "").strip()
        event_budget = (request.POST.get("event_budget", "") or "").strip()




        #create the event model object and return the event page
        event = Event.objects.create(organizer=request.user, event_name=event_name, event_date=event_date, budget = event_budget, time=event_time, location=event_location )  # ******************************
        for name, email in participants:
            Participant.objects.create(event=event, name=name, email=email) #create participant model object tied to the event object 

        return redirect("event_detail") #, event_id=event.id) #********************************************************************************************************

    #the initial return view of the form
    return render(request, "santa/create_event.html", {  
        "organizer_name": organizer_name,
        "organizer_email": organizer_email,
        "extra_range": range(5, 31),
        })

@login_required
def event_view(request):
    return render(request, "santa/event.html")

        

