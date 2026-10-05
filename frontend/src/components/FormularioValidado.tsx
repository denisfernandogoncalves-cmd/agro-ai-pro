import { FormHTMLAttributes, forwardRef, useId, useImperativeHandle, useRef, useState } from "react";
import { createPortal } from "react-dom";
type Campo = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
export function mensagemValidacao(validade: Pick<ValidityState,"valueMissing"|"rangeUnderflow"|"rangeOverflow"|"typeMismatch"|"badInput"|"stepMismatch"|"tooLong">) {
  if(validade.valueMissing)return "Preencha este campo para continuar.";
  if(validade.rangeUnderflow||validade.rangeOverflow)return "Informe um valor dentro dos limites deste campo.";
  if(validade.typeMismatch||validade.badInput||validade.stepMismatch)return "Confira o formato ou o valor informado.";
  if(validade.tooLong)return "Reduza o texto deste campo.";
  return "Confira este campo antes de continuar.";
}
const FormularioValidado=forwardRef<HTMLFormElement,FormHTMLAttributes<HTMLFormElement>>(function FormularioValidado({children,onSubmit,onBlurCapture,onInputCapture,...props},externa){
  const form=useRef<HTMLFormElement>(null),prefixo=useId(),campos=useRef(new WeakMap<Campo,string>()),contador=useRef(0);
  const [erros,setErros]=useState<Record<string,{campo:Campo;alvo:Element;mensagem:string}>>({});
  useImperativeHandle(externa,()=>form.current!);
  function validar(campo:Campo){let id=campos.current.get(campo);if(!id){id=`${prefixo}-campo-${++contador.current}`;campos.current.set(campo,id);}const chave=id;
    if(campo.validity.valid){campo.removeAttribute("aria-invalid");campo.removeAttribute("aria-errormessage");setErros(atual=>{const proximo={...atual};delete proximo[chave];return proximo;});return;}
    campo.setAttribute("aria-invalid","true");campo.setAttribute("aria-errormessage",chave);
    const alvo=campo.closest("label")||campo.parentElement;if(alvo)setErros(atual=>({...atual,[chave]:{campo,alvo,mensagem:mensagemValidacao(campo.validity)}}));
  }
  function ehCampo(alvo:EventTarget|null):alvo is Campo{return alvo instanceof HTMLInputElement||alvo instanceof HTMLSelectElement||alvo instanceof HTMLTextAreaElement;}
  return <form {...props} ref={form} noValidate onInvalidCapture={e=>{e.preventDefault();if(ehCampo(e.target))validar(e.target);}} onBlurCapture={e=>{if(ehCampo(e.target))validar(e.target);onBlurCapture?.(e);}} onInputCapture={e=>{if(ehCampo(e.target)&&e.target.getAttribute("aria-invalid"))validar(e.target);onInputCapture?.(e);}} onSubmit={e=>{if(!e.currentTarget.checkValidity()){e.preventDefault();e.currentTarget.querySelector<Campo>(":invalid")?.focus();return;}onSubmit?.(e);}}>{children}{Object.entries(erros).map(([id,erro])=>createPortal(<small id={id} className="erro-campo" role="alert">{erro.mensagem}</small>,erro.alvo,id))}</form>;
});
export default FormularioValidado;
