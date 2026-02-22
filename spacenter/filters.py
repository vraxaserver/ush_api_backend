from admin_searchable_dropdown.filters import AutocompleteFilter
from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _


class CountryFilter(AutocompleteFilter):
    title = 'Country' # display title
    field_name = 'country' # name of the foreign key field

class CityFilter(AutocompleteFilter):
    title = 'City' # display title
    field_name = 'city' # name of the foreign key field


class ServiceSpaCenterFilter(AutocompleteFilter):
    """Filter services by spa center (M2M relationship)."""
    title = 'Spa Center'
    field_name = 'spa_centers'
    rel_model = None  # Will be auto-detected
    
    @property
    def parameter_name(self):
        return 'spa_centers__id__exact'

class ServiceArrangementServiceFilter(AutocompleteFilter):
    title = 'Service' # display title
    field_name = 'service' # name of the foreign key field