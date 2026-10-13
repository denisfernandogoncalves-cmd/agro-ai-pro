from decimal import Decimal
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.cadpro.models import CADPro
from apps.financeiro.models import LancamentoFinanceiro
from apps.core.models import RegistroAlteracao
from .models import ContratoComercial,VinculoAcerto

class Entrada(serializers.Serializer):
    contrato=serializers.PrimaryKeyRelatedField(queryset=ContratoComercial.objects.all())
    cad_pro=serializers.PrimaryKeyRelatedField(queryset=CADPro.objects.filter(ativo=True))
    lancamento=serializers.PrimaryKeyRelatedField(queryset=LancamentoFinanceiro.objects.all())
    valor_vinculado=serializers.DecimalField(max_digits=14,decimal_places=2,min_value=Decimal("0.01"))
    natureza=serializers.ChoiceField(choices=("receita","frete","desconto","custo"))
    justificativa=serializers.CharField(max_length=2000,allow_blank=False)

def autorizar(user,escrita=False,acao="cadastrar"):
    if not pode(user,"vendas",acao if escrita else "consultar") or not pode(user,"financeiro","editar" if escrita else "consultar"):
        raise PermissionDenied("O acerto exige acesso a Vendas e Financeiro nas ações correspondentes.")

def dados_vinculo(v,distribuicoes=None):
    f=v.lancamento
    valid=v.ativo and f.status!="cancelado"
    recebido=None
    distributed = (distribuicoes or {}).get(f.pk)
    if distributed is None:
        distributed=VinculoAcerto.objects.filter(lancamento=f,ativo=True).aggregate(total=Sum("valor_vinculado"))["total"] or Decimal("0")
    inconsistent=distributed>f.valor
    if valid and not inconsistent and f.status=="liquidado" and f.valor_liquidado is not None:
        recebido=(v.valor_vinculado/f.valor*f.valor_liquidado).quantize(Decimal("0.01"))
    return {"id":v.pk,"contrato":v.contrato_id,"cad_pro":str(v.cad_pro_id),"codigo":v.cad_pro.codigo,"lancamento":f.pk,"descricao":f.descricao,"natureza":v.natureza,"valor_vinculado":str(v.valor_vinculado),"realizado_proporcional":str(recebido) if recebido is not None else None,"status":f.status,"ativo":v.ativo,"versao":v.versao,"usuario":v.usuario.get_username(),"valido":valid,"distribuicao_inconsistente":inconsistent}

class AcertoView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        autorizar(request.user)
        try:
            contrato=int(request.query_params.get("contrato",""));page=int(request.query_params.get("pagina",1))
            if page<1 or page>100000:raise ValueError()
        except (ValueError,TypeError):
            raise serializers.ValidationError("Informe contrato e página válidos.")
        get_object_or_404(ContratoComercial,pk=contrato)
        qs=VinculoAcerto.objects.filter(contrato_id=contrato).select_related("lancamento","cad_pro","usuario").order_by("id")
        cad=request.query_params.get("cad_pro")
        if cad:
            try:cad=CADPro._meta.pk.to_python(cad)
            except (DjangoValidationError,ValueError,TypeError):raise serializers.ValidationError("CAD/PRO inválido.")
            qs=qs.filter(cad_pro_id=cad)
        ids=qs.values_list("lancamento_id",flat=True).distinct()
        distribuicoes={r["lancamento_id"]:r["total"] for r in VinculoAcerto.objects.filter(lancamento_id__in=ids,ativo=True).values("lancamento_id").annotate(total=Sum("valor_vinculado"))}
        summary={"receitas_previstas":Decimal("0"),"custos_previstos":Decimal("0"),"recebido":Decimal("0"),"pago":Decimal("0"),"liquidacoes_sem_valor":0,"vinculos_inconsistentes":0}
        for v in qs.iterator(chunk_size=200):
            d=dados_vinculo(v,distribuicoes)
            if not d["valido"]:continue
            if d["distribuicao_inconsistente"]:summary["vinculos_inconsistentes"]+=1
            summary["receitas_previstas" if v.natureza=="receita" else "custos_previstos"]+=v.valor_vinculado
            if d["realizado_proporcional"] is not None:summary["recebido" if v.natureza=="receita" else "pago"]+=Decimal(d["realizado_proporcional"])
            elif v.lancamento.status=="liquidado" and not d["distribuicao_inconsistente"]:summary["liquidacoes_sem_valor"]+=1
        summary["resultado_previsto"]=summary["receitas_previstas"]-summary["custos_previstos"]
        summary["resultado_caixa"]=summary["recebido"]-summary["pago"]
        return Response({"count":qs.count(),"pagina":page,"results":[dados_vinculo(v,distribuicoes) for v in qs[(page-1)*25:page*25]],"resumo":{k:str(v) if isinstance(v,Decimal) else v for k,v in summary.items()},"gerado_em":timezone.now(),"base":"Somente vínculos manuais por ID. Realizado proporcional = valor vinculado / valor nominal do título × valor liquidado, arredondado a centavos. Sem valor liquidado não se presume pagamento. Fretes da conferência não são somados novamente; use o lançamento financeiro para compor o acerto. Custos não vinculados não estão incluídos."})
    def post(self,request):
        autorizar(request.user,True)
        ser=Entrada(data=request.data);ser.is_valid(raise_exception=True)
        d=dict(ser.validated_data)
        with transaction.atomic():
            f=LancamentoFinanceiro.objects.select_for_update().get(pk=d["lancamento"].pk)
            if f.status=="cancelado":raise serializers.ValidationError("Título cancelado não pode receber vínculo ativo.")
            if (d["natureza"]=="receita") != (f.tipo=="receber"):
                raise serializers.ValidationError("Receitas exigem conta a receber; despesas exigem conta a pagar.")
            old=VinculoAcerto.objects.filter(contrato=d["contrato"],cad_pro=d["cad_pro"],lancamento=f,natureza=d["natureza"]).first()
            if old:
                if old.ativo and old.valor_vinculado==d["valor_vinculado"]:return Response(dados_vinculo(old))
                return Response({"detail":"Vínculo já existe com dados diferentes; consulte o histórico."},status=409)
            allocated=VinculoAcerto.objects.filter(lancamento=f,ativo=True).aggregate(v=Sum("valor_vinculado"))["v"] or Decimal("0")
            if allocated+d["valor_vinculado"]>f.valor:raise serializers.ValidationError("A soma dos vínculos excede o valor nominal do título.")
            v=VinculoAcerto.objects.create(**d,usuario=request.user)
            result=dados_vinculo(v)
            RegistroAlteracao.objects.create(usuario=request.user,usuario_nome=request.user.get_username(),modulo="vendas",entidade="VinculoAcerto",registro_id=str(v.pk),acao="cadastrar",alteracoes={"depois":result,"justificativa":d["justificativa"]})
            return Response(result,status=201)

    def patch(self,request,pk=None):
        autorizar(request.user,True,"editar")
        class Alteracao(serializers.Serializer):
            ativo=serializers.BooleanField()
            versao=serializers.IntegerField(min_value=1)
            justificativa=serializers.CharField(max_length=2000,allow_blank=False)
        ser=Alteracao(data=request.data);ser.is_valid(raise_exception=True)
        base=get_object_or_404(VinculoAcerto,pk=pk)
        with transaction.atomic():
            f=LancamentoFinanceiro.objects.select_for_update().get(pk=base.lancamento_id)
            v=VinculoAcerto.objects.select_for_update().select_related("lancamento","cad_pro","usuario").get(pk=pk)
            d=ser.validated_data
            if v.versao!=d["versao"]:return Response({"detail":"Vínculo alterado. Recarregue."},status=409)
            if d["ativo"]:
                total=VinculoAcerto.objects.filter(lancamento=f,ativo=True).exclude(pk=v.pk).aggregate(v=Sum("valor_vinculado"))["v"] or Decimal("0")
                if f.status=="cancelado" or total+v.valor_vinculado>f.valor:raise serializers.ValidationError("Título cancelado ou valor já distribuído impede reativação.")
            before=dados_vinculo(v)
            v.ativo=d["ativo"];v.versao+=1;v.usuario=request.user;v.justificativa=d["justificativa"];v.save(update_fields=["ativo","versao","usuario","justificativa"])
            after=dados_vinculo(v)
            RegistroAlteracao.objects.create(usuario=request.user,usuario_nome=request.user.get_username(),modulo="vendas",entidade="VinculoAcerto",registro_id=str(v.pk),acao="editar",alteracoes={"antes":before,"depois":after,"justificativa":d["justificativa"]})
            return Response(after)
