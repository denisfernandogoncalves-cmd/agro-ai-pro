"""Recebimentos e retiradas independentes da produção própria."""
import hashlib
import json
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404

from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from apps.cadpro.models import CADPro, CADProPropriedade
from apps.propriedades.models import Propriedade
from .models import ArmazemGraos, EntradaProducaoTerceiro, MovimentoProducaoTerceiro, LoteGraos, MovimentacaoGraos, normalizar_placa, TerceiroCadastro
from .services import SaldoGraosError, _bloquear_cadpros_para_saldo, registrar_ajuste, estornar_movimentacao


from .cargas_services import calcular_peso_liquido, CargaColhidaError


class CalculoSerializer(serializers.Serializer):
    peso_total_kg = serializers.DecimalField(max_digits=16, decimal_places=3, required=False, allow_null=True)
    tara_kg = serializers.DecimalField(max_digits=16, decimal_places=3, required=False, allow_null=True)
    cultura = serializers.CharField()
    peso_bruto_kg = serializers.DecimalField(max_digits=16, decimal_places=3, min_value=Decimal("0.001"))
    umidade_percentual = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100)
    impureza_percentual = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100)
    defeitos_percentual = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100)
    ph = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100, required=False, allow_null=True)
    tolerancia_impureza_percentual = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100, required=False)
    desconto_impureza_por_ponto = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100, required=False)
    tolerancia_defeitos_percentual = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100, required=False)
    desconto_defeitos_por_ponto = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100, required=False)
    ph_minimo = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100, required=False)
    desconto_ph_por_ponto = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=0, max_value=100, required=False)

    def validate(self, dados):
        from .pesagem import peso_produto
        try:
            dados["peso_bruto_kg"] = peso_produto(dados["peso_bruto_kg"], dados.get("peso_total_kg"), dados.get("tara_kg"))
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        if dados["cultura"].lower() != "trigo":
            dados.update(ph=None, ph_minimo=Decimal("0"), desconto_ph_por_ponto=Decimal("0"))
        try:
            percentual, desconto, liquido, sacas, regra = calcular_peso_liquido(**{k:v for k,v in dados.items() if k not in ("peso_total_kg", "tara_kg")})
        except CargaColhidaError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return {**dados, "peso_liquido_kg": liquido, "desconto_total_percentual": percentual, "desconto_total_kg": desconto, "regra_desconto_aplicada": regra}


class EntradaSerializer(serializers.ModelSerializer):
    depositante = serializers.CharField(max_length=160,required=False)
    terceiro = serializers.PrimaryKeyRelatedField(queryset=TerceiroCadastro.objects.all(),required=False,allow_null=True)
    terceiro_codigo = serializers.CharField(source="terceiro.codigo",read_only=True,default="")
    armazem_nome = serializers.CharField(source="armazem.nome", read_only=True)
    criado_por_nome = serializers.CharField(source="criado_por.username", read_only=True)
    movimentos = serializers.SerializerMethodField()

    class Meta:
        model = EntradaProducaoTerceiro
        fields = ("id", "versao", "terceiro", "terceiro_codigo", "depositante", "propriedade_origem", "cad_pro", "cultura", "safra", "armazem", "armazem_nome", "peso_liquido_kg", "saldo_kg", "data_entrada", "placa", "motorista", "documento", "observacoes", "criado_em", "criado_por_nome", "movimentos", "peso_total_kg", "tara_kg", "peso_bruto_kg", "umidade_percentual", "impureza_percentual", "defeitos_percentual", "ph", "desconto_total_percentual", "desconto_total_kg", "regra_desconto_aplicada")
        read_only_fields = ("versao", "saldo_kg", "criado_em", "peso_liquido_kg", "desconto_total_percentual", "desconto_total_kg", "regra_desconto_aplicada", "propriedade_origem", "cad_pro")

    def validate(self, dados):
        terceiro=dados.get("terceiro",self.instance.terceiro if self.instance else None)
        if terceiro:
            if not terceiro.ativo and (not self.instance or self.instance.terceiro_id!=terceiro.pk):
                raise serializers.ValidationError("O cadastro do terceiro está inativo.")
            if "terceiro" in dados or not self.instance:
                dados["depositante"]=terceiro.nome
        if not terceiro and not dados.get('depositante',self.instance.depositante if self.instance else ''):
            raise serializers.ValidationError({'depositante':'Informe o nome ou selecione o cadastro do terceiro.'})
        dados_calculo = {k: self.initial_data[k] for k in CalculoSerializer().fields if k in self.initial_data}
        if self.instance:
            parcelas = self.instance.regra_desconto_aplicada.get("parcelas", {})
            for campo, parcela, chave in (("tolerancia_impureza_percentual","impureza","tolerancia_percentual"),("desconto_impureza_por_ponto","impureza","desconto_por_ponto"),("tolerancia_defeitos_percentual","defeitos","tolerancia_percentual"),("desconto_defeitos_por_ponto","defeitos","desconto_por_ponto"),("ph_minimo","ph","minimo"),("desconto_ph_por_ponto","ph","desconto_por_ponto")):
                if campo not in dados_calculo and parcelas.get(parcela, {}).get(chave) is not None:
                    dados_calculo[campo] = parcelas[parcela][chave]
        calculo = CalculoSerializer(data=dados_calculo)
        calculo.is_valid(raise_exception=True)
        calculados = calculo.validated_data
        campos = {f.name for f in EntradaProducaoTerceiro._meta.fields}
        resultado = {**dados, **{k: v for k, v in calculados.items() if k in campos}}
        if resultado.get("cultura", "").lower() != "trigo":
            resultado["ph"] = None
        return resultado

    def validate_peso_liquido_kg(self, valor):
        if valor <= 0:
            raise serializers.ValidationError("Informe peso líquido maior que zero.")
        return valor

    def validate_placa(self, valor):
        return normalizar_placa(valor)

    def get_movimentos(self, obj):
        return MovimentoSerializer(obj.movimentos.all(), many=True).data


class EdicaoEntradaSerializer(EntradaSerializer):
    versao = serializers.IntegerField(min_value=1)
    motivo = serializers.CharField(max_length=500)

    class Meta(EntradaSerializer.Meta):
        fields = EntradaSerializer.Meta.fields + ("motivo",)
        read_only_fields = tuple(c for c in EntradaSerializer.Meta.read_only_fields if c != "versao")


class MovimentoSerializer(serializers.ModelSerializer):
    criado_por_nome = serializers.CharField(source="criado_por.username", read_only=True)
    estornado = serializers.SerializerMethodField()

    class Meta:
        model = MovimentoProducaoTerceiro
        exclude = ("hash_requisicao", "chave_idempotencia")

    def get_estornado(self, obj):
        return hasattr(obj, "estorno")


class SaidaSerializer(serializers.Serializer):
    quantidade_kg = serializers.DecimalField(max_digits=16, decimal_places=3, min_value=Decimal("0.001"))
    data_movimento = serializers.DateField()
    destino = serializers.CharField(max_length=160)
    documento = serializers.CharField(max_length=120, required=False, allow_blank=True)
    placa = serializers.CharField(max_length=7, required=False, allow_blank=True)
    motorista = serializers.CharField(max_length=120, required=False, allow_blank=True)
    observacoes = serializers.CharField(max_length=4000, required=False, allow_blank=True)


class EstornoSerializer(serializers.Serializer):
    versao = serializers.IntegerField(min_value=1, required=False)
    motivo = serializers.CharField(max_length=500)
    data_movimento = serializers.DateField()


class TransferenciaSerializer(serializers.Serializer):
    versao = serializers.IntegerField(min_value=1)
    propriedade = serializers.PrimaryKeyRelatedField(queryset=Propriedade.objects.all())
    cad_pro = serializers.PrimaryKeyRelatedField(queryset=CADPro.objects.filter(ativo=True))
    quantidade_kg = serializers.DecimalField(max_digits=16, decimal_places=3, min_value=Decimal("0.001"))
    data_movimento = serializers.DateField()
    documento = serializers.CharField(max_length=120, required=False, allow_blank=True)
    observacoes = serializers.CharField(max_length=4000, required=False, allow_blank=True)

    def validate(self, dados):
        if not CADProPropriedade.objects.filter(propriedade=dados["propriedade"], cad_pro=dados["cad_pro"], ativo=True).exists():
            raise serializers.ValidationError("Selecione um CAD/PRO com vínculo ativo na propriedade de destino.")
        return dados


def executar_terceiro(*, usuario, tipo, dados, chave, pk=None, request=None):
    if not chave or len(chave) > 160:
        raise serializers.ValidationError("Informe a chave de reenvio do lançamento.")
    # Valores normalizados identificam a intenção; uma chave não pode mudar dados/usuário.
    resumo = {k: v.pk if hasattr(v, "pk") else str(v) for k, v in dados.items()}
    digest = hashlib.sha256(json.dumps([tipo, pk, resumo], sort_keys=True, default=str).encode()).hexdigest()

    def repetido():
        movimento = MovimentoProducaoTerceiro.objects.filter(chave_idempotencia=chave).first()
        if movimento and (movimento.hash_requisicao != digest or movimento.criado_por_id != usuario.pk):
            raise serializers.ValidationError("Esta chave já foi usada em outro lançamento.")
        return movimento

    anterior = repetido()
    if anterior:
        return anterior.entrada, True
    if tipo == "entrada":
        armazem_id = dados["armazem"].pk
    elif tipo in ("saida", "edicao", "transferencia"):
        armazem_id = get_object_or_404(EntradaProducaoTerceiro, pk=pk).armazem_id
    else:
        armazem_id = get_object_or_404(MovimentoProducaoTerceiro, pk=pk).entrada.armazem_id
    try:
        with transaction.atomic():
            # Mesma ordem do ledger: CAD/PRO, armazém, entrada, posição.
            if tipo == "transferencia":
                _bloquear_cadpros_para_saldo((dados["cad_pro"].pk,))
            elif tipo == "estorno":
                referencia = get_object_or_404(MovimentoProducaoTerceiro, pk=pk)
                if referencia.movimentacao_saldo_id:
                    _bloquear_cadpros_para_saldo((referencia.movimentacao_saldo.posicao.cad_pro_id,))
            armazem = ArmazemGraos.objects.select_for_update().get(pk=armazem_id)
            anterior = repetido()
            if anterior:
                return anterior.entrada, True
            if not armazem.ativo:
                raise serializers.ValidationError("O armazém está inativo.")
            from .fechamentos import verificar_periodo
            from types import SimpleNamespace
            if tipo == 'entrada':
                contexto=SimpleNamespace(armazem=armazem,cultura=dados['cultura'],safra=dados['safra'],data_entrada=dados.get('data_entrada',timezone.localdate()))
            elif tipo == 'estorno':
                contexto=get_object_or_404(MovimentoProducaoTerceiro,pk=pk).entrada
            else:
                contexto=get_object_or_404(EntradaProducaoTerceiro,pk=pk)
            verificar_periodo(request,contexto,dados.get('data_movimento'),dados if tipo=='edicao' else None)
            if tipo=='estorno':
                referencia=get_object_or_404(MovimentoProducaoTerceiro,pk=pk)
                snap=referencia.snapshot_depois
                verificar_periodo(request,SimpleNamespace(armazem=armazem,cultura=snap.get('cultura',contexto.cultura),safra=snap.get('safra',contexto.safra),data_entrada=referencia.data_movimento),dados.get('data_movimento'))
            if tipo == "entrada":
                entrada = EntradaProducaoTerceiro(**dados, criado_por=usuario, saldo_kg=0)
                delta = dados["peso_liquido_kg"]
                movimento_dados = {"data_movimento": entrada.data_entrada, "documento": entrada.documento, "placa": entrada.placa, "motorista": entrada.motorista, "observacoes": entrada.observacoes}
            else:
                original = get_object_or_404(MovimentoProducaoTerceiro, pk=pk) if tipo == "estorno" else None
                entrada_id = original.entrada_id if original else pk
                entrada = EntradaProducaoTerceiro.objects.select_for_update().get(pk=entrada_id)
                if tipo == "edicao":
                    if entrada.versao != dados["versao"]:
                        raise serializers.ValidationError("Esta entrada mudou. Atualize a consulta antes de editar.")
                    if entrada.movimentos.filter(tipo="entrada", estorno__isnull=False).exists():
                        raise serializers.ValidationError("Esta entrada foi excluída; consulte o histórico.")
                    if dados["armazem"].pk != entrada.armazem_id:
                        raise serializers.ValidationError("Para mudar o armazém, exclua a entrada e registre novamente.")
                    retirado = entrada.peso_liquido_kg - entrada.saldo_kg
                    if dados["peso_liquido_kg"] < retirado:
                        raise serializers.ValidationError("O novo peso líquido não pode ser menor que a quantidade já retirada.")
                    if retirado > 0 and (dados["cultura"] != entrada.cultura or dados["safra"] != entrada.safra):
                        raise serializers.ValidationError("Estorne as retiradas antes de alterar cultura ou safra.")
                    snapshot_antes = json.loads(json.dumps({k:v for k,v in EntradaSerializer(entrada).data.items() if k != "movimentos"}, default=str))
                    delta = dados["peso_liquido_kg"] - entrada.peso_liquido_kg
                    for campo, valor in dados.items():
                        if campo not in ("versao", "motivo"):
                            setattr(entrada, campo, valor)
                    movimento_dados = {"data_movimento": entrada.data_entrada, "observacoes": dados["motivo"], "snapshot_antes": snapshot_antes}
                elif tipo in ("saida", "transferencia"):
                    if entrada.movimentos.filter(tipo="entrada", estorno__isnull=False).exists():
                        raise serializers.ValidationError("Esta entrada foi estornada.")
                    delta = -dados["quantidade_kg"]
                    if tipo == "transferencia":
                        if entrada.versao != dados["versao"]:
                            raise serializers.ValidationError("Esta entrada mudou. Atualize antes de transferir.")
                        cad = CADPro.objects.get(pk=dados["cad_pro"].pk)
                        if not cad.ativo or not CADProPropriedade.objects.filter(cad_pro=cad, propriedade=dados["propriedade"], ativo=True).exists():
                            raise serializers.ValidationError("O CAD/PRO de destino deve estar ativo e vinculado à propriedade.")
                        movimento_dados = {k: v for k, v in dados.items() if k in ("data_movimento", "documento", "observacoes")}
                        movimento_dados["destino"] = f"{dados['propriedade'].nome} / CAD/PRO {cad.codigo}"[:160]
                    else:
                        movimento_dados = {k: v for k, v in dados.items() if k != "quantidade_kg"}
                else:
                    if original.tipo in ("estorno", "edicao") or hasattr(original, "estorno"):
                        raise serializers.ValidationError("Este movimento já foi estornado ou é um estorno.")
                    if original.tipo == "entrada" and "versao" in dados and entrada.versao != dados["versao"]:
                        raise serializers.ValidationError("Esta entrada mudou. Atualize antes de excluir.")
                    delta = -entrada.peso_liquido_kg if original.tipo == "entrada" else -original.delta_kg
                    movimento_dados = {"data_movimento": dados["data_movimento"], "observacoes": dados["motivo"], "estorno_de": original}
                    if original.movimentacao_saldo_id:
                        if not pode(usuario, "transferencias", "excluir"):
                            raise PermissionDenied("Sem permissão para estornar transferências.")
                        resultado = estornar_movimentacao(usuario=usuario, movimentacao=original.movimentacao_saldo,
                            chave_idempotencia=f"terceiro-estorno:{hashlib.sha256(chave.encode()).hexdigest()}",
                            data_movimento=dados["data_movimento"], observacoes=dados["motivo"], permitir_terceiro=True)
                        movimento_dados["movimentacao_saldo"] = MovimentacaoGraos.objects.get(pk=resultado.movimentacoes[0].id)
                        movimento_dados["destino"] = original.destino
            saldo_anterior = entrada.saldo_kg
            saldo_novo = saldo_anterior + delta
            if saldo_novo < 0 or saldo_novo > entrada.peso_liquido_kg:
                raise serializers.ValidationError("Saldo de terceiros insuficiente. Confira as retiradas e seus estornos.")
            if delta > 0:
                from .services import _ocupacao_armazem_bloqueada
                if _ocupacao_armazem_bloqueada(armazem.pk) + delta > armazem.capacidade_kg:
                    raise serializers.ValidationError("Capacidade do armazém insuficiente para esta entrada.")
            entrada.saldo_kg = saldo_novo
            if tipo != "entrada":
                entrada.versao += 1
            entrada.save()
            if tipo == "transferencia":
                # Reclassifica a titularidade do líquido no mesmo silo; não gera produção.
                produto = hashlib.sha256(f"{entrada.cultura}:{entrada.safra}".encode()).hexdigest()[:12]
                codigo = f"TERCEIRO-{entrada.pk}-{dados['propriedade'].pk}-{dados['cad_pro'].pk}-{produto}"
                lote, _ = LoteGraos.objects.get_or_create(armazem=armazem, codigo=codigo,
                    defaults={"propriedade": dados["propriedade"], "cad_pro": dados["cad_pro"], "cultura": entrada.cultura, "safra": entrada.safra})
                if (lote.propriedade_id, lote.cad_pro_id, lote.cultura, lote.safra) != (dados["propriedade"].pk, dados["cad_pro"].pk, entrada.cultura, entrada.safra):
                    raise serializers.ValidationError("O lote de destino mudou. Confira seu cadastro antes de transferir.")
                resultado = registrar_ajuste(usuario=usuario, lote=lote, delta_fisico_kg=-delta,
                    chave_idempotencia=f"terceiro-transferencia:{hashlib.sha256(chave.encode()).hexdigest()}",
                    data_movimento=dados["data_movimento"], referencia_externa=dados.get("documento", ""),
                    observacoes=dados.get("observacoes", ""), metadados={"entrada_terceiro_id": entrada.pk, "depositante": entrada.depositante, "tipo": "transferencia_terceiro"})
                movimento_dados["movimentacao_saldo"] = MovimentacaoGraos.objects.get(pk=resultado.movimentacoes[0].id)
            if tipo == "edicao":
                movimento_dados["snapshot_depois"] = json.loads(json.dumps({k:v for k,v in EntradaSerializer(entrada).data.items() if k != "movimentos"}, default=str))
            else:
                movimento_dados['snapshot_depois']=json.loads(json.dumps({k:v for k,v in EntradaSerializer(entrada).data.items() if k != 'movimentos'},default=str))
            MovimentoProducaoTerceiro.objects.create(entrada=entrada, tipo=tipo, quantidade_kg=entrada.peso_liquido_kg if tipo == "edicao" else abs(delta), delta_kg=delta, saldo_anterior_kg=saldo_anterior, saldo_posterior_kg=saldo_novo, chave_idempotencia=chave, hash_requisicao=digest, criado_por=usuario, **movimento_dados)
            return entrada, False
    except SaldoGraosError as exc:
        raise serializers.ValidationError(str(exc)) from exc
    except IntegrityError:
        anterior = repetido()
        if anterior:
            return anterior.entrada, True
        raise serializers.ValidationError("Não foi possível registrar. Atualize e confira o lançamento.")


class TerceirosView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)
    tipo = "entrada"

    def verificar(self, request, acao):
        if not pode(request.user, "cargas", acao):
            raise PermissionDenied("Sem permissão para produção de terceiros.")

    def get(self, request, pk=None):
        if self.tipo in ("pdf", "excel"):
            self.verificar(request, "imprimir")
            from .romaneios_terceiros import gerar_pdf, gerar_excel
            entrada = get_object_or_404(EntradaProducaoTerceiro.objects.select_related("armazem"), pk=pk)
            try:
                conteudo = gerar_pdf(entrada) if self.tipo == "pdf" else gerar_excel(entrada)
            except ValueError as exc:
                raise serializers.ValidationError(str(exc)) from exc
            extensao = "pdf" if self.tipo == "pdf" else "xlsx"
            resposta = HttpResponse(conteudo, content_type="application/pdf" if self.tipo == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            resposta["Content-Disposition"] = f'attachment; filename="romaneio-terceiro-{pk}.{extensao}"'
            return resposta
        self.verificar(request, "consultar")
        if self.tipo != "entrada":
            return Response(status=405)
        itens = EntradaProducaoTerceiro.objects.select_related("armazem", "criado_por", "terceiro").prefetch_related("movimentos__criado_por", "movimentos__estorno")
        from django.db.models import Q
        situacao = request.query_params.get('situacao', '')
        if situacao not in ('', 'ativos', 'cancelados', 'esgotados'):
            raise serializers.ValidationError('Situação inválida.')
        cancelados = MovimentoProducaoTerceiro.objects.filter(tipo='entrada', estorno__isnull=False).values('entrada_id')
        if situacao == 'cancelados':
            itens = itens.filter(pk__in=cancelados)
        elif situacao in ('ativos', 'esgotados'):
            itens = itens.exclude(pk__in=cancelados)
            if situacao == 'esgotados':
                itens = itens.filter(saldo_kg=0)
        busca = request.query_params.get('busca', '').strip()[:160]
        if busca:
            filtro = Q(depositante__icontains=busca)|Q(terceiro__codigo__icontains=busca)|Q(cultura__icontains=busca)|Q(safra__icontains=busca)|Q(armazem__nome__icontains=busca)|Q(placa__icontains=busca)|Q(documento__icontains=busca)
            if busca.isdigit(): filtro |= Q(pk=int(busca))
            itens = itens.filter(filtro)
        if request.query_params.get('sem_vinculo') == 'true':
            itens = itens.filter(terceiro__isnull=True)
        if request.query_params.get("pagina"):
            p=serializers.IntegerField(min_value=1,max_value=1000000).run_validation(request.query_params["pagina"])
            return Response({"total":itens.count(),"itens":EntradaSerializer(itens.order_by("-data_entrada","-id")[(p-1)*25:p*25],many=True).data})
        return Response(EntradaSerializer(itens, many=True).data)

    def post(self, request, pk=None):
        if self.tipo in ("pdf", "excel"):
            return Response(status=405)
        if self.tipo == "previa":
            self.verificar(request, "consultar")
            calculo = CalculoSerializer(data=request.data)
            calculo.is_valid(raise_exception=True)
            return Response(calculo.validated_data)
        self.verificar(request, "excluir" if self.tipo == "estorno" else "cadastrar")
        if self.tipo == "transferencia" and not pode(request.user, "transferencias", "cadastrar"):
            raise PermissionDenied("Sem permissão para transferir saldo para CAD/PRO.")
        if self.tipo == "estorno":
            original = get_object_or_404(MovimentoProducaoTerceiro, pk=pk)
            if original.movimentacao_saldo_id and not pode(request.user, "transferencias", "excluir"):
                raise PermissionDenied("Sem permissão para estornar transferências.")
        classe = {"entrada": EntradaSerializer, "saida": SaidaSerializer, "estorno": EstornoSerializer, "transferencia": TransferenciaSerializer}[self.tipo]
        serializer = classe(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            entrada, repetida = executar_terceiro(request=request, usuario=request.user, tipo=self.tipo, dados=serializer.validated_data, chave=request.headers.get("Idempotency-Key", ""), pk=pk)
            if not repetida and self.tipo == "entrada":
                from .pendencias import pendencias_pesagem
                pendencias_pesagem(entrada,request.user,terceiro=True)
        return Response(EntradaSerializer(entrada).data, status=200 if repetida else 201)


    @transaction.atomic
    def patch(self, request, pk=None):
        if self.tipo != "entrada" or pk is None:
            return Response(status=405)
        self.verificar(request, "editar")
        entrada = get_object_or_404(EntradaProducaoTerceiro, pk=pk)
        serializer = EdicaoEntradaSerializer(instance=entrada, data=request.data)
        serializer.is_valid(raise_exception=True)
        salvo, _ = executar_terceiro(request=request, usuario=request.user, tipo="edicao", dados=serializer.validated_data, chave=request.headers.get("Idempotency-Key", ""), pk=pk)
        from .pendencias import pendencias_pesagem
        pendencias_pesagem(salvo,request.user,terceiro=True)
        return Response(EntradaSerializer(salvo).data)

    def delete(self, request, pk=None):
        if self.tipo != "entrada" or pk is None:
            return Response(status=405)
        self.verificar(request, "excluir")
        entrada = get_object_or_404(EntradaProducaoTerceiro, pk=pk)
        original = get_object_or_404(MovimentoProducaoTerceiro, entrada=entrada, tipo="entrada")
        serializer = EstornoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        salvo, _ = executar_terceiro(request=request, usuario=request.user, tipo="estorno", dados=serializer.validated_data, chave=request.headers.get("Idempotency-Key", ""), pk=original.pk)
        return Response(EntradaSerializer(salvo).data)
