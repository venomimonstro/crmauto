import {useCallback,useEffect,useState} from "react";
import {api} from "./api";
type Doc={id:string;type:string;title:string;revision:number;created_at:string;sha256:string;state:string};
type DocumentWithHtml=Doc&{html:string};
const kinds=[
  {type:"work_order",title:"Заказ-наряд"},
  {type:"intake",title:"Акт приёмки"},
  {type:"completion",title:"Акт выполненных работ"},
  {type:"handover",title:"Акт выдачи автомобиля"},
  {type:"warranty",title:"Гарантийная памятка"},
];
export default function OrderDocuments({organization,orderId,orderStatus,canEdit}:{
 organization:string;orderId:string;orderStatus:string;canEdit:boolean;
}){
 const [docs,setDocs]=useState<Doc[]>([]);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 const [notice,setNotice]=useState("");
 const refresh=useCallback(async()=>setDocs(await api<Doc[]>(
   "workorders/"+orderId+"/documents",{organization})),[organization,orderId]);
 useEffect(()=>{
   let active=true;setDocs([]);setError("");
   api<Doc[]>("workorders/"+orderId+"/documents",{organization})
      .then(v=>{if(active)setDocs(v);})
      .catch(e=>{if(active)setError(e instanceof Error?e.message:"Ошибка документов");});
   return()=>{active=false;};
 },[organization,orderId]);
 async function create(type:string){
   setBusy(true);setError("");setNotice("");
   try{
     await api("workorders/"+orderId+"/documents",{method:"POST",organization,
       idempotencyKey:crypto.randomUUID(),data:{type}});
     await refresh();setNotice("Новая версия документа сформирована.");
   }catch(e){setError(e instanceof Error?e.message:"Документ не создан");}
   finally{setBusy(false);}
 }
 async function open(doc:Doc){
   setBusy(true);setError("");
   try{
     const result=await api<DocumentWithHtml>("workorders/"+orderId+"/documents/"+doc.id,{organization});
     const blob=new Blob([result.html],{type:"text/html;charset=utf-8"});
     const url=URL.createObjectURL(blob);
     const a=document.createElement("a");a.href=url;
     a.download=doc.type+"-"+orderId.slice(0,8)+"-v"+doc.revision+".html";
     document.body.append(a);a.click();a.remove();
     URL.revokeObjectURL(url);
     setNotice("Документ скачан в формате HTML. Откройте его и выберите печать или «Сохранить в PDF».");
   }catch(e){setError(e instanceof Error?e.message:"Ошибка загрузки документа");}
   finally{setBusy(false);}
 }
 return <section className="order-documents" style={{marginTop:24}}>
   <h2>Документы по ремонту</h2>
   <p className="muted">Бланки для печати и подписания. Не являются подтверждением оплаты, электронной подписью или фискальными чеками.</p>
   {error&&<div className="notice error" role="alert">{error}</div>}
   {notice&&<div className="notice info" role="status">{notice}</div>}
   {canEdit&&<div className="quick-actions" style={{marginBottom:16}}>
    {kinds.map(k=><button type="button" className="secondary" key={k.type} disabled={busy||
      (["completion","handover","warranty"].includes(k.type)&&!["qa","ready","delivered"].includes(orderStatus))}
      onClick={()=>void create(k.type)}>+ {k.title}</button>)}
   </div>}
   <div className="table-scroll"><table><thead><tr><th>Документ</th><th>Версия</th><th>Создан</th><th>Действие</th></tr></thead>
   <tbody>{docs.map(d=><tr key={d.id}>
     <td>{d.title}</td><td>№{d.revision}</td>
     <td>{new Date(d.created_at).toLocaleString("ru-RU")}</td>
     <td><button className="secondary" type="button" disabled={busy} onClick={()=>void open(d)}>Скачать / печать</button></td>
   </tr>)}</tbody></table>{!docs.length&&<p className="table-empty">Документы ещё не сформированы.</p>}</div>
 </section>;
}