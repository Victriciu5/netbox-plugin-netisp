from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import View
from django.contrib.contenttypes.models import ContentType
from django_tables2 import RequestConfig
from utilities.utils import csv_format, normalize_querydict, prepare_cloned_fields
from utilities.views import GetReturnURLMixin, ObjectPermissionRequiredMixin
from django.utils.html import escape
from django.utils.http import is_safe_url
from django.utils.safestring import mark_safe
from django.contrib import messages
import logging

class ObjectListView(View):
    """
    List a series of objects.

    Sutley disclaimer
        Code adapted from parent project as technically this part of the core
            and is not officially supported by the maintainers
        To adhere completely to the plugin guidelines, I believe we would have to re-write all the helper and utils
            Due to the scope of this project, creating a condensed wrapper of the core code feels adequate enough
    """
    queryset = None
    filterset = None
    filterset_form = None
    table = None
    template_name = 'netbox_netisp/generic/object_list.html'
    action_buttons = ('add', 'import', 'export')

    def get(self, request):

        model = self.queryset.model
        content_type = ContentType.objects.get_for_model(model)

        if self.filterset:
            self.queryset = self.filterset(request.GET, self.queryset).qs

        table = self.table(self.queryset, user=request.user)
        paginate = {
            'per_page': 5
        }
        RequestConfig(request, paginate).configure(table)

        context = {
            'content_type': content_type,
            'action_buttons': self.action_buttons,
            'table': table,
            'filter_form': self.filterset_form(request.GET, label_suffix='') if self.filterset_form else None,
        }

        return render(request, self.template_name, context)

class ObjectEditView(GetReturnURLMixin,View):
    """
    Create or edit a single object

    Sutley disclaimer
        Code adapted from parent project as technically this part of the core
            and is not officially supported by the maintainers
        To adhere completely to the plugin guidelines, I believe we would have to re-write all the helper and utils
            Due to the scope of this project, creating a condensed wrapper of the core code feels adequate enough
    """
    queryset = None
    model_form = None
    template_name = 'netbox_netisp/generic/object_edit.html'


    def get_object(self, kwargs):
        # Look up an existing object by slug or PK, if provided.
        if 'slug' in kwargs:
            return get_object_or_404(self.queryset, slug=kwargs['slug'])
        elif 'pk' in kwargs:
            return get_object_or_404(self.queryset, pk=kwargs['pk'])
        # Otherwise, return a new instance.
        return self.queryset.model()


    def alter_obj(self, obj, request, url_args, url_kwargs):
        # Allow views to add extra info to an object before it is processed. For example, a parent object can be defined
        # given some parameter from the request URL.
        return obj

    def get(self, request, *args, **kwargs):
        obj = self.alter_obj(self.get_object(kwargs), request, args, kwargs)

        initial_data = normalize_querydict(request.GET)
        form = self.model_form(instance=obj, initial=initial_data)

        return render(request, self.template_name, {
            'obj': obj,
            'obj_type': self.queryset.model._meta.verbose_name,
            'form': form,
            'return_url': self.get_return_url(request, obj),
        })

    def post(self, request, *args, **kwargs):
        logger = logging.getLogger('netbox.views.ObjectEditView')
        obj = self.alter_obj(self.get_object(kwargs), request, args, kwargs)
        form = self.model_form(
            data=request.POST,
            files=request.FILES,
            instance=obj
        )

        if form.is_valid():
            logger.debug("Form validation was successful")

            try:
                with transaction.atomic():
                    object_created = form.instance.pk is None
                    obj = form.save()

                    # Check that the new object conforms with any assigned object-level permissions
                    self.queryset.get(pk=obj.pk)

                msg = '{} {}'.format(
                    'Created' if object_created else 'Modified',
                    self.queryset.model._meta.verbose_name
                )
                logger.info(f"{msg} {obj} (PK: {obj.pk})")
                if hasattr(obj, 'get_absolute_url'):
                    msg = '{} <a href="{}">{}</a>'.format(msg, obj.get_absolute_url(), escape(obj))
                else:
                    msg = '{} {}'.format(msg, escape(obj))
                messages.success(request, mark_safe(msg))

                if '_addanother' in request.POST:

                    # If the object has clone_fields, pre-populate a new instance of the form
                    if hasattr(obj, 'clone_fields'):
                        url = '{}?{}'.format(request.path, prepare_cloned_fields(obj))
                        return redirect(url)

                    return redirect(request.get_full_path())

                return_url = form.cleaned_data.get('return_url')
                if return_url is not None and is_safe_url(url=return_url, allowed_hosts=request.get_host()):
                    return redirect(return_url)
                else:
                    return redirect(self.get_return_url(request, obj))

            except ObjectDoesNotExist:
                msg = "Object save failed due to object-level permissions violation"
                logger.debug(msg)
                form.add_error(None, msg)

        else:
            logger.debug("Form validation failed")

        return render(request, self.template_name, {
            'obj': obj,
            'obj_type': self.queryset.model._meta.verbose_name,
            'form': form,
            'return_url': self.get_return_url(request, obj),
        })

class HomeView(View):
    template_name = 'netbox_netisp/generic/home.html'
    def get(self, request):
        return render(request, self.template_name)