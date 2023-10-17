from django.shortcuts import render
from django.urls import reverse, resolve, Resolver404
from .models import Dish, Meal
from django.utils import timezone
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
)


# Create your views here.


def meal_schedule(request):

    date_now = timezone.now().date()
    meals = Meal.objects.filter(date__gte=date_now).order_by("date")

    return render(request, "chef/meal_schedule.html", {"meals": meals})


def dish_list(request):
    dishes = Dish.objects.all().order_by("title")
    return render(request, "chef/dish_list.html", {"dishes": dishes})


class DishCreate(CreateView):

    # The automatic template _name_ generated for this view is dish_form.html

    model = Dish
    fields = [
        "title",
        "text",
    ]

    def setup(self, request, *args, **kwargs):
        # Run all of the setup() method from the base class - we don't
        # want to skip that because we need self.request to be set
        super().setup(request, *args, **kwargs)

        # Check the referrer to see if we came from the meal-creation view
        referring_url = request.META.get("HTTP_REFERER")
        # referring_url is the whole thing eg https://example.com/meal/add/
        # but we only want /meal/add/ which comes after the example.com hostname

        hostname = request.get_host()

        split_referring_url = referring_url.split(hostname)
        # this gives us a list containing the "scheme" (http:// or https://) and the path
        # eg ["https://", "/meal/add/"]
        # and we can just take the last element there because that's the path

        referring_path = split_referring_url[1]
        # eg /meal/add/

        # now let's be sure it's the MealCreate view that it's for, because
        # that's the only one we want to go back to as a special case
        try:
            resolver_match = resolve(referring_path)
            if resolver_match.func.view_class == MealCreate:
                # OK, the referring page was definitely generated by MealCreate, so we know
                # referring_path will send us back to a useful destination

                # So let's put that in the session, ready for another view to check
                self.request.session["special_success_url"] = referring_path

        except (Resolver404, AttributeError):
            # Resolver404 is raised if there is no match for referring_path
            # AttributeError can be raised if the matched view is a traditional
            # function-based one with no view_class attr
            pass

    def get_context_data(self):

        context = super().get_context_data()
        context["title"] = "Create a new dish"

        return context

    def get_success_url(self):

        # Is there a special URL in the session? If so redirect to there.

        special_dest = self.request.session.get("special_success_url")
        if special_dest:
            # remember to clean up the session so that we don't risk falsely signalling
            # that a future visit to this view also came from MealCreate
            del self.request.session["special_success_url"]

            return special_dest

        # The get and del steps above can be done in one go with pop()
        # special_dest = self.request.pop("special_success_url", None)
        # if special_dest:
        #     return special_dest

        return reverse("dish-list")


class DishUpdate(UpdateView):

    # The automatic template _name_ generated for this view is dish_form.html

    model = Dish
    fields = [
        "title",
        "text",
    ]

    def get_context_data(self):

        context = super().get_context_data()
        context["title"] = "Edit dish"
        return context

    def get_success_url(self):

        return reverse("dish-list")


class DishDelete(DeleteView):
    model = Dish

    def get_success_url(self):
        return reverse("dish-list")


class FormDateInputMixin:
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Django's DateInput uses type = "text", but we can force it
        # to "date" to get a datepicker from the browser
        for fieldname in self.date_fields:
            form.fields[fieldname].widget.input_type = "date"
        return form


class MealCreate(FormDateInputMixin, CreateView):

    # The automatic template _name_ generated for this view is meal_form.html

    model = Meal
    fields = [
        "dish",
        "date",
    ]
    date_fields = ["date"]

    def get_context_data(self):

        context = super().get_context_data()
        context["title"] = "Schedule a new meal"

        return context

    def get_success_url(self):

        return reverse("meal-schedule")


class MealUpdate(FormDateInputMixin, UpdateView):

    # The automatic template _name_ generated for this view is meal_form.html

    model = Meal
    fields = [
        "dish",
        "date",
    ]
    date_fields = ["date"]

    def get_context_data(self):

        context = super().get_context_data()
        context["title"] = "Edit meal"
        return context

    def get_success_url(self):

        return reverse("meal-schedule")


class MealDelete(DeleteView):
    model = Meal

    def get_success_url(self):
        return reverse("meal-schedule")


def meal_list(request):

    meals = Meal.objects.all().order_by("date")

    return render(request, "chef/meal_list.html", {"meals": meals})
