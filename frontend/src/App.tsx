import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import {
  Activity, BarChart3, CalendarDays, CarFront, CheckCircle2, ChevronDown,
  CircleHelp, ClipboardList, CreditCard, Gauge, LayoutDashboard, LogOut,
  Menu, Package, Plus, Search, Settings, ShieldCheck, ShoppingCart, Users, Wrench, X,
} from "lucide-react";
import Schedule from "./Schedule";
import WorkOrders from "./WorkOrders";
import Inventory from "./Inventory";
import Reports from "./Reports";
import Dismantling from "./Dismantling";
import CashDesk from "./CashDesk";
import SubscriptionPage from "./SubscriptionPage";
import { Staff, AcceptInvitation } from "./Staff";
import TireStorage from "./TireStorage";
import OwnerDashboard from "./OwnerDashboard";
import { api, ApiError, type Customer, type Organization, type SessionUser, type Vehicle } from "./api";

type Area = "dashboard" | "customers" | "vehicles" | "orders" | "lifts" | "tyres" |
  "inventory" | "donors" | "suppliers" | "personnel" | "cash" | "reports" | "settings";
const navigation: { key: Area; title: string; icon: typeof Users; ready: boolean }[] = [
  { key: "dashboard", title: "Главная", icon: LayoutDashboard, ready: true },
  { key: "customers", title: "Клиенты", icon: Users, ready: true },
  { key: "vehicles", title: "Автомобили", icon: CarFront, ready: true },
  { key: "orders", title: "Заказ-наряды", icon: ClipboardList, ready: true },
  { key: "lifts", title: "Подъёмники", icon: Gauge, ready: true },
  { key: "tyres", title: "Шиномонтаж", icon: CalendarDays, ready: true },
  { key: "inventory", title: "Запчасти и склад", icon: Package, ready: true },
  { key: "donors", title: "Авторазбор", icon: Wrench, ready: true },
  { key: "suppliers", title: "Закупки", icon: ShoppingCart, ready: true },
  { key: "personnel", title: "Персонал", icon: Users, ready: true },
  { key: "cash", title: "Касса", icon: CreditCard, ready: true },
  { key: "reports", title: "Отчёты", icon: BarChart3, ready: true },
  { key: "settings", title: "Настройки", icon: Settings, ready: true },
];
function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "Непредвиденная ошибка.";
}
function Notice({ children, type = "error" }: { children: ReactNode; type?: "error" | "info" }) {
  return <div className={"notice " + type} role={type === "error" ? "alert" : "status"}>{children}</div>;
}
function Auth({ afterLogin }: { afterLogin: () => Promise<void> }) {
  type Mode = "login" | "signup" | "forgot" | "verify" | "reset";
  const params = new URLSearchParams(window.location.search);
  const linkedMode: Mode = params.get("account_action")==="verify"?"verify":
                            params.get("account_action")==="reset"?"reset":"login";
  const [mode,setMode] = useState<Mode>(linkedMode);
  const [enabled,setEnabled] = useState(false);
  const [email,setEmail] = useState("");
  const [password,setPassword] = useState("");
  const [submitting,setSubmitting] = useState(false);
  const [error,setError] = useState("");
  const [notice,setNotice] = useState("");
  const uid=params.get("uid")??"";
  const token=params.get("token")??"";
  useEffect(()=>{
    let alive=true;
    api<{email_signup_enabled:boolean}>("auth/capabilities")
      .then(x=>{if(alive)setEnabled(x.email_signup_enabled);})
      .catch(()=>{if(alive)setEnabled(false);});
    return ()=>{alive=false;};
  },[]);
  function changeMode(next:Mode){
    setMode(next);setError("");setNotice("");setPassword("");
  }
  function completeLink(){
    window.history.replaceState({}, "", window.location.pathname);
    changeMode("login");
  }
  async function submit(e:FormEvent){
    e.preventDefault();setSubmitting(true);setError("");setNotice("");
    try{
      if(mode==="login"){
        await api("auth/login",{method:"POST",data:{email,password}});
        await afterLogin();
      }else if(mode==="signup"){
        const data=await api<{message_ru:string}>("auth/signup-email",
          {method:"POST",data:{email,password}});
        setNotice(data.message_ru);
      }else if(mode==="forgot"){
        const data=await api<{message_ru:string}>("auth/password/recovery",
          {method:"POST",data:{email}});
        setNotice(data.message_ru);
      }else if(mode==="verify"){
        await api("auth/email/verify",{method:"POST",data:{uid,token,password}});
        setNotice("Адрес подтверждён. Можно войти.");
        window.history.replaceState({}, "", window.location.pathname);
        setMode("login");
      }else if(mode==="reset"){
        await api("auth/password/confirm",{method:"POST",data:{uid,token,password}});
        setNotice("Пароль изменён. Войдите с новым паролем.");
        window.history.replaceState({}, "", window.location.pathname);
        setMode("login");
      }
    }catch(err){setError(errorText(err));}
    finally{setSubmitting(false);}
  }
  const captions:Record<Mode,string>={
    login:"Вход в систему",signup:"Создать учётную запись",forgot:"Восстановить пароль",
    verify:"Подтвердить электронную почту",reset:"Установить новый пароль"
  };
  return <div className="auth-layout">
    <aside className="auth-intro">
      <div className="brand light"><span className="brand-mark"><Wrench size={21}/></span> CRM <strong>Автосервис</strong></div>
      <h1>Управляйте сервисом. Контролируйте операции.</h1>
      <p>Клиенты, автомобили, ремонт, запчасти и авторазбор — в одной системе.</p>
      <div className="auth-features"><span><ShieldCheck size={17}/> Изоляция данных компаний</span>
        <span><Activity size={17}/> Учёт операций и изменений</span></div>
    </aside>
    <main className="auth-main"><div className="login-card">
      <div className="eyebrow">Доступ в CRM</div><h2>{captions[mode]}</h2>
      {mode==="signup"&&<p className="muted">После регистрации подтвердите электронную почту по ссылке из письма.</p>}
      {mode==="forgot"&&<p className="muted">Если адрес есть в системе, мы отправим ссылку для восстановления.</p>}
      {mode==="verify"&&<p className="muted">Подтверждение адреса требуется для безопасного входа.</p>}
      <form onSubmit={submit}>
        {["login","signup","forgot"].includes(mode)&&<label>Электронная почта
          <input type="email" autoComplete="email" required value={email}
            onChange={e=>setEmail(e.target.value)} placeholder="name@company.ru"/>
        </label>}
        {["login","signup","reset","verify"].includes(mode)&&<label>
          {mode==="reset"?"Новый пароль":mode==="verify"?"Пароль, заданный при регистрации":"Пароль"}
          <input type="password" minLength={12}
            autoComplete={["login","verify"].includes(mode)?"current-password":"new-password"}
            required value={password} onChange={e=>setPassword(e.target.value)}
            placeholder="Не менее 12 символов"/>
        </label>}
        {error&&<Notice>{error}</Notice>}
        {notice&&<Notice type="info">{notice}</Notice>}
        <button className="primary wide" disabled={submitting||(["signup","forgot"].includes(mode)&&!enabled)}>
          {submitting?"Сохранение…":
            mode==="login"?"Войти":mode==="signup"?"Отправить письмо":
            mode==="forgot"?"Восстановить доступ":mode==="verify"?"Подтвердить адрес":"Сменить пароль"}
        </button>
      </form>
      <div className="quick-actions" style={{marginTop:15}}>
        {mode==="login"&&enabled&&<>
          <button type="button" onClick={()=>changeMode("signup")}>Регистрация</button>
          <button type="button" onClick={()=>changeMode("forgot")}>Забыли пароль?</button>
        </>}
        {mode!=="login"&&<button type="button" onClick={completeLink}>Вернуться ко входу</button>}
      </div>
      {!enabled&&["signup","forgot","login"].includes(mode)&&
        <Notice type="info">Самостоятельная регистрация включается после настройки защищённой отправки писем.</Notice>}
    </div></main>
  </div>;
}
function CreateOrganization({ onCreated }: { onCreated: () => Promise<void> }) {
  const [name, setName] = useState(""); const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try { await api("organizations", { method: "POST", data: { name } }); await onCreated(); }
    catch(err) { setError(errorText(err)); } finally { setBusy(false); }
  }
  return <main className="empty-workspace"><div className="card create-org">
    <span className="circle"><Wrench/></span><h1>Создайте рабочее пространство</h1>
    <p className="muted">Первый шаг: организация и основной филиал. Данные других компаний будут недоступны.</p>
    <form onSubmit={save}><label>Название автосервиса<input value={name} onChange={e=>setName(e.target.value)} minLength={2} maxLength={200} required placeholder="Например, Автоцентр Восток"/></label>
      {error && <Notice>{error}</Notice>}<button disabled={busy} className="primary wide">{busy?"Сохраняем…":"Создать организацию"}</button></form>
  </div></main>;
}
function allowedArea(area:Area, role:string):boolean{
 const roles:Record<Area,string[]>={
  dashboard:["owner","manager","adviser","mechanic","stock","cashier","viewer"],
  customers:["owner","manager","adviser","viewer"],
  vehicles:["owner","manager","adviser","mechanic","stock","viewer"],
  orders:["owner","manager","adviser","mechanic","viewer"],
  lifts:["owner","manager","adviser","mechanic","viewer"],
  tyres:["owner","manager","adviser","mechanic","viewer"],
  inventory:["owner","manager","stock","adviser","viewer"],
  donors:["owner","manager","stock","adviser","viewer"],
  suppliers:["owner","manager","stock","adviser","viewer"],
  personnel:["owner","manager"],
  cash:["owner","manager","cashier","viewer"],
  reports:["owner","manager","viewer"],
  settings:["owner","manager"],
 };
 return roles[area].includes(role);
}
function Dashboard({role,navigate}:{role:string;navigate:(s:Area)=>void}){
 const links=navigation.filter(x=>x.key!=="dashboard"&&x.ready&&allowedArea(x.key,role));
 return <><div className="page-lead"><div>
   <div className="eyebrow">Моё рабочее пространство</div>
   <h1>Быстрый доступ к задачам</h1>
   <p className="muted">Выберите рабочий раздел. Доступ зависит от роли и филиала.</p>
 </div></div>
 <section className="card action-card"><h2>Доступные разделы</h2>
  <div className="quick-actions">{links.map(x=><button key={x.key}
   onClick={()=>navigate(x.key)}>{x.title}</button>)}</div>
 </section></>;
}
function retryKey(ref: { current: { signature: string; key: string } | null }, data: unknown): string {
  const signature = JSON.stringify(data);
  if (!ref.current || ref.current.signature !== signature) {
    ref.current = { signature, key: crypto.randomUUID() };
  }
  return ref.current.key;
}
function Customers({ organization, items, refresh, canEdit }: { organization:string; items:Customer[]; refresh:()=>Promise<void>; canEdit:boolean }) {
  const [adding,setAdding]=useState(false); const [query,setQuery]=useState("");
  const [name,setName]=useState(""); const [kind,setKind]=useState<"person"|"company">("person");
  const [phone,setPhone]=useState(""); const [email,setEmail]=useState(""); const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const pending=useRef<{signature:string;key:string}|null>(null);
  const filtered=items.filter(x=>[x.name,x.phone,x.email].some(v=>v.toLowerCase().includes(query.toLowerCase())));
  async function create(e:FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      const data={name,kind,phone,email};
      await api("customers", { method:"POST", organization,
        idempotencyKey:retryKey(pending,data), data });
      pending.current=null;
      setAdding(false);setName("");setPhone("");setEmail("");await refresh();
    } catch(err){setError(errorText(err));}finally{setBusy(false);}
  }
  return <><div className="page-lead"><div><div className="eyebrow">CRM</div><h1>Клиенты</h1>
    <p className="muted">Единая база клиентов автосервиса и истории обслуживания.</p></div>
    {canEdit&&<button className="primary" onClick={()=>{setAdding(true);setError("");}}><Plus size={17}/> Добавить клиента</button>}</div>
    <section className="card table-card"><div className="table-head"><h2>Список клиентов</h2>
      <label className="search-input"><Search size={17}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Поиск по имени, телефону, почте" aria-label="Поиск клиентов"/></label></div>
      <div className="table-scroll"><table><thead><tr><th>Клиент</th><th>Контакты</th><th>Тип</th></tr></thead>
      <tbody>{filtered.map(c=><tr key={c.id}><td><strong>{c.name}</strong></td><td>{c.phone || c.email || "—"}</td><td>{c.kind==="company"?"Организация":"Физлицо"}</td></tr>)}</tbody></table>
      {filtered.length===0&&<p className="table-empty">Клиенты не найдены. Создайте первую карточку или измените поиск.</p>}</div></section>
    {adding&&<div className="modal-backdrop" role="presentation"><div className="modal" role="dialog" aria-modal="true" aria-labelledby="customer-title">
      <div className="modal-heading"><h2 id="customer-title">Новый клиент</h2><button className="icon-button" aria-label="Закрыть" onClick={()=>setAdding(false)}><X/></button></div>
      <form onSubmit={create}><label>Тип<select value={kind} onChange={e=>setKind(e.target.value as "person"|"company")}><option value="person">Физическое лицо</option><option value="company">Организация</option></select></label>
      <label>Имя / организация<input autoFocus value={name} onChange={e=>setName(e.target.value)} minLength={2} maxLength={200} required/></label>
      <label>Телефон<input type="tel" value={phone} onChange={e=>setPhone(e.target.value)} placeholder="+7 999 123-45-67"/></label>
      <label>Электронная почта<input type="email" value={email} onChange={e=>setEmail(e.target.value)}/></label>
      {error&&<Notice>{error}</Notice>}
      <div className="modal-footer"><button type="button" className="secondary" onClick={()=>setAdding(false)}>Отменить</button>
        <button disabled={busy} className="primary">{busy?"Сохранение…":"Создать клиента"}</button></div></form>
    </div></div>}
  </>;
}
function Vehicles({ organization, vehicles, customers, refresh, canEdit }: {
  organization:string; vehicles:Vehicle[]; customers:Customer[];refresh:()=>Promise<void>;canEdit:boolean
}) {
  const [adding,setAdding]=useState(false);const [query,setQuery]=useState("");
  const [make,setMake]=useState("");const [model,setModel]=useState("");
  const [vin,setVin]=useState("");const [plate,setPlate]=useState("");
  const [owner,setOwner]=useState("");const [error,setError]=useState("");const [busy,setBusy]=useState(false);
  const pending=useRef<{signature:string;key:string}|null>(null);
  const filtered=vehicles.filter(v=>[v.make,v.model,v.plate,v.vin].some(value=>value.toLowerCase().includes(query.toLowerCase())));
  async function create(e:FormEvent){
    e.preventDefault();setError("");setBusy(true);
    try {
      const data={make,model,vin,plate,...(owner?{owner_id:owner}:{})};
      await api("vehicles",{method:"POST",organization,idempotencyKey:retryKey(pending,data),data});
      pending.current=null;
      setAdding(false);setMake("");setModel("");setVin("");setPlate("");setOwner("");await refresh();
    }catch(err){setError(errorText(err));}finally{setBusy(false);}
  }
  return <><div className="page-lead"><div><div className="eyebrow">Автопарк клиентов</div><h1>Автомобили</h1>
      <p className="muted">VIN, госномер и связь с клиентом. История владельцев сохраняется.</p></div>
      {canEdit&&<button className="primary" onClick={()=>{setAdding(true);setError("");}}><Plus size={17}/> Добавить автомобиль</button>}</div>
      <section className="card table-card"><div className="table-head"><h2>Автомобили</h2>
        <label className="search-input"><Search size={17}/><input aria-label="Поиск автомобилей" value={query}
        onChange={e=>setQuery(e.target.value)} placeholder="Марка, модель, VIN или номер"/></label></div>
        <div className="table-scroll"><table><thead><tr><th>Автомобиль</th><th>Госномер</th><th>VIN</th><th>Владелец</th></tr></thead>
        <tbody>{filtered.map(v=><tr key={v.id}><td><strong>{v.make} {v.model}</strong></td><td>{v.plate||"—"}</td>
          <td className="mono">{v.vin||"—"}</td><td>{customers.find(c=>c.id===v.current_owner)?.name||"Не указан"}</td></tr>)}</tbody></table>
        {filtered.length===0&&<p className="table-empty">Автомобили не найдены.</p>}</div></section>
      {adding&&<div className="modal-backdrop" role="presentation"><div className="modal" role="dialog" aria-modal="true" aria-labelledby="vehicle-title">
        <div className="modal-heading"><h2 id="vehicle-title">Новый автомобиль</h2><button className="icon-button" aria-label="Закрыть" onClick={()=>setAdding(false)}><X/></button></div>
        <form onSubmit={create}><div className="form-grid"><label>Марка<input autoFocus required maxLength={100} value={make} onChange={e=>setMake(e.target.value)} placeholder="Toyota"/></label>
        <label>Модель<input required maxLength={100} value={model} onChange={e=>setModel(e.target.value)} placeholder="Camry"/></label></div>
        <label>VIN (если известен)<input className="mono" maxLength={17} value={vin} onChange={e=>setVin(e.target.value.toUpperCase())} placeholder="17 символов"/></label>
        <label>Госномер<input maxLength={20} value={plate} onChange={e=>setPlate(e.target.value.toUpperCase())}/></label>
        <label>Владелец<select value={owner} onChange={e=>setOwner(e.target.value)}><option value="">Не указан</option>
          {customers.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
        {error&&<Notice>{error}</Notice>}<div className="modal-footer"><button type="button" className="secondary" onClick={()=>setAdding(false)}>Отменить</button>
        <button className="primary" disabled={busy}>{busy?"Сохраняем…":"Создать автомобиль"}</button></div></form>
      </div></div>}
    </>;
}
function ComingSoon({ name }: { name:string }) {
  return <div className="coming-soon"><span className="circle"><Wrench/></span>
    <h1>{name}</h1><p>Этот раздел находится в разработке. Учётные операции появятся после проверки серверной логики и тестов.</p>
    <Notice type="info">В настоящей системе не используются фиктивные записи, оплаты или остатки.</Notice></div>;
}
export default function App(){
  const [session,setSession]=useState<SessionUser|null>(null);
  const [loading,setLoading]=useState(true);
  const [pendingInvite,setPendingInvite]=useState(()=>new URLSearchParams(window.location.search).get("staff_invite")??"");
  const [organizationId,setOrganizationId]=useState("");
  const [area,setArea]=useState<Area>("dashboard");
  const [customers,setCustomers]=useState<Customer[]>([]);
  const [vehicles,setVehicles]=useState<Vehicle[]>([]);
  const [dataLoading,setDataLoading]=useState(false);
  const [error,setError]=useState("");const [menuOpen,setMenuOpen]=useState(false);
  const organizations=session?.organizations??[];
  const activeOrg:Organization|undefined=useMemo(()=>organizations.find(o=>o.id===organizationId)??organizations[0],[organizations,organizationId]);
  const loadSession=useCallback(async()=>{
    try{
      const user=await api<SessionUser>("auth/me");
      setSession(user);setOrganizationId(prev=>user.organizations.some(o=>o.id===prev)?prev:user.organizations[0]?.id??"");
    }catch(err){if(err instanceof ApiError&&(err.status===401||err.status===403)){setSession(null);}
      else setError(errorText(err));}
    finally{setLoading(false);}
  },[]);
  useEffect(()=>{void loadSession();},[loadSession]);
  const refreshData=useCallback(async()=>{
    if(!activeOrg)return;
    setDataLoading(true);setError("");
    try{
      const role=activeOrg.role;
      const canCustomers=["owner","manager","adviser","viewer"].includes(role);
      const canVehicles=canCustomers||["mechanic","stock"].includes(role);
      const [c,v]=await Promise.all([
        canCustomers ? api<Customer[]>("customers",{organization:activeOrg.id}) : Promise.resolve([] as Customer[]),
        canVehicles ? api<Vehicle[]>("vehicles",{organization:activeOrg.id}) : Promise.resolve([] as Vehicle[]),
      ]);
      setCustomers(c);setVehicles(v);
    }catch(err){setError(errorText(err));}
    finally{setDataLoading(false);}
  },[activeOrg?.id]);
  useEffect(()=>{void refreshData();},[refreshData]);
  async function logOut(){try{await api("auth/logout",{method:"POST"});}finally{
    setSession(null);setCustomers([]);setVehicles([]);setArea("dashboard");
  }}
  function navigate(next:Area){
    if(activeOrg&&allowedArea(next,activeOrg.role))setArea(next);
    setMenuOpen(false);
  }
  useEffect(()=>{
    if(activeOrg&&!allowedArea(area,activeOrg.role))setArea("dashboard");
  },[activeOrg?.id,activeOrg?.role,area]);
  if(loading)return <div className="loading"><Activity size={24}/> Загрузка CRM…</div>;
  if(!session)return <Auth afterLogin={loadSession}/>;
  if(pendingInvite)return <AcceptInvitation token={pendingInvite}
    onDecline={()=>{window.history.replaceState({},"",window.location.pathname);setPendingInvite("");}}
    onAccepted={async()=>{window.history.replaceState({},"",window.location.pathname);
      setPendingInvite("");await loadSession();}}/>;
  if(!activeOrg)return <CreateOrganization onCreated={loadSession}/>;
  const selected=navigation.find(n=>n.key===area);
  return <div className="app-shell">
    {menuOpen&&<button className="mobile-scrim" onClick={()=>setMenuOpen(false)} aria-label="Закрыть меню"/>}
    <aside className={"sidebar "+(menuOpen?"open":"")}>
      <div className="brand"><span className="brand-mark"><Wrench size={20}/></span><span>CRM <strong>Автосервис</strong></span></div>
      <div className="workspace-switch"><span className="avatar-org">{activeOrg.name.slice(0,1).toUpperCase()}</span>
        <div className="workspace-name"><strong>{activeOrg.name}</strong><small>Роль: {activeOrg.role}</small></div><ChevronDown size={15}/></div>
      {organizations.length>1&&<label className="org-select-label">Организация<select value={activeOrg.id} onChange={e=>setOrganizationId(e.target.value)}>
        {organizations.map(o=><option key={o.id} value={o.id}>{o.name}</option>)}</select></label>}
      <div className="menu-heading">РАБОЧЕЕ ПРОСТРАНСТВО</div>
      <nav aria-label="Разделы CRM">{navigation.filter(item=>allowedArea(item.key,activeOrg.role)).map(item=>{
        const Icon=item.icon;return <button key={item.key} aria-current={area===item.key?"page":undefined}
          className={"nav-link "+(area===item.key?"active":"")} onClick={()=>navigate(item.key)}>
          <Icon size={18}/><span>{item.title}</span>{!item.ready&&<span className="lock-mark" title="В разработке">·</span>}</button>;
      })}</nav>
      <div className="sidebar-bottom"><button className="nav-link" onClick={()=>navigate("settings")}><CircleHelp size={18}/> Справка</button>
        <button className="nav-link" onClick={()=>void logOut()}><LogOut size={18}/> Выйти</button></div>
    </aside>
    <div className="main-column">
      <header className="topbar"><div className="topbar-left"><button className="icon-button mobile-toggle" aria-label="Открыть меню" onClick={()=>setMenuOpen(true)}><Menu/></button>
        <span className="breadcrumbs">CRM <span>/</span> {selected?.title}</span></div>
        <div className="topbar-right"><span className="health-badge"><CheckCircle2 size={15}/> Тестовая сборка</span>
          <span className="user-pill">{session.email.slice(0,1).toUpperCase()}</span></div></header>
      <main key={activeOrg.id} className="content" id="main">
        {error&&<Notice>{error}</Notice>}
        {area==="dashboard"?(
           ["owner","manager","viewer"].includes(activeOrg.role)
            ?<OwnerDashboard organization={activeOrg.id} onNavigate={navigate}/>
            :<Dashboard role={activeOrg.role} navigate={navigate}/>
         ):
         area==="customers"?<Customers organization={activeOrg.id} items={customers} refresh={refreshData} canEdit={["owner","manager","adviser"].includes(activeOrg.role)}/>:
         area==="vehicles"?<Vehicles organization={activeOrg.id} vehicles={vehicles} customers={customers} refresh={refreshData} canEdit={["owner","manager","adviser"].includes(activeOrg.role)}/>:
         area==="settings"?<SubscriptionPage organization={activeOrg.id} role={activeOrg.role}/>:
         area==="personnel"?<Staff organization={activeOrg.id} role={activeOrg.role}/>:
         area==="tyres"?<TireStorage organization={activeOrg.id} role={activeOrg.role} customers={customers} vehicles={vehicles}/>:
         area==="cash"&&["owner","manager","cashier","viewer"].includes(activeOrg.role)?<CashDesk organization={activeOrg.id} role={activeOrg.role}/>:
         area==="donors"?<Dismantling organization={activeOrg.id} role={activeOrg.role}/>:
         area==="reports"&&["owner","manager","viewer"].includes(activeOrg.role)?<Reports organization={activeOrg.id}/>:
         (area==="inventory"||area==="suppliers")?<Inventory organization={activeOrg.id} role={activeOrg.role}/>:
         area==="orders"?<WorkOrders organization={activeOrg.id} role={activeOrg.role} customers={customers} vehicles={vehicles}/>:
         area==="lifts"?<Schedule organization={activeOrg.id} role={activeOrg.role} customers={customers} vehicles={vehicles}/>:
         <ComingSoon name={selected?.title??"Раздел"}/>}
      </main>
    </div>
  </div>;
}
