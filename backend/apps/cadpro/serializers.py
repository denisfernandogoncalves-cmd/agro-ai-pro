from rest_framework import serializers

from apps.propriedades.models import Propriedade

from .models import CADPro, CADProPropriedade, normalizar_codigo_cadpro


class CADProSerializer(serializers.ModelSerializer):
    class Meta:
        model = CADPro
        fields = (
            "id",
            "codigo",
            "codigo_normalizado",
            "descricao",
            "ativo",
            "criado_em",
            "atualizado_em",
        )
        read_only_fields = (
            "id",
            "codigo_normalizado",
            "ativo",
            "criado_em",
            "atualizado_em",
        )

    def validate_codigo(self, value):
        normalizado = normalizar_codigo_cadpro(value)
        if not normalizado:
            raise serializers.ValidationError(
                "Informe um código CAD/PRO com letras ou números."
            )
        duplicados = CADPro.objects.filter(codigo_normalizado=normalizado)
        if self.instance:
            duplicados = duplicados.exclude(pk=self.instance.pk)
        if duplicados.exists():
            raise serializers.ValidationError(
                "Já existe um CAD/PRO com este código."
            )
        return " ".join(value.strip().split())

    def validate_descricao(self, value):
        descricao = " ".join(value.strip().split())
        if not descricao:
            raise serializers.ValidationError("Informe a descrição do CAD/PRO.")
        return descricao


class CADProPropriedadeSerializer(serializers.ModelSerializer):
    propriedade = serializers.PrimaryKeyRelatedField(
        queryset=Propriedade.objects.all(),
    )
    propriedade_nome = serializers.CharField(
        source="propriedade.nome",
        read_only=True,
    )

    class Meta:
        model = CADProPropriedade
        fields = (
            "id",
            "cad_pro",
            "propriedade",
            "propriedade_nome",
            "ativo",
            "criado_em",
            "atualizado_em",
        )
        read_only_fields = (
            "id",
            "cad_pro",
            "ativo",
            "criado_em",
            "atualizado_em",
        )

    def validate(self, attrs):
        cad_pro = self.context["cad_pro"]
        if not cad_pro.ativo:
            raise serializers.ValidationError(
                {"cad_pro": "Não é possível vincular uma propriedade a um CAD/PRO inativo."}
            )
        propriedade = attrs["propriedade"]
        if CADProPropriedade.objects.filter(
            cad_pro=cad_pro,
            propriedade=propriedade,
        ).exists():
            raise serializers.ValidationError(
                {"propriedade": "Esta propriedade já está vinculada ao CAD/PRO."}
            )
        return attrs

    def create(self, validated_data):
        return CADProPropriedade.objects.create(
            cad_pro=self.context["cad_pro"],
            **validated_data,
        )
