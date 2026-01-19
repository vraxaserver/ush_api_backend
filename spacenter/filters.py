from admin_searchable_dropdown.filters import AutocompleteFilter


class CountryFilter(AutocompleteFilter):
    title = 'Country' # display title
    field_name = 'country' # name of the foreign key field

class CityFilter(AutocompleteFilter):
    title = 'City' # display title
    field_name = 'city' # name of the foreign key field


class TherapistCityFilter(AutocompleteFilter):
    title = 'City' # display title
    field_name = 'spa_center__city' # name of the foreign key field

class TherapistCountryFilter(AutocompleteFilter):
    title = 'Country' # display title
    field_name = 'spa_center__country' # name of the foreign key field

class TherapistSpaCenterFilter(AutocompleteFilter):
    title = 'Spa Center' # display title
    field_name = 'spa_center__name' # name of the foreign key field

