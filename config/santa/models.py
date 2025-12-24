from django.db import models
from django.contrib.auth.models import User

class Event(models.Model):
    event_name = models.CharField(max_length=30)
    organizer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="organized_events"
    )
    event_date = models.DateField()
    budget = models.CharField(max_length=20, blank=True)
    time = models.TimeField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.event_name

   
class Participant(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='participants')
    name = models.CharField(max_length=50)
    email = models.EmailField()

    def __str__(self):
        return f"{self.name} ({self.email})"
    

#the genereated match giver to reciver
class Match(models.Model): 
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='matches')
    giver = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='matches_as_giver')
    receiver = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='matches_as_receiver')

    def __str__(self):
        return f"{self.giver.name} → {self.receiver.name}"

#class Wishlist(models.Model):
 #   pass

