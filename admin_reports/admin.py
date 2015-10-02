import unicodecsv as csv
from django.contrib import admin
from django.http import HttpResponse
from django.contrib.admin.utils import display_for_value, label_for_field
from django.utils.translation import ugettext_lazy as _


class ReportFilter(admin.SimpleListFilter):
    template = 'report.html'
    title = _("Get report")
    parameter_name = 'generate_report'

    def lookups(self, request, model_admin):
        return [(1, 'Download Report'),]

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }

    def queryset(self, request, queryset):
        return queryset


class ReportAdminBase(admin.ModelAdmin):
    """
    Admin interface for being able to generate reports in the changelist view.
    """

    report_filename = "report.csv"

    def changelist_view(self, request, extra_context=None):
        list_filter = list(self.list_filter)
        if ReportFilter not in list_filter:
            list_filter.insert(0, ReportFilter)
            self.list_filter = list_filter
        is_report = request.GET.get('generate_report', None)
        if is_report:
            #make request mutable, fuck this... fuck that... fuck those
            request.GET._mutable = True
            request.GET.pop('generate_report')
            request.GET._mutable = False
            list_display = self.get_list_display(request)
            list_display_links = self.get_list_display_links(request, list_display)
            list_filter = self.get_list_filter(request)
            search_fields = self.get_search_fields(request)

            ChangeList = self.get_changelist(request)
            change_view = None
            try:
                change_view = ChangeList(
                    request, self.model, list_display, list_display_links, list_filter,
                    self.date_hierarchy, search_fields, self.list_select_related,
                    self.list_per_page, self.list_max_show_all, self.list_editable, self)
            except:
                pass
            if change_view:
                queryset = change_view.queryset
                response, writer = self.make_csv_response_and_writer()
                self.make_csv(queryset, writer)
                return response
        return super(ReportAdminBase, self).changelist_view(request, extra_context)

    def make_csv_response_and_writer(self):
        """
        Make a blank csv response and writer.
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s"' % self.report_filename
        writer = csv.writer(response)
        return response, writer

    def label_for_field(self, field_name):
    	return label_for_field(field_name, self.model, model_admin=self, return_attr=True)

    def make_csv(self, queryset, writer):
        headers = [self.label_for_field(field_name) for field_name in self.list_display]
        writer.writerow([head[0] for head in headers])
        for obj in queryset:
            row = []
            for index, key in enumerate(self.list_display):
                if hasattr(obj, key):
                    row.append(display_for_value(getattr(obj, key)))
                elif headers[index][1]:
                    try:
                        row.append(display_for_value(headers[index][1](obj)))
                    except:
                        row.append("")
                else:
                    row.append("")
            writer.writerow(row)
