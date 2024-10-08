from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db import IntegrityError
from django.db.models import Q
from django.db.models.functions import Lower
from django.shortcuts import render, redirect
from django.urls import reverse, resolve, Resolver404
from django.utils import timezone
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
)

from .forms import MealForm
from .helpers import meals_for_week, first_day_of_week, suggest_dishes
from .models import Dish, Meal

# Create your views here.


def meal_schedule(request):

    meals = {}
    date_now = timezone.now().date()

    current_week_label = "This week"

    if request.user.is_authenticated:

        # get the starts of week for the weeks we care about
        start_of_this_week = first_day_of_week(date_now)
        start_of_last_week = start_of_this_week - timedelta(days=7)
        start_of_next_week = start_of_this_week + timedelta(days=7)

        # now get the relevant meals info for each week and add it to our
        # overall meals dictionary

        # NB: the order things are added to the `meals` dictionary is significant. Modern Python
        # dictionaries remember the order keys are set, so when we loop through meals.items() we each
        # week's data in the order we set them in/the order we want to show them in.
        # This means we don't have to sort them by the date of the first day in each week
        # when read the `meals` dict.
        meals["Last week"] = meals_for_week(start_of_last_week, request.user)
        meals[current_week_label] = meals_for_week(start_of_this_week, request.user)
        meals["Next week"] = meals_for_week(start_of_next_week, request.user)

    return render(
        request,
        "chef/meal_schedule.html",
        {
            "meals": meals,
            "current_week_label": current_week_label,
        },
    )


def dish_list(request):
    dishes = Dish.objects.all().order_by(Lower("title")).filter(owner=request.user)

    if "q" in request.GET:
        query = request.GET["q"]
        dishes = dishes.filter(Q(title__icontains=query) | Q(text__icontains=query))

    least_recent_suggested_dishes = suggest_dishes(request.user)

    return render(
        request,
        "chef/dish_list.html",
        {
            "dishes": dishes,
            "dish_suggestions": least_recent_suggested_dishes,
        },
    )


class SetOwnerMixin:
    def form_valid(self, form):
        # first save the form as normal, using the method from the superclass
        # which sets self.object to be the thing we just saved
        retval = super().form_valid(form)

        # then tack on who the owner is:
        self.object.owner = self.request.user

        # catch an IntegrityError due to a database constraint and redirect the user to the homepage
        try:
            self.object.save()  # Needing a second save is not the most efficient solution, but it's fine for now
        except IntegrityError:

            # item_description = "That"
            # if hasattr(self.object, "title"):
            #     item_description = self.object.title

            item_description = getattr(self.object, "title", "That")

            messages.warning(
                self.request,
                f"{item_description} was a duplicate, which is not allowed",
            )
            return redirect(self.request.path)

        return retval


class DishCreate(SetOwnerMixin, CreateView):

    # The automatic template _name_ generated for this view is dish_form.html

    model = Dish
    fields = [
        "title",
        "text",
        "exclude_from_suggestions",
    ]

    def setup(self, request, *args, **kwargs):
        # Run all of the setup() method from the base class - we don't
        # want to skip that because we need self.request to be set
        super().setup(request, *args, **kwargs)

        # Check the referrer to see if we came from the meal-creation view
        referring_url = request.META.get("HTTP_REFERER")
        if not referring_url:
            return

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

    def get_initial(self):
        initial_data = super().get_initial()
        if "term" in self.request.GET:
            initial_data["title"] = self.request.GET["term"]
        return initial_data

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


class DishUpdate(UserPassesTestMixin, UpdateView):

    # The automatic template _name_ generated for this view is dish_form.html

    model = Dish
    fields = [
        "title",
        "text",
        "exclude_from_suggestions",
    ]

    # raise_exception is from AccessMixin (via UserPassesTestMixin):
    # complain about unauthorised users, rather than redirect to login
    raise_exception = True
    permission_denied_message = "That's not yours to update!"

    def get_context_data(self):

        context = super().get_context_data()
        context["title"] = "Edit dish"
        return context

    def get_success_url(self):

        return reverse("dish-list")

    def test_func(self):
        # Used by UserPassesTestMixin to determine if access is allowed
        dish = self.get_object()
        return self.request.user == dish.owner


class DishDelete(UserPassesTestMixin, DeleteView):
    model = Dish

    # raise_exception is from AccessMixin (via UserPassesTestMixin):
    # complain about unauthorised users, rather than redirect to login
    raise_exception = True
    permission_denied_message = "That's not yours to delete!"

    def get_success_url(self):
        return reverse("dish-list")

    def test_func(self):
        # Used by UserPassesTestMixin to determine if access is allowed
        dish = self.get_object()
        return self.request.user == dish.owner


class FormDateInputMixin:
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Django's DateInput uses type = "text", but we can force it
        # to "date" to get a datepicker from the browser
        for fieldname in self.date_fields:
            form.fields[fieldname].widget.input_type = "date"
        return form


class MealCreate(FormDateInputMixin, SetOwnerMixin, CreateView):

    # The automatic template _name_ generated for this view is meal_form.html

    model = Meal
    form_class = MealForm

    date_fields = ["date"]

    def get_context_data(self):

        context = super().get_context_data()
        context["title"] = "Schedule a new meal"

        return context

    def get_initial(self):
        initial_data = super().get_initial()
        if "dish_id" in self.request.GET:
            dish_id = self.request.GET["dish_id"]
            initial_data["dish"] = dish_id

        if "date" in self.request.GET:
            the_date = self.request.GET["date"]
            initial_data["date"] = the_date
        return initial_data

    def get_success_url(self):

        return reverse("meal-schedule")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user

        return kwargs


class MealUpdate(UserPassesTestMixin, FormDateInputMixin, UpdateView):

    # The automatic template _name_ generated for this view is meal_form.html

    model = Meal
    form_class = MealForm

    date_fields = ["date"]

    # raise_exception is from AccessMixin (via UserPassesTestMixin):
    # complain about unauthorised users, rather than redirect to login
    raise_exception = True
    permission_denied_message = "That's not yours to update!"

    def get_context_data(self):

        context = super().get_context_data()
        context["title"] = "Edit meal"
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user

        return kwargs

    def test_func(self):
        # Used by UserPassesTestMixin to determine if access is allowed
        meal = self.get_object()
        return self.request.user == meal.owner

    def get_success_url(self):

        return reverse("meal-schedule")


class MealDelete(UserPassesTestMixin, DeleteView):
    model = Meal

    # raise_exception is from AccessMixin (via UserPassesTestMixin):
    # complain about unauthorised users, rather than redirect to login
    raise_exception = True
    permission_denied_message = "That's not yours to delete!"

    def get_success_url(self):
        return reverse("meal-schedule")

    def test_func(self):
        # Used by UserPassesTestMixin to determine if access is allowed
        meal = self.get_object()
        return self.request.user == meal.owner


def meal_list(request):

    meals = Meal.objects.order_by("date").filter(owner=request.user)
    return render(request, "chef/meal_list.html", {"meals": meals})
