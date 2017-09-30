from django import forms


class Input(forms.Form):
    temperature = forms.FloatField()
    pressure = forms.FloatField()
    humidity = forms.FloatField()
    ozone = forms.FloatField()
    time = forms.IntegerField()
    city = forms.CharField()