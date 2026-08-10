import hashlib
from decimal import Decimal

from django.db import migrations


def normalizar(apps, schema_editor):
    Lote = apps.get_model("graos", "LoteGraos")
    Movimento = apps.get_model("graos", "MovimentacaoGraos")
    Origem = apps.get_model("graos", "OrigemSaldoGraos")
    Posicao = apps.get_model("graos", "PosicaoSaldoGraos")
    Vinculo = apps.get_model("cadpro", "CADProPropriedade")

    for lote in Lote.objects.select_related("armazem").all().iterator():
        classificacao = str(lote.classificacao_codigo or "PADRAO").strip().upper()
        atualizacoes = {"classificacao_codigo": classificacao or "PADRAO"}
        if not lote.cad_pro_id:
            vinculos = list(
                Vinculo.objects.filter(
                    propriedade_id=lote.armazem.propriedade_id,
                    ativo=True,
                    cad_pro__ativo=True,
                ).values_list("cad_pro_id", flat=True)[:2]
            )
            if len(vinculos) == 1:
                atualizacoes["cad_pro_id"] = vinculos[0]
        Lote.objects.filter(pk=lote.pk).update(**atualizacoes)

    saldos = {}
    versoes = {}
    pendentes = []
    for movimento in Movimento.objects.select_related("lote").order_by("id").iterator():
        lote = movimento.lote
        if not lote.cad_pro_id:
            pendentes.append(movimento.pk)
            continue
        chave = {
            "cad_pro_id": lote.cad_pro_id,
            "cultura": lote.cultura,
            "safra": lote.safra,
            "classificacao_codigo": lote.classificacao_codigo,
            "armazem_id": lote.armazem_id,
        }
        posicao, _ = Posicao.objects.get_or_create(**chave)
        origem = Origem.objects.create(
            tipo="legado",
            chave_idempotencia=f"legado:movimentacao:{movimento.pk}",
            referencia_externa=movimento.referencia_externa,
            hash_requisicao=hashlib.sha256(
                f"legado:{movimento.pk}".encode("utf-8")
            ).hexdigest(),
            metadados={"migration": "0003", "movimentacao_id": movimento.pk},
            criado_por_id=movimento.criado_por_id,
        )
        delta = movimento.quantidade_kg if movimento.tipo == "entrada" else -movimento.quantidade_kg
        saldo_anterior = saldos.get(posicao.pk, Decimal("0.000"))
        saldo_posterior = saldo_anterior + delta
        versao_anterior = versoes.get(posicao.pk, 0)
        versao_posterior = versao_anterior + 1
        Movimento.objects.filter(pk=movimento.pk).update(
            operacao="legado",
            posicao_id=posicao.pk,
            origem_id=origem.pk,
            delta_fisico_kg=delta,
            delta_comprometido_kg=0,
            snapshot_anterior={
                "posicao_id": posicao.pk,
                "saldo_fisico_kg": str(saldo_anterior),
                "saldo_comprometido_kg": "0.000",
                "saldo_disponivel_kg": str(saldo_anterior),
                "versao": versao_anterior,
            },
            snapshot_posterior={
                "posicao_id": posicao.pk,
                "saldo_fisico_kg": str(saldo_posterior),
                "saldo_comprometido_kg": "0.000",
                "saldo_disponivel_kg": str(saldo_posterior),
                "versao": vg=ÛËh‘éì¶»§q«^vWF–öãÕG'VR¢G'“ ¢6–FÂVçG&FÒG&ç6fW&—%öw&÷2€¢W7V&–ó×&WVW7BçW6W"À¢Æ÷FUö÷&–vVÓ×6VÆbævWEöö&¦V7B‚’À¢¢§6W&–Æ—¦W"çfÆ–FFVEöFFÀ¢¢W†6WBfÇVTW'&÷"2W†3 ¢&WGW&â&W7öç6R€¢²&FWF–Â#¢7G"†W†2—ÒÀ¢7FGW3×7FGW2ä…EEóC•ô4ôädÄ”5BÀ¢¢Ö÷f–ÖVçFõ÷6W&–Æ—¦W"ÒÖ÷f–ÖVçF6ôw&÷56W&–Æ—¦W"€¢‡6–FÂVçG&F’À¢Öç“ÕG'VRÀ¢¢&WGW&â&W7öç6R€¢°¢'6–F#¢Ö÷f–ÖVçFõ÷6W&–Æ—¦W"æFF³ÒÀ¢&VçG&F#¢Ö÷f–ÖVçFõ÷6W&–Æ—¦W"æFF³ÒÀ¢ÒÀ¢7FGW3×7FGW2ä…EEó#ô5$TDTBÀ¢  ¦6Æ72Ö÷f–ÖVçF6ôw&÷5f–Wu6WB€¢f–Ww6WG2æÖ—†–ç2ä7&VFTÖöFVÄÖ—†–âÀ¢f–Ww6WG2æÖ—†–ç2äÆ—7DÖöFVÄÖ—†–âÀ¢f–Ww6WG2æÖ—†–ç2å&WG&–WfTÖöFVÄÖ—†–âÀ¢f–Ww6WG2ävVæW&–5f–Wu6WBÀ¢“ ¢VW'—6WBÒÖ÷f–ÖVçF6ôw&÷2æö&¦V7G2ç6VÆV7E÷&VÆFVB€¢&Æ÷FR"À¢&Æ÷FUõö&Ö¦VÒ"À¢&Æ÷FUõö&Ö¦VÕõ÷&÷&–VFFR"À¢&7&–Fõ÷÷""À¢¢6W&–Æ—¦W%ö6Æ72ÒÖ÷f–ÖVçF6ôw&÷56W&–Æ—¦W ¢W&Ö—76–öåö6Æ76W2Ò´—4WF†VçF–6FVEĞ¢f–ÇFW%ö&6¶VæG2Ò¶f–ÇFW'2å6V&6„f–ÇFW"Âf–ÇFW'2ä÷&FW&–ætf–ÇFW%Ğ¢6V&6…öf–VÆG2Ò€¢&Æ÷FUõö6öF–vò"À¢&Æ÷FUõö7VÇGW&"À¢&Æ÷FUõ÷6g&"À¢'&VfW&Væ6–öW‡FW&æ"À¢&ö'6W'f6öW2"À¢¢÷&FW&–æuöf–VÆG2Ò‚&FFöÖ÷f–ÖVçFò"Â'VçF–FFUö¶r"Â'F—ò"Â&7&–FõöVÒ"¢÷&FW&–ærÒ‚"ÖFFöÖ÷f–ÖVçFò"Â"Ö–B" ¢FVbvWE÷VW'—6WB‡6VÆb“ ¢VW'—6WBÒ7WW"‚’ævWE÷VW'—6WB‚¢f÷"&ÖWG&òÂ6×ò–â€¢‚'F—ò"Â'F—ò"’À¢‚&Æ÷FR"Â&Æ÷FUö–B"’À¢‚&&Ö¦VÒ"Â&Æ÷FUõö&Ö¦VÕö–B"’À¢‚'&÷&–VFFR"Â&Æ÷FUõö&Ö¦VÕõ÷&÷&–VFFUö–B"’À¢‚'6g&"Â&Æ÷FUõ÷6g&"’À¢“ ¢fÆ÷"Ò6VÆbç&WVW7BçVW'•÷&×2ævWB‡&ÖWG&òÂ""’ç7G&—‚¢–bfÆ÷# ¢VW'—6WBÒVW'—6WBæf–ÇFW"‚¢§¶6×ó¢fÆ÷'Ò¢7VÇGW&Ò6VÆbç&WVW7BçVW'•÷&×2ævWB‚&7VÇGW&"Â""’ç7G&—‚¢–b7VÇGW& ¢VW'—6WBÒVW'—6WBæf–ÇFW"†Æ÷FUõö7VÇGW&õö–W†7CÖ7VÇGW&¢&WGW&âVW'—6W@ ¢7F–öâ†FWF–ÃÕG'VRÂÖWF†öG3Õ²'÷7B%ÒÂW&Å÷FƒÒ&W7F÷&æ""¢FVbW7F÷&æ"‡6VÆbÂ&WVW7BÂ³ÔæöæR“ ¢FF÷2Ò&WVW7BæFFæ6÷’‚¢FF÷5²&Ö÷f–ÖVçF6ò%ÒÒ°¢&WGW&âöW†V7WF%ö÷W&6ò€¢&WVW7BÀ¢W7F÷&æôÖ÷f–ÖVçF6õ6W&–Æ—¦W"À¢W7F÷&æ%öÖ÷f–ÖVçF6òÀ¢FF÷3ÖFF÷2À¢  ¦6Æ726ÆFôw&÷5f–Wu6WB‡f–Ww6WG2åf–Wu6WB“ ¢W&Ö—76–öåö6Æ76W2Ò´—4WF†VçF–6FVEĞ ¢FVbÆ—7B‡6VÆbÂ&WVW7B“ ¢f–ÇG&÷2Òf–ÇG&÷5÷6–6õ6ÆFõ6W&–Æ—¦W"†FF×&WVW7BçVW'•÷&×2¢f–ÇG&÷2æ—5÷fÆ–B‡&—6UöW†6WF–öãÕG'VR¢VW'—6WBÒ6öç7VÇF%÷÷6–6ò‚¢¦f–ÇG&÷2çfÆ–FFVEöFF¢&WGW&â&W7öç6R…÷6–6õ6ÆFôw&÷56W&–Æ—¦W"‡VW'—6WBÂÖç“ÕG'VR’æFF ¢FVb&WG&–WfR‡6VÆbÂ&WVW7BÂ³ÔæöæR“ ¢÷6–6òÒ6öç7VÇF%÷÷6–6ò‚’æf–ÇFW"‡³×²’æf—'7B‚¢–bæ÷B÷6–6ó ¢&WGW&â&W7öç6R€¢²&FWF–Â#¢%÷6œ:|:6òFR6ÆFòì:6òVæ6öçG&Fâ'ÒÀ¢7FGW3×7FGW2ä…EEóCEôäõEôdõTäBÀ¢¢&WGW&â&W7öç6R…÷6–6õ6ÆFôw&÷56W&–Æ—¦W"‡÷6–6ò’æFF ¢FVböW†V7WF"‡6VÆbÂ&WVW7BÂ6W&–Æ—¦W%ö6Æ72Â6W'f–6ò“ ¢&WGW&âöW†V7WF%ö÷W&6ò‡&WVW7BÂ6W&–Æ—¦W%ö6Æ72Â6W'f–6ò ¢7F–öâ†FWF–ÃÔfÇ6RÂÖWF†öG3Õ²'÷7B%ÒÂW&Å÷FƒÒ&7&VF—F"×&öGV6ò"¢FVb7&VF—F%÷&öGV6ò‡6VÆbÂ&WVW7B“ ¢&WGW&â6VÆbåöW†V7WF"‡&WVW7BÂ÷W&6ôÆ÷FU6W&–Æ—¦W"Â7&VF—F%÷&öGV6ò ¢7F–öâ†FWF–ÃÔfÇ6RÂÖWF†öG3Õ²'÷7B%ÒÂW&Å÷FƒÒ'&W6W'f""¢FVb&W6W'f"‡6VÆbÂ&WVW7B“ ¢&WGW&â6VÆbåöW†V7WF"‡&WVW7BÂ&W6W'f%6ÆFõ6W&–Æ—¦W"Â&W6W'f%÷6ÆFò ¢7F–öâ†FWF–ÃÔfÇ6RÂÖWF†öG3Õ²'÷7B%ÒÂW&Å÷FƒÒ&Æ–&W&"×&W6W'f"¢FVbÆ–&W&%÷&W6W'f‡6VÆbÂ&WVW7B“ ¢&WGW&â6VÆbåöW†V7WF"‡&WVW7BÂÆ–&W&%&W6W'f6W&–Æ—¦W"ÂÆ–&W&%÷&W6W'f ¢7F–öâ†FWF–ÃÔfÇ6RÂÖWF†öG3Õ²'÷7B%ÒÂW&Å÷FƒÒ&6öæf—&Ö"ÖVçG&Vv"¢FVb6öæf—&Ö%öVçG&Vv‡6VÆbÂ&WVW7B“ ¢&WGW&â6VÆbåöW†V7WF"‡&WVW7BÂ÷W&6õ&W6W'f6W&–Æ—¦W"Â6öæf—&Ö%öVçG&Vv ¢7F–öâ†FWF–ÃÔfÇ6RÂÖWF†öG3Õ²'÷7B%ÒÂW&Å÷FƒÒ'&Vv—7G&"ÖFWföÇV6ò"¢FVb&Vv—7G&%öFWföÇV6ò‡6VÆbÂ&WVW7B“ ¢&WGW&â6VÆbåöW†V7WF"‡&WVW7BÂ÷W&6ôÆ÷FU6W&–Æ—¦W"Â&Vv—7G&%öFWföÇV6ò ¢7F–öâ†FWF–ÃÔfÇ6RÂÖWF†öG3Õ²'÷7B%ÒÂW&Å÷FƒÒ'&Vv—7G&"Ö§W7FR"¢FVb&Vv—7G&%ö§W7FR‡6VÆbÂ&WVW7B“ ¢&WGW&â6VÆbåöW†V7WF"‡&WVW7BÂ§W7FU6ÆFõ6W&–Æ—¦W"Â&Vv—7G&%ö§W7FR ¢7F–öâ†FWF–ÃÔfÇ6RÂÖWF†öG3Õ²'÷7B%ÒÂW&Å÷FƒÒ&W7F÷&æ"ÖÖ÷f–ÖVçF6ò"¢FVbW7F÷&æ%öÖ÷f–ÖVçF6ò‡6VÆbÂ&WVW7B“ ¢&WGW&â6VÆbåöW†V7WF"€¢&WVW7BÀ¢W7F÷&æôÖ÷f–ÖVçF6õ6W&–Æ—¦W"À¢W7F÷&æ%öÖ÷f–ÖVçF6òÀ¢ ¢7F–öâ†FWF–ÃÔfÇ6RÂÖWF†öG3Õ²'÷7B%ÒÂW&Å÷FƒÒ'G&ç6fW&—""¢FVbG&ç6fW&—"‡6VÆbÂ&WVW7B“ ¢&WGW&â6VÆbåöW†V7WF"€¢&WVW7BÀ¢G&ç6fW&—%6ÆFôf—6–6õ6W&–Æ—¦W"À¢G&ç6fW&—%÷6ÆFõöf—6–6òÀ¢ ¢7F–öâ†FWF–ÃÔfÇ6RÂÖWF†öG3Õ²'÷7B%ÒÂW&Å÷FƒÒ'&V6öæ6–Æ–""¢FVb&V6öæ6–Æ–"‡6VÆbÂ&WVW7B“ ¢&WGW&â6VÆbåöW†V7WF"€¢&WVW7BÀ¢&V6öæ6–Æ–%÷6–6õ6W&–Æ—¦W"À¢&V6öæ6–Æ–%÷÷6–6òÀ¢  ¦6Æ72÷&–vVÕ6ÆFôw&÷5f–Wu6WB‡f–Ww6WG2å&VDöæÇ”ÖöFVÅf–Wu6WB“ ¢VW'—6WBÒ6VÆV6–öæ%ö÷&–vVç2‚¢6W&–Æ—¦W%ö6Æ72Ò÷&–vVÕ6ÆFôw&÷56W&–Æ—¦W ¢W&Ö—76–öåö6Æ76W2Ò´—4WF†VçF–6FVEĞ¢f–ÇFW%ö&6¶VæG2Ò¶f–ÇFW'2å6V&6„f–ÇFW"Âf–ÇFW'2ä÷&FW&–ætf–ÇFW%Ğ¢6V&6…öf–VÆG2Ò‚&6†fUö–FV×÷FVæ6–"Â'&VfW&Væ6–öW‡FW&æ"¢÷&FW&–æuöf–VÆG2Ò‚'F—ò"Â&7&–FõöVÒ" ¢FVbvWE÷VW'—6WB‡6VÆb“ ¢VW'—6WBÒ7WW"‚’ævWE÷VW'—6WB‚¢F—òÒ6VÆbç&WVW7BçVW'•÷&×2ævWB‚'F—ò"Â""’ç7G&—‚¢–bF—ó ¢VW'—6WBÒVW'—6WBæf–ÇFW"‡F—ó×F—ò¢&WGW&âVW'—6W@  ¦6Æ72&W6W'f6ÆFôw&÷5f–Wu6WB‡f–Ww6WG2å&VDöæÇ”ÖöFVÅf–Wu6WB“ ¢VW'—6WBÒ6VÆV6–öæ%÷&W6W'f2‚¢6W&–Æ—¦W%ö6Æ72Ò&W6W'f6ÆFôw&÷56W&–Æ—¦W ¢W&Ö—76–öåö6Æ76W2Ò´—4WF†VçF–6FVEĞ¢f–ÇFW%ö&6¶VæG2Ò¶f–ÇFW'2ä÷&FW&–ætf–ÇFW%Ğ¢÷&FW&–æuöf–VÆG2Ò‚'7FGW2"Â&7&–FõöVÒ"Â'6ÆFõ÷&W6W'fFõö¶r" ¢FVbvWE÷VW'—6WB‡6VÆb“ ¢&WGW&â6VÆV6–öæ%÷&W6W'f2€¢÷6–6ó×6VÆbç&WVW7BçVW'•÷&×2ævWB‚'÷6–6ò"Â""’ç7G&—‚’À¢7FGW3×6VÆbç&WVW7BçVW'•÷&×2ævWB‚'7FGW2"Â""’ç7G&—‚’À¢