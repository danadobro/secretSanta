from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect

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

