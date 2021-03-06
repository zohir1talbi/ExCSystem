from core.forms.MemberForms import (
    MemberChangeCertsForm, MemberChangeGroupsForm, MemberChangeRFIDForm, MemberFinishForm,
    MemberUpdateContactForm, StafferDataForm
)
from core.models.MemberModels import Member, Staffer
from core.views.common import ModelDetailView, get_default_context
from core.views.ViewList import RestrictedViewList
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse
from django.views.generic.edit import UpdateView
from ExCSystem.settings import WEB_BASE


class MemberListView(RestrictedViewList):

    def can_view_all(self):
        """Only staffers should be a"""
        return self.request.user.has_permission("core.view_all_members")

    def set_restriction_filters(self):
        """Non-staffers should only be able to see themselves"""
        self.restriction_filters["pk__exact"] = self.request.user.pk


class MemberDetailView(UserPassesTestMixin, ModelDetailView):
    """Simple view that displays the all details of a user and provides access to specific change forms"""

    model = Member
    template_name = "admin/core/member/member_detail.html"

    raise_exception = True
    permission_denied_message = "You are not allowed to view another member's personal details!"

    def test_func(self):
        """Only allow members to see the detail page if it is for themselves, or they are staffers"""
        member_to_view = self.get_object()
        is_self = self.request.user.rfid == member_to_view.rfid
        view_others = self.request.user.has_permission('core.view_member')
        return view_others or is_self

    def post(self, request, *args, **kwargs):
        """Treat post requests as get requests"""
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **context):
        context['main_admin_url'] = WEB_BASE + "/admin"
        context['departments_url'] = WEB_BASE + "/admin/core/department"
        context['staffers_url'] = WEB_BASE + "/admin/core/staffer"
        return super(MemberDetailView, self).get_context_data(**context)


class MemberFinishView(UserPassesTestMixin, UpdateView):

    model = Member
    form_class = MemberFinishForm
    template_name_suffix = "_finish"

    raise_exception = True
    permission_denied_message = "You are not allowed complete the sign up process for anyone but yourself!"

    def test_func(self):
        """Only the member themselves is allowed to see the member finish page"""
        member_to_finish = self.get_object()
        return self.request.user.rfid == member_to_finish.rfid

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = get_default_context(self, context)
        return context

    def get_success_url(self):
        return WEB_BASE + reverse("admin:core_member_detail", kwargs={'pk': self.object.pk})


class StafferDetailView(UserPassesTestMixin, ModelDetailView):

    model = Staffer

    raise_exception = True
    permission_denied_message = "You are not allowed to view staffer details!"

    def test_func(self):
        """Only allow members to see the detail page if it is for themselves, or they are staffers"""
        return self.request.user.has_permission('core.view_staffer')
