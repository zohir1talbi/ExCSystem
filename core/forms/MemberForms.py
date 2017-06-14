from django import forms
from core.models import Member
from django.contrib.auth.forms import ReadOnlyPasswordHashField


class MemberCreationForm(forms.ModelForm):
    """A form for creating new members. Includes all the required
    fields, plus a repeated password."""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = Member
        fields = ('email', 'first_name', 'last_name', 'phone_number', 'rfid')

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(MemberCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class MemberChangeForm(forms.ModelForm):
    """A form for updating members. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = Member
        fields = ('email',
                  'password',
                  'date_joined',
                  'first_name',
                  'last_name',
                  'phone_number',
                  'rfid',
                  'status')

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]


class MemberViewForm(forms.ModelForm):
    """This form allows you to view all the information, without editing any of it"""

    class Meta:
        model = Member
        fields = ('email',
                  'password',
                  'date_joined',
                  'first_name',
                  'last_name',
                  'phone_number',
                  'rfid',
                  'is_admin')
