from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError


class PaginacaoOpcional(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200

    def paginate_queryset(self, queryset, request, view=None):
        if "page" not in request.query_params and "page_size" not in request.query_params:
            return None
        for campo in ("page", "page_size"):
            valor = request.query_params.get(campo)
            if valor is not None and (not str(valor).isdecimal() or int(valor) < 1):
                raise ValidationError({campo: "Informe um inteiro positivo."})
        return super().paginate_queryset(queryset, request, view)
