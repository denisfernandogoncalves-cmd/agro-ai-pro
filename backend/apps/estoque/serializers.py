from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    LocalEstoque,
    LoteEstoque,
    MovimentacaoEstoque,
    ProdutoEstoque,
)
from .services import EstoqueInsuficienteError, registrar_movimentacao, saldo_lote


class ProdutoEstoqueSerializer(serializers.ModelSerializer):
    def validate_unidade(self, value):
        if self.instance and value != self.instance.unidade and self.instance.faturamentoinsumo_set.exists():
            raise serializers.ValidationError("A unidade de produto com faturamento confirmado não pode ser alterada.")
        return value

    class Meta:
        model = ProdutoEstoque
        fields = "__all__"
        read_only_fields = ("criado_em",)
        extra_kwargs = {
            "fabricante": {
                "required": False,
                "allow_blank": True,
                "default": "",
            }
        }


class LocalEstoqueSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(
        source="propriedade.nome", read_only=True
    )

    class Meta:
        model = LocalEstoque
        fields = "__all__"
        read_only_fields = ("criado_em",)


class LoteEstoqueSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source="produto.nome", read_only=True)
    produto_unidade = serializers.CharField(source="produto.unidade", read_only=True)
    local_nome = serializers.CharField(source="local.nome", read_only=True, default="")
    fornecedor_nome = serializers.CharField(source="fornecedor.nome", read_only=True, default="")
    saldo = serializers.SerializerMethodField()
    vencido = serializers.BooleanField(read_only=True)

    class Meta:
        model = LoteEstoque
        fields = "__all__"
        read_only_fields = ("criado_em",)

    def get_saldo(self, obj):
        return saldo_lote(obj)

    def validate(self, attrs):
        if self.instance and self.instance.movimentacoes.filter(baixa_faturamento__isnull=False).exists():
            for campo in ("produto", "fornecedor", "local"):
                if campo in attrs and attrs[campo] != getattr(self.instance, campo):
                    raise serializers.ValidationError({campo: "Este lote possui faturamento confirmado e não pode mudar de produto, empresa ou local."})
        fornecedor = attrs.get("fornecedor", getattr(self.instance, "fornecedor", None))
        local = attrs.get("local", getattr(self.instance, "local", None))
        produto = attrs.get("produto", getattr(self.instance, "produto", None))
        codigo = attrs.get("codigo", getattr(self.instance, "codigo", ""))
        if not local and not fornecedor:
            raise serializers.ValidationError({"fornecedor": "Selecione um fornecedor cadastrado."})
        if fornecedor and (not self.instance or "fornecedor" in attrs):
            if not fornecedor.ativo or fornecedor.tipo not in {"fornecedor", "ambos"}:
                raise serializers.ValidationError({"fornecedor": "Selecione um fornecedor ativo."})
        if produto and (not self.instance or "produto" in attrs) and not produto.ativo:
            raise serializers.ValidationError({"produto": "Selecione um produto agrícola ativo."})
        if not local and fornecedor:
            duplicados = LoteEstoque.objects.filter(produto=produto, fornecedor=fornecedor, codigo=codigo, local__isnull=True)
            if self.instance:
                duplicados = duplicados.exclude(pk=self.instance.pk)
            if duplicados.exists():
                raise serializers.ValidationError({"codigo": "Já existe este lote para o produto e fornecedor."})
        return attrs


class MovimentacaoEstoqueSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source="lote.produto.nome", read_only=True)
    unidade = serializers.CharField(source="lote.produto.unidade", read_only=True)
    lote_codigo = serializers.CharField(source="lote.codigo", read_only=True)
    local_nome = serializers.CharField(source="lote.local.nome", read_only=True, default="")
    fornecedor_nome = serializers.CharField(source="lote.fornecedor.nome", read_only=True, default="")
    propriedade_nome = serializers.CharField(
        source="propriedade.nome", read_only=True
    )
    criado_por_nome = serializers.CharField(
        source="criado_por.username", read_only=True
    )

    class Meta:
        model = MovimentacaoEstoque
        fields = "__all__"
        read_only_fields = ("criado_por", "criado_em")

    def create(self, validated_data):
        try:
            return registrar_movimentacao(
                usuario=self.context["request"].user,
                **validated_data,
            )
        except (ValueError, EstoqueInsuficienteError, DjangoValidationError) as exc:
            if isinstance(exc, DjangoValidationError):
                detalhe = exc.message_dict
            else:
                detalhe = {"detail": str(exc)}
            raise serializers.ValidationError(detalhe) from exc
