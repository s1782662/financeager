"""Tabular, frontend-representation of financeager period."""
from . import DEFAULT_TABLE
from .entries import BaseEntry, CategoryEntry


class Listing:
    """Holds Entries in hierarchical order. First-level children are
    CategoryEntries, second-level children are BaseEntries. Generator methods
    are provided to iterate over these."""

    CATEGORY_ENTRY_SORT_KEY = "value"

    def __init__(self, name=None, categories=None):
        self.name = name or "Listing"
        self.categories = categories or []

    @classmethod
    def from_elements(cls, elements, name=None):
        """Create listing from list of element dictionaries"""
        listing = cls(name=name)
        for element in elements:
            category = element.pop("category", None)
            listing.add_entry(BaseEntry(**element), category_name=category)
        return listing

    def __str__(self):
        """Format listing (incl. name and header)."""
        result = ["{1:^{0}}".format(CategoryEntry.TOTAL_LENGTH, self.name)]

        header_line = "{3:{0}} {4:{1}} {5:{2}}".format(
            CategoryEntry.NAME_LENGTH, BaseEntry.VALUE_LENGTH,
            BaseEntry.DATE_LENGTH,
            *[k.capitalize() for k in BaseEntry.ITEM_TYPES])
        if BaseEntry.SHOW_EID:
            header_line += " " + "ID".ljust(BaseEntry.EID_LENGTH)
        result.append(header_line)

        sort_key = lambda e: getattr(e, Listing.CATEGORY_ENTRY_SORT_KEY)
        for category in sorted(self.categories, key=sort_key):
            result.append(str(category))

        return '\n'.join(result)

    def add_entry(self, entry, category_name=None):
        """Add a Category- or BaseEntry to the listing.
        Category names are unique, i.e. a CategoryEntry is discarded if one
        with identical name (case INsensitive) already exists.
        When adding a BaseEntry, the parent CategoryEntry is created if it does
        not exist. If no category is specified, the BaseEntry is added to the
        default category.

        :raises: TypeError if neither CategoryEntry nor BaseEntry given
        """

        if isinstance(entry, CategoryEntry):
            if entry.name not in self.category_entry_names:
                self.categories.append(entry)
        elif isinstance(entry, BaseEntry):
            category_entry = self._get_category_entry(
                category_name or CategoryEntry.DEFAULT_NAME)
            category_entry.append(entry)
        else:
            raise TypeError("Invalid entry type: {}".format(entry))

    def category_fields(self, field_type):
        """Generator iterating over the field specified by `field_type` of the
        first-level children (CategoryEntries) of the listing.

        :param field_type: 'name' or 'value'

        raises: KeyError if `field_type` not found.
        yields: str or float
        """
        for category_entry in self.categories:
            yield getattr(category_entry, field_type)

    @property
    def category_entry_names(self):
        """Convenience generator method yielding category names."""
        for category_name in self.category_fields("name"):
            yield category_name

    def _get_category_entry(self, category_name):
        """Fetch CategoryEntry searching for given `category_name` or return a
        new instance that is automatically added to the Listing's categories.
        The search is case insensitive.

        :return: CategoryEntry
        """

        category_name = category_name.lower()
        for category_entry in self.categories:
            if category_entry.name == category_name:
                return category_entry
        else:
            # Nothing found in existing categories
            category_entry = CategoryEntry(name=category_name)
            self.add_entry(category_entry)
            return category_entry

    def total_value(self):
        """Return total value of the listing."""
        return sum(v for v in self.category_fields("value"))


def prettify(elements, stacked_layout=False):
    """Sort the given elements (type acc. to Period._search_all_tables) by
    positive and negative value and return pretty string build from the
    corresponding Listings.

    :param stacked_layout: If True, listings are displayed one by one
    """

    earnings = []
    expenses = []

    def _sort(eid, element):
        # Copying avoids modifying the original element. Flattening is in order
        # to distinguish recurrent entries (they have the same element ID which
        # thus can't be used as dict key)
        flat_element = element.copy()
        flat_element["eid"] = eid
        if flat_element["value"] > 0:
            earnings.append(flat_element)
        else:
            expenses.append(flat_element)

    # process standard elements
    for eid, element in elements[DEFAULT_TABLE].items():
        _sort(eid, element)

    # process recurrent elements, i.e. for each eid iterate list
    for eid, recurrent_elements in elements["recurrent"].items():
        for element in recurrent_elements:
            _sort(eid, element)

    if not earnings and not expenses:
        return ""

    listing_earnings = Listing.from_elements(earnings, name="Earnings")
    listing_expenses = Listing.from_elements(expenses, name="Expenses")

    if stacked_layout:
        return "{}\n\n{}\n\n{}".format(
            str(listing_earnings), CategoryEntry.TOTAL_LENGTH * "-",
            str(listing_expenses))
    else:
        result = []
        listings = [listing_earnings, listing_expenses]
        listings_str = [str(listing).splitlines() for listing in listings]
        for row in zip(*listings_str):
            result.append(" | ".join(row))
        earnings_size = len(listings_str[0])
        expenses_size = len(listings_str[1])
        diff = earnings_size - expenses_size
        if diff > 0:
            for row in listings_str[0][expenses_size:]:
                result.append(row + " | ")
        else:
            for row in listings_str[1][earnings_size:]:
                result.append(CategoryEntry.TOTAL_LENGTH * " " + " | " + row)
        # add 3 to take central separator " | " into account
        result.append((2 * CategoryEntry.TOTAL_LENGTH + 3) * "=")

        # add total value of earnings and expenses as final line
        total_values = []
        for listing in listings:
            total_entry = CategoryEntry(name="TOTAL")
            total_entry.value = listing.total_value()
            total_values.append(str(total_entry))
        result.append(" | ".join(total_values))

        return '\n'.join(result)
