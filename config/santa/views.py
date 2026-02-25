from django.shortcuts import render, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Event, Participant, Exclusion, Match
from django.db.models import Q
from django.db import transaction
from .logic import generate_secret_santa_matches, dry_run_matches_from_restrictions
from django.core.mail import send_mail
from django.conf import settings

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
    return render(request, 'santa/home.html')

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



        # store in session until restrictions are added 
        request.session["event_data"] = {
            "event_name": event_name,
            "event_date": event_date,
            "event_time": event_time,
            "event_location": event_location,
            "event_budget": event_budget,
            }
        request.session["participants"] = [{"name": n, "email": e} for n, e in participants]


        return redirect("event_restrictions") 

    saved_event = request.session.get("event_data", {})
    saved_participants = request.session.get("participants", [])

    return render(request, "santa/create_event.html", {
        "organizer_name": organizer_name,
        "organizer_email": organizer_email,
        "extra_range": range(5, 31),
        "saved_event": saved_event,
        "saved_participants": saved_participants,
    })

@login_required
def event_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    is_organizer = (event.organizer == request.user)

    participant = Participant.objects.filter(event=event, email=request.user.email).first()

    my_match = None
    if participant:
        my_match = Match.objects.filter(event=event, giver=participant).select_related("receiver").first()

    all_matches = None
    if is_organizer:
        all_matches = Match.objects.filter(event=event).select_related("giver", "receiver").order_by("giver__name")

    return render(request, "santa/event.html", {
        "event": event,
        "is_organizer": is_organizer,
        "participant": participant,
        "my_match": my_match,
        "all_matches": all_matches,
    })


@login_required
def events(request):
    user = request.user

    events = Event.objects.filter(
        Q(organizer=user) |
        Q(participants__email=user.email)
    ).distinct()

    return render(request, "santa/events_list.html", {
        "events": events
    })


@login_required
def restrictions_view(request):
    event_data = request.session.get("event_data")
    participants = request.session.get("participants")  # list of dicts: {"name","email"}

    if not event_data or not participants:
        return redirect("create_event")

    if request.method == "GET":
        return render(request, "santa/restrictions.html", {
            "event_data": event_data,
            "participants": participants,
            "max_exclusions": max(0, len(participants) - 3),
        })

    # ---------- POST ----------
    n = len(participants)
    max_allowed = max(0, n - 3)

    # 1) Build restrictions_map (index-based) + validate
    restrictions_map = {}

    for giver_index in range(n):
        selected = request.POST.getlist(f"exclude_{giver_index}")

        if len(selected) > max_allowed:
            return render(request, "santa/restrictions.html", {
                "event_data": event_data,
                "participants": participants,
                "max_exclusions": max_allowed,
                "error": f"You can exclude at most {max_allowed} names per person."
            })

        forbidden = {giver_index}  # always forbid self
        for idx_str in selected:
            try:
                idx = int(idx_str)
            except ValueError:
                continue
            if 0 <= idx < n and idx != giver_index:
                forbidden.add(idx)

        restrictions_map[giver_index] = forbidden

    # 2) DRY RUN: test if matching is possible BEFORE saving event
    test_assignment = dry_run_matches_from_restrictions(n, restrictions_map)
    if test_assignment is None:
        return render(request, "santa/restrictions.html", {
            "event_data": event_data,
            "participants": participants,
            "max_exclusions": max_allowed,
            "error": "Too many restrictions — can't generate valid matches. Remove a few exclusions and try again."
        })

    # 3) Now it's safe: create event + participants + exclusions
    event = Event.objects.create(
        organizer=request.user,
        event_name=event_data["event_name"],
        event_date=event_data["event_date"],
        time=event_data.get("event_time") or None,
        location=event_data.get("event_location", ""),
        budget=event_data.get("event_budget", ""),
    )

    participant_objs = [
        Participant(event=event, name=p["name"], email=p["email"])
        for p in participants
    ]
    Participant.objects.bulk_create(participant_objs)

    participants_db = list(event.participants.all().order_by("id"))

    for giver_index, giver in enumerate(participants_db):
        selected = request.POST.getlist(f"exclude_{giver_index}")
        for idx_str in selected:
            try:
                idx = int(idx_str)
            except ValueError:
                continue
            if 0 <= idx < n and idx != giver_index:
                Exclusion.objects.create(
                    event=event,
                    giver=giver,
                    excluded=participants_db[idx]
                )

    # 4) Clear session
    request.session.pop("event_data", None)
    request.session.pop("participants", None)

    return redirect("event_details", event_id=event.id)


@login_required
def generate_matches_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    # organizer-only
    if event.organizer != request.user:
        messages.error(request, "Only the organizer can generate matches.")
        return redirect("event_details", event_id=event.id)

    if request.method != "POST":
        return redirect("event_details", event_id=event.id)

    with transaction.atomic():
        # If re-generating, clear old matches first
        Match.objects.filter(event=event).delete()

        matches = generate_secret_santa_matches(event)
        if matches is None:
            messages.error(request, "Too many restrictions — can't generate valid matches.")
            return redirect("event_details", event_id=event.id)

        # Save matches
        objs = []
        for giver, receiver in matches.items():
            objs.append(Match(event=event, giver=giver, receiver=receiver))
        Match.objects.bulk_create(objs)

        matches_qs = Match.objects.filter(event=event).select_related("giver", "receiver")
        sent = 0
        for m in matches_qs:
            send_match_email(event, m.giver, m.receiver)
            sent += 1

    messages.success(request, f"Matches generated and emailed to {sent} participants!")
    return redirect("event_details", event_id=event.id)

def send_match_email(event, giver, receiver):
    login_link = f"{settings.SITE_URL}/login/"
    subject = f"Your Secret Santa match for {event.event_name}"
    body = (
        f"Hi {giver.name},\n\n"
        f"You are getting a gift for: {receiver.name}.\n\n"
        f"Event details:\n"
        f"- Date: {event.event_date}\n"
        f"- Time: {event.time or '-'}\n"
        f"- Location: {event.location or '-'}\n"
        f"- Budget: {event.budget or '-'}\n\n"
        f"You can also log in using this email ({giver.email}) to view your match at {login_link}.\n"
    )

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[giver.email],
        fail_silently=False,
    )