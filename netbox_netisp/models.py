from django.db import models
from extras.models import ChangeLoggedModel
from datetime import datetime
from django.urls import reverse

class Customer(ChangeLoggedModel):
    first_name = models.CharField(max_length=30)
    middle_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    slug = models.SlugField(unique=True)

    def name(self):
        return "{0} {1} {2}".format(self.first_name, self.middle_name, self.last_name)

    def get_absolute_url(self):
        return reverse('plugins:netbox_netisp:customer', args=[self.slug])

class Address(ChangeLoggedModel):
    street_number = models.IntegerField()
    street_ordinance = models.CharField(max_length=1)
    street_name = models.CharField(max_length=255)
    street_suffix = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    state_code = models.CharField(max_length=2)
    zip = models.CharField(max_length=10)

    def get_absolute_url(self):
        return reverse('plugins:netbox_netisp:address_list')

