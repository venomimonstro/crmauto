import {useEffect,useRef,useState,type FormEvent} from "react";
import {api} from "./api";
type Profile={legal_name:string;entity_kind:string;inn:string;kpp:string;ogrn:string;postal_address:string;service_address:string;phone:string;email:string;bank_name:string;bik:string;account_number:string;correspondent_account:string;tax_label:string;version:number};
const fields:[keyof Profile,string][]=[["legal_name","Наименование исполнителя"],["inn","ИНН"],["kpp","КПП"],["ogrn","ОГРН / ОГРНИП"],["postal_address","Юридический адрес"],["service_address","Адрес автосервиса"],["phone","Телефон"],["email","Электронная почта"],["bank_name","Банк"],["bik","БИК"],["account_number","Расчётный счёт"],["correspondent_account","Корреспондентский счёт"],["tax_label","Налогообложение"]];
export default function LegalProfile({organization}:{organization:string}){
 const [data,setData]=useState<Profile|null>(null),[error,setError]=useState(""),[notice,setNotice]=useState(""),[busy,setBusy]=useState(false);
 const key=useRef<string|null>(null);
 useEffect(()=>{let active=true;setData(null);setError("");api<Profile>("organization/legal-profile",{organization})
  .then(p=>{if(active)setData(p);}).catch(e=>{if(active)setError(String(e));});return()=>{active=false;};},[organization]);
 async function save(e:FormEvent){
  e.preventDefault();if(!data)return;setBusy(true);setError("");setNotice("");
  if(!key.current)key.current=crypto.randomUUID();
  const {version,...payload}=data;
  try{const next=await api<Profile>("organization/legal-profile",{method:"PATCH",organization,
   ifMatch:version,idempotencyKey:key.current,data:payload});
   key.current=null;setData(next);setNotice("Реквизиты сохранены.");}
  catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
 }
 return <section className="card action-card" style={{marginTop:16}}><h2>Реквизиты для печатных документов</h2>
  <p className="muted">Проверяйте реквизиты перед печатью: автоматической проверки по реестрам нет.</p>
  {error&&<p className="notice error">{error}</p>}{notice&&<p className="notice info">{notice}</p>}
  {!data?<div className="loading-inline">Загрузка реквизитов…</div>:<form onSubmit={save}>
   <label>Тип исполнителя<select value={data.entity_kind}
    onChange={e=>setData({...data,entity_kind:e.target.value})}>
    <option value="company">Юридическое лицо</option><option value="individual">ИП</option>
    <option value="self_employed">Самозанятый</option></select></label>
   <div className="form-grid">{fields.filter(([field])=>field!=="kpp"||data.entity_kind==="company").map(([field,label])=>
    <label key={field}>{label}<input value={String(data[field])} onChange={e=>{key.current=null;setData({...data,[field]:e.target.value});}}/></label>)}</div>
   <button className="primary" disabled={busy}>{busy?"Сохранение…":"Сохранить реквизиты"}</button>
  </form>}
 </section>;
}