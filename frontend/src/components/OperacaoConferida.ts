import axios from 'axios';
import { api } from '../api/propriedades';
import { useConfirmacaoCompacta } from './ConfirmacaoCompacta';

export function useOperacaoConferida() {
  const confirmar=useConfirmacaoCompacta();
  return async function executar<T>(acao:()=>Promise<T>):Promise<T> {
    try {return await acao();}
    catch(erro) {
      if(!axios.isAxiosError(erro)||erro.response?.status!==409||erro.response.data?.codigo!=='periodo_fechado'||!erro.config)throw erro;
      if(!await confirmar({titulo:'Alterar período conferido',mensagem:erro.response.data.detail,confirmar:'Confirmar alteração',perigo:true}))throw new Error('Alteração cancelada. O lançamento foi preservado.');
      return (await api.request<T>({...erro.config,headers:{...erro.config.headers,'Confirmar-Periodo-Fechado':'sim'}})).data;
    }
  };
}
