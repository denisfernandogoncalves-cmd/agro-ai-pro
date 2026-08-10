from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.propriedades.models import Propriedade

from ..models import CADPro, CADProPropriedade


class CADProEndpointTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="cadpro-teste", password="senha-segura"
        )
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda API",
            municipio="Londrina",
            uf="PR",
            area_hectares="50.00",
        )

    def test_endpoints_exigem_autenticacao(self):
        cad_pro = CADPro.objects.create(codigo="1000001", descricao="Titular")
        for metodo, url, dados in (
            (self.client.get, "/api/cadpros/", None),
            (self.client.post, "/api/cadpros/", {}),
            (self.client.get, f"/api/cadpros/{cad_pro.pk}/", None),
            (self.client.patch, f"/api/cadpros/{cad_pro.pk}/", {}),
            (self.client.get, f"/api/cadpros/{cad_pro.pk}/propriedades/", None),
            (self.client.post, f"/api/cadpros/{cad_pro.pk}/propriedades/", {}),
            (self.client.post, f"/api/cadpros/{cad_pro.pk}/inativar/", {}),
        ):
            resposta = metodo(url, dados, format="json") if dados is not None else metodo(url)
            self.assertEqual(resposta.status_code, 401, (metodo, url, resposta.data))

    def test_fluxo_completo_sem_delete_publico(self):
        self.client.force_authenticate(self.usuario)
        criacao = self.client.post(
            "/api/cadpros/",
            {"codigo": " 123.456-7 ", "descricao": "Produtor V1", "ativo": False},
            format="json",
        )
        self.assertEqual(criacao.status_code, 201, criacao.data)
        cad_pro_id = criacao.data["id"]
        self.assertEqual(criacao.data["codigo_normalizado"], "1234567")
        self.assertTrue(criacao.data["ativo"])
        lista = self.client.get("/api/cadpros/?search=123.456")
        self.assertEquaoyç­m¢G§²ÚîÆ­yÔ66R‚’Ò—ÒóãÂöÆ&VÃà¢ÂöF—cà¢ÆÆ&VÃäÆö6ÂFR6öÆ†V—FÆ–çWBÆ6V†öÆFW#Ò%FÆŒ:6òÂvÆV&÷RöçFòFR÷&–vVÒ"fÇVS×¶6&væÆö6Åö6öÆ†V—FÒöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂÆö6Åö6öÆ†V—F¢RçF&vWBçfÇVRÒ—ÒóãÂöÆ&VÃà¢ÆÆ&VÃåW6ò''WFò†¶r“Æ–çWB&WV—&VBÖ–ãÒ#ã"7FWÒ#ã"G—SÒ&çVÖ&W""fÇVS×¶6&vçW6õö''WFõö¶wÒöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂW6õö''WFõö¶s¢RçF&vWBçfÇVRÒ—ÒóãÂöÆ&VÃà¢ÆF—b6Æ74æÖSÒ&Æ–æ†#à¢ÆÆ&VÃåVÖ–FFR‚R“Æ–çWB&WV—&VBÖ–ãÒ#"ÖƒÒ#"7FWÒ#ã"G—SÒ&çVÖ&W""fÇVS×¶6&vçVÖ–FFU÷W&6VçGVÇÒöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂVÖ–FFU÷W&6VçGVÃ¢RçF&vWBçfÇVRÒ—ÒóãÂöÆ&VÃà¢ÆÆ&VÃä–×W&W¦‚R“Æ–çWB&WV—&VBÖ–ãÒ#"ÖƒÒ#"7FWÒ#ã"G—SÒ&çVÖ&W""fÇVS×¶6&væ–×W&W¦÷W&6VçGVÇÒöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂ–×W&W¦÷W&6VçGVÃ¢RçF&vWBçfÇVRÒ—ÒóãÂöÆ&VÃà¢ÆÆ&VÃäFVfV—F÷2‚R“Æ–çWB&WV—&VBÖ–ãÒ#"ÖƒÒ#"7FWÒ#ã"G—SÒ&çVÖ&W""fÇVS×¶6&væFVfV—F÷5÷W&6VçGVÇÒöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂFVfV—F÷5÷W&6VçGVÃ¢RçF&vWBçfÇVRÒ—ÒóãÂöÆ&VÃà¢ÂöF—cà¢ÆF—b6Æ74æÖSÒ&Æ–æ†#à¢ÆÆ&VÃåƒÆ–çWBÖ–ãÒ#"ÖƒÒ#"7FWÒ#ã"G—SÒ&çVÖ&W""fÇVS×¶6&vç‡Òöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂƒ¢RçF&vWBçfÇVRÒ—ÒóãÂöÆ&VÃà¢ÆÆ&VÂ6Æ74æÖSÒ&÷6òÖ6†V6¶&÷‚#ãÆ–çWBG—SÒ&6†V6¶&÷‚"6†V6¶VC×¶6&væFW7F–æFõ÷6VÖVçFWÒöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂFW7F–æFõ÷6VÖVçFS¢RçF&vWBæ6†V6¶VBÒ—ÒóâFW7F–æF6VÖVçFSÂöÆ&VÃà¢ÂöF—cà¢ÆÆ&VÃäö'6W'f:|;VW3ÇFW‡F&VfÇVS×¶6&væö'6W'f6öW7Òöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂö'6W'f6öW3¢RçF&vWBçfÇVRÒ—ÒóãÂöÆ&VÃà¢ÆF—b6Æ74æÖSÒ'&W7VÖò×W6ò"&–ÖÆ—fSÒ'öÆ—FR#à¢Ç7ãäFW66öçFòÇ7G&öæsç¶6Æ7VÆòçW&6VçGVÂçFôf—†VBƒ2—ÒSÂ÷7G&öæsãÂ÷7ãà¢Ç7ãåW6òÌ:×V–FòÇ7G&öæsç¶6Æ7VÆòæÆ—V–FòçFôÆö6ÆU7G&–ær‚'BÔ%""Â²Ö†–×VÔg&7F–öäF–v—G3¢2Ò—Ò¶sÂ÷7G&öæsãÂ÷7ãà¢Ç7ãä6öçfW'<:6òÇ7G&öæsç¶6Æ7VÆòç662çFôÆö6ÆU7G&–ær‚'BÔ%""Â²Ö†–×VÔg&7F–öäF–v—G3¢2Ò—Ò663Â÷7G&öæsãÂ÷7ãà¢ÂöF—cà¢Æ'WGFöâF—6&ÆVC×¶6'&VvæFòÇÂ6Æ7VÆòçW&6VçGVÂãÒÒG—SÒ'7V&Ö—B#å&Vv—7G&"R7&VF—F"6ÆFóÂö'WGFöãà¢Âöf÷&Óà ¢Ç6V7F–öâ6Æ74æÖSÒ&6öçFWVFò#à¢ÆF—b6Æ74æÖSÒ'–æVÂÖf–ÇG&÷2#à¢Æ–çWB&–ÖÆ&VÃÒ$'W66"6&v2"Æ6V†öÆFW#Ò$'W66"Æ6Â&÷&–VFFRÂw'WòÂ4Bõ$ò÷RÆö6Â"fÇVS×¶'W66Òöä6†ævS×²†R’Óâ6WD'W66†RçF&vWBçfÇVR—Òóà¢Æ'WGFöâG—SÒ&'WGFöâ"öä6Æ–6³×²‚’Óâfö–B6'&Vv"‚—ÓäGVÆ—¦#Âö'WGFöãà¢ÂöF—cà¢ÆF—b6Æ74æÖSÒ&Æ—7F6&v2ÖÆ—7F#à¢¶6&v4f–ÇG&F2æÆVæwF‚ÓÓÒòÆF—b6Æ74æÖSÒ&6&Bf¦–ò#äæVæ‡VÖ6&v6öÆ†–F&Vv—7G&FãÂöF—câ¢6&v4f–ÇG&F2æÖ‚†—FVÒ’Óâ€¢Æ'F–6ÆR6Æ74æÖSÒ&6&B6&vÖ—FVÒ"¶W“×¶—FVÒæ–GÓà¢ÆF—b6Æ74æÖSÒ&6&vÖ—FVÒ×F÷ò#ãÆF—cãÇ7â6Æ74æÖSÒ&¶–6¶W"#ç¶—FVÒæFFö6öÆ†V—FÒ+r¶—FVÒçÆ6ÓÂ÷7ããÆƒ3ç¶—FVÒç&÷&–VFFUöæöÖWÓÂöƒ3ãÇç¶—FVÒæw'Wõö6öÆ†V—FöæöÖWÒ+r4Bõ$ò¶—FVÒæ6E÷&õö6öF–v÷Ò+r¶—FVÒæ&Ö¦VÕöæöÖWÓÂ÷ãÂöF—cãÇ7G&öæsç¶çVÖW&ò†—FVÒç665óc¶r’çFôÆö6ÆU7G&–ær‚'BÔ%""Â²Ö†–×VÔg&7F–öäF–v—G3¢2Ò—Ò63Â÷7G&öæsãÂöF—cà¢ÆF—b6Æ74æÖSÒ&6&vÖÖWG&–62#ãÇ7ãä''WFòÇ7G&öæsç¶çVÖW&ò†—FVÒçW6õö''WFõö¶r’çFôÆö6ÆU7G&–ær‚'BÔ%""—Ò¶sÂ÷7G&öæsãÂ÷7ããÇ7ãäFW66öçFòÇ7G&öæsç¶—FVÒæFW66öçFõ÷F÷FÅ÷W&6VçGVÇÒSÂ÷7G&öæsãÂ÷7ããÇ7ãäÌ:×V–FòÇ7G&öæsç¶çVÖW&ò†—FVÒçW6õöÆ—V–Fõö¶r’çFôÆö6ÆU7G&–ær‚'BÔ%""—Ò¶sÂ÷7G&öæsãÂ÷7ããÂöF—cà¢Ç6ÖÆÃåVÖ–FFR¶—FVÒçVÖ–FFU÷W&6VçGVÇÒR+r–×W&W¦¶—FVÒæ–×W&W¦÷W&6VçGVÇÒR+rFVfV—F÷2¶—FVÒæFVfV—F÷5÷W&6VçGVÇÒW¶—FVÒç‚ò+r‚G¶—FVÒç‡Ö¢"'×¶—FVÒæFW7F–æFõ÷6VÖVçFRò"+r6VÖVçFR"¢"'Ò+rÖ÷f–ÖVçFò7¶—FVÒæÖ÷f–ÖVçF6÷ÓÂ÷6ÖÆÃà¢Âö'F–6ÆSà¢’—Ğ¢ÂöF—cà¢Â÷6V7F–öãà¢Â÷6V7F–öãà¢Â÷6V7F–öãà¢“°§Ğ 