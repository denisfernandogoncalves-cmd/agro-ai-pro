import type { Propriedade } from "../../api/propriedades";
import ImportacaoHistory from "./ImportacaoHistory";
import ProducaoPage from "./ProducaoPage";

export default function ProducaoIntegratedPage(props: {
  properties: Propriedade[];
  selectedProperty: Propriedade | null;
  shellSafra: string;
  canManage: boolean;
  canOperate: boolean;
}) {
  return (
    <div className="production-integrated-page">
      <ProducaoPage {...props} />
      <ImportacaoHistory
        selectedProperty={props.selectedProperty}
        canManage={props.canManage}
      />
    </div>
  );
}
