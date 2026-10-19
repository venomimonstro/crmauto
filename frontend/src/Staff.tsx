import {useEffect,useRef,useState,type FormEvent} from "react";
import {api} from "./api";

type Branch={id:string;name:string};
type Invite={id:string;email:string;role:string;branch_id:string|null;expires_at:string};
const ROLES=[
  {value:"manager",label:"Управляющий"},
  {value:"adviser",label:"Мастер-приёмщик"},
  {value:"mechanic",label:"Механик"},
  {value:"stock",label:"Кладовщик"},
  {value:"cashier",label:"Кассир"},
  {value:"viewer",label:"Наблюдатель"},
];
function message(error:unknown){return error instanceof Error?error.message:"Ошибка операции";}

export function Staff({organization,role}:{organization:string;role:string}){
  const [email,setEmail]=useState("");
  const [selectedRole,setSelectedRole]=useState("mechanic");
  const [branches,setBranches]=useState<Branch[]>([]);
  const [branchId,setBranchId]=useState("");
  const [invitations,setInvitations]=useState<Invite[]>([]);
  const [busy,setBusy]=useState(false);
  const [notice,setNotice]=useState("");
  const [error,setError]=useState("");
  const attempt=useRef<{signature:string;key:string}|null>(null);
  const canInvite=["owner","manager"].includes(role);
  useEffect(()=>{
    let active=true;
    setBranches([]);setInvitations([]);setError("");
    Promise.all([
      api<Branch[]>("branches",{organization}),
      canInvite?api<Invite[]>("staff/invitations",{organization}):Promise.resolve([]),
    ]).then(([b,inv])=>{
      if(!active)return;
      setBranches(b);setBranchId(b[0]?.id??"");setInvitations(inv);
    }).catch(e=>{if(active)setError(message(e));});
    return()=>{active=false;};
  },[organization,canInvite]);
  async function submit(e:FormEvent){
    e.preventDefault();
    if(!canInvite)return;
    setError("");setNotice("");setBusy(true);
    const payload={email:email.trim().toLowerCase(),role:selectedRole,
      ...((selectedRole==="manager")?{}:{branch_id:branchId})};
    const signature=JSON.stringify(payload);
    if(attempt.current?.signature!==signature){
      attempt.current={signature,key:crypto.randomUUID()};
    }
    try{
      await api("staff/invitations",{method:"POST",organization,
        idempotencyKey:attempt.current.key,data:payload});
      attempt.current=null;
      setNotice("Приглашение отправлено. Сотрудник получит письмо и сможет принять его после входа.");
      setEmail("");
      const rows=await api<Invite[]>("staff/invitations",{organization});
      setInvitations(rows);
    }catch(e){setError(message(e));}
    finally{setBusy(false);}
  }
  return <><div className="page-lead"><div><div className="eyebrow">Доступ сотрудников</div>
    <h1>Команда автосервиса</h1>
    <p className="muted">Каждому сотруднику — собственная подтверждённая учётная запись и роль.</p>
  </div></div>
  {error&&<div className="notice error" role="alert">{error}</div>}
  {notice&&<div className="notice info" role="status">{notice}</div>}
  {!canInvite?<div className="notice info">Управлять доступами могут владелец и управляющий.</div>:
  <>
    <section className="card action-card">
      <h2>Пригласить сотрудника</h2>
      <form onSubmit={submit}>
        <label>Электронная почта
          <input type="email" required autoComplete="off" value={email}
            onChange={e=>setEmail(e.target.value)} placeholder="employee@example.ru"/>
        </label>
        <div className="form-grid">
          <label>Роль<select value={selectedRole} onChange={e=>setSelectedRole(e.target.value)}>
            {ROLES.filter(x=>x.value!=="manager"||role==="owner").map(x=>
              <option key={x.value} value={x.value}>{x.label}</option>)}
          </select></label>
          {selectedRole!=="manager"&&<label>Филиал
            <select required value={branchId} onChange={e=>setBranchId(e.target.value)}>
              <option value="">Выберите филиал</option>
              {branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}
            </select></label>}
        </div>
        <button className="primary" disabled={busy||!email||(!branchId&&selectedRole!=="manager")}>
          {busy?"Отправка…":"Пригласить по почте"}
        </button>
      </form>
    </section>
    <section className="card action-card" style={{marginTop:16}}>
      <h2>Ожидают принятия</h2>
      <div className="table-scroll"><table><thead><tr>
        <th>Почта</th><th>Роль</th><th>Филиал</th><th>Срок</th>
      </tr></thead><tbody>
        {invitations.map(x=><tr key={x.id}><td>{x.email}</td>
          <td>{ROLES.find(r=>r.value===x.role)?.label??x.role}</td>
          <td>{branches.find(b=>b.id===x.branch_id)?.name??"Все филиалы"}</td>
          <td>{new Date(x.expires_at).toLocaleDateString("ru-RU")}</td>
        </tr>)}
      </tbody></table>{!invitations.length&&<p className="table-empty">Пока нет приглашений.</p>}
      </div>
      <p className="muted">Действующее приглашение учитывается в лимите сотрудников тарифного плана.</p>
    </section>
  </>}
  </>;
}

export function AcceptInvitation({token,onAccepted,onDecline}:{
  token:string;onAccepted:()=>Promise<void>;onDecline:()=>void;
}){
  const [busy,setBusy]=useState(false),[error,setError]=useState("");
  async function accept(){
    setBusy(true);setError("");
    try{
      await api("staff/invitations/accept",{method:"POST",data:{token}});
      await onAccepted();
    }catch(e){setError(message(e));}finally{setBusy(false);}
  }
  return <main className="empty-workspace">
    <section className="card create-org">
      <h1>Приглашение в автосервис</h1>
      <p className="muted">Войти в команду может только владелец адреса электронной почты,
        указанного при приглашении. Текущая учётная запись должна быть подтверждена.</p>
      {error&&<div className="notice error" role="alert">{error}</div>}
      <div className="quick-actions">
        <button className="primary" disabled={busy} onClick={()=>void accept()}>
          {busy?"Проверка…":"Принять приглашение"}
        </button>
        <button className="secondary" disabled={busy} onClick={onDecline}>Отмена</button>
      </div>
    </section>
  </main>;
}
