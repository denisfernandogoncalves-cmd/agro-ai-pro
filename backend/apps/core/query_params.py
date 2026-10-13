from rest_framework import serializers


class FiltrosPropriedadeSafraSerializer(serializers.Serializer):
    propriedade = serializers.IntegerField(required=False, min_value=1)
    safra = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate_safra(self, value):
        return value.strip()


def obter_filtros_propriedade_safra(query_params):
    dados = {"safra": query_params.get("safra", "").strip()}
    propriedade = query_params.get("propriedade", "").strip()
    if propriedade:
        dados["propriedade"] = propriedade

    serializer = FiltrosPropriedadeSafraSerializer(data=dados)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def validar_filtros(query_params, *, ids=(), datas=()):
    """Valida filtros sem mudar o formato público das consultas existentes."""
    campos = {nome: serializers.IntegerField(min_value=1) for nome in ids}
    campos.update({nome: serializers.DateField(input_formats=["%Y-%m-%d"]) for nome in datas})
    dados = {}
    for nome, campo in campos.items():
        valor = query_params.get(nome, "")
        if valor not in (None, ""):
            try:
                dados[nome] = campo.run_validation(valor)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({nome: exc.detail}) from exc
    for inicio, fim in (("data_inicio", "data_fim"), ("vencimento_inicio", "vencimento_fim"), ("liquidacao_inicio", "liquidacao_fim")):
        if inicio in dados and fim in dados and dados[inicio] > dados[fim]:
            raise serializers.ValidationError({fim: "A data final deve ser igual ou posterior à inicial."})
    return dados
