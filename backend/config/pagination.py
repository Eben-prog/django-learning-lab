from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """?page=2&page_size=25 -> {"count", "next", "previous", "results"}"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100  # protects the database from ?page_size=1000000
