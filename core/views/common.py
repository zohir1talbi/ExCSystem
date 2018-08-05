from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView

from ExCSystem.settings import WEB_BASE


def get_default_context(obj, context):
    """Convenience function for getting the default context data of a member"""
    context['now'] = timezone.now()
    context['opts'] = obj.model._meta
    context['app_label'] = obj.model._meta.app_label
    context['change'] = False
    context['is_popup'] = False
    context['add'] = False
    context['save_as'] = False
    context['has_delete_permission'] = False
    context['has_change_permission'] = False
    context['has_add_permission'] = False
    return context


class ModelDetailView(DetailView):

    template_name = "admin/core/detail.html"
    field_sets = None

    def get_html_repr(self, obj):
        """
        Get the HTML to render the provided fields sets as a table

        will have the structure:

        <table>
            <tr><td>{{set_name}}</td></tr>
            <tr>
                <td>
                    <table>
                        <tr>
                            <td width="10px"></td>
                            <td>{field_name}</td>
                            <td><a href="field url">{field_value}</a></td>
                        </tr>
                    </table>
                </td>
            </tr>
            <tr><td>{{set_name}}</td></tr>
            <tr>
                <td>
                    <table>
                        <tr>
                            <td width="10px"></td>
                            <td>{field_name}</td>
                            <td><a href="field url">{field_value}</a></td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>


        values will be the string representations of the values saved for the given field
        if the value is a model object, then link will be the url to the related object
        """
        lines = []
        lines.append("<table>")
        for set in self.field_sets:
            set_name = set[0]
            lines.append(f"<tr><td>{set_name}</td></tr>")
            lines.append("<tr>\n<td>\n<table>")
            fields = set[1]["fields"]
            for field_name in fields:
                lines.append("<tr>")
                lines.append("<td width=\"10px\"></td>")
                lines.append(f"<td>{field_name}: </td>")
                value = getattr(obj, field_name)
                if hasattr(value, "DoesNotExist"):  # This allows us to check if the object is a model
                    app = value._meta.app_label
                    model = value._meta.model_name
                    link = WEB_BASE + reverse(f"admin:{app}_{model}_detail", kwargs={"pk": value.pk})
                    lines.append(f"<td><a href=\"{link}\">{str(value)}</a></td>")
                else:
                    lines.append(f"<td>{str(value)}</td>")
                lines.append("</tr>")
            lines.append("</table>\n</td>\n</tr>")

        lines.append("</table>")

        html = "\n".join(lines)
        return html

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = get_default_context(self, context)
        context['html_representation'] = self.get_html_repr(kwargs['object'])
        return context





