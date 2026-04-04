from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsPagination(PageNumberPagination):
    """
    Consistent pagination envelope across all list endpoints.
    Response shape:
    {
        "count": 1000,
        "next": "http://...",
        "previous": null,
        "page": 2,
        "page_size": 50,
        "total_pages": 20,
        "results": [...]
    }
    """
    page_size             = 50
    page_size_query_param = "page_size"
    max_page_size         = 500

    def get_paginated_response(self, data):
        return Response({
            "count":       self.page.paginator.count,
            "next":        self.get_next_link(),
            "previous":    self.get_previous_link(),
            "page":        self.page.number,
            "page_size":   self.get_page_size(self.request),
            "total_pages": self.page.paginator.num_pages,
            "results":     data,
        })