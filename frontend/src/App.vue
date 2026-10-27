<template>
  <div v-if="!token" class="login-page">
    <section class="login-scene">
      <div class="brand"><span class="mark"><ScanSearch :size="22" /></span><span><b>TraceRAG</b><small>KNOWLEDGE INTELLIGENCE</small></span></div>
      <div class="scene-copy"><p class="eyebrow">GROUNDED AI WORKSPACE</p><h1>答案有来源，过程可追踪。</h1><p>面向企业支持团队的知识检索、证据引用与质量评测工作台。</p></div>
      <div class="scene-metrics"><span><b>12</b>知识文档</span><span><b>4</b>最大引用数</span><span><b>3</b>执行阶段</span></div>
    </section>
    <section class="login-panel"><form @submit.prevent="login"><span class="login-badge"><LockKeyhole :size="20" /></span><h2>进入知识工作台</h2><p>使用演示账号访问完整数据。</p><label>账号<input v-model="credentials.username" /></label><label>密码<input v-model="credentials.password" type="password" /></label><button class="primary full" :disabled="loading"><LogIn :size="16" />{{loading?'登录中':'安全登录'}}</button><div class="demo"><KeyRound :size="14" />admin / admin123</div><p v-if="error" class="error">{{error}}</p></form></section>
  </div>

  <div v-else class="shell">
    <aside :class="{open:menuOpen}"><div class="brand"><span class="mark"><ScanSearch :size="20" /></span><span><b>TraceRAG</b><small>知识智能工作台</small></span></div><nav>
      <button v-for="item in nav" :key="item.id" :class="{active:tab===item.id}" @click="tab=item.id"><component :is="item.icon" :size="17" />{{item.name}}</button>
    </nav><div class="aside-foot"><div class="model"><i></i><span><b>Grounded runtime</b><small>引用校验已开启</small></span></div><div class="profile"><span>林</span><p><b>林然</b><small>Workspace owner</small></p><button title="退出" @click="logout"><LogOut :size="15" /></button></div></div></aside>
    <div v-if="menuOpen" class="mask" @click="menuOpen=false"></div>
    <main><header><button class="menu" @click="menuOpen=true"><Menu :size="18" /></button><div class="crumb"><span>TraceRAG</span><ChevronRight :size="14" /><b>{{pageTitle}}</b></div><div class="header-actions"><span class="production"><i></i>Production</span><a href="https://github.com/peixi2/tracerag" target="_blank"><Code2 :size="16" />GitHub</a></div></header>
      <div class="content"><div class="page-head"><div><p class="eyebrow">{{pageEyebrow}}</p><h1>{{pageTitle}}</h1><p>{{pageDescription}}</p></div><button class="secondary" @click="refresh"><RefreshCw :size="15" />刷新</button></div>

        <template v-if="tab==='overview'">
          <section class="metrics"><article><span>知识文档<Library :size="17" /></span><strong>{{overview.documents||0}}</strong><small>{{Object.keys(overview.categories||{}).length}} 个知识域</small></article><article><span>支持工单<MessagesSquare :size="17" /></span><strong>{{overview.tickets||0}}</strong><small>{{overview.openTickets||0}} 条处理中</small></article><article><span>查询轨迹<Route :size="17" /></span><strong>{{overview.queryTraces||0}}</strong><small>持久化 traceId</small></article><article><span>最近 Recall@4<Target :size="17" /></span><strong>{{percent(latestEval?.recallAt4)}}</strong><small>{{latestEval?.cases||6}} 条评测集</small></article></section>
          <section class="overview-grid"><article class="panel"><div class="panel-head"><h2>知识域覆盖</h2><span>实时统计</span></div><div class="category-list"><div v-for="(count,name) in overview.categories" :key="name"><span>{{name}}</span><div><i :style="{width:(count/maxCategory*100)+'%'}"></i></div><b>{{count}}</b></div></div></article><article class="panel"><div class="panel-head"><h2>最近查询</h2><button @click="tab='copilot'">打开 Copilot <ArrowRight :size="13" /></button></div><div class="trace-list"><div v-for="t in overview.recentTraces" :key="t.traceId"><span class="trace-dot"></span><span><b>{{t.question}}</b><small>{{t.mode}} · {{t.sourceCount}} 来源 · {{t.latencyMs}}ms</small></span><em>{{Math.round(t.confidence*100)}}%</em></div><p v-if="!overview.recentTraces?.length" class="empty">暂无查询记录</p></div></article></section>
          <section class="panel tickets"><div class="panel-head"><h2>客户支持现场</h2><span>模拟真实使用痕迹</span></div><div class="ticket-row" v-for="t in overview.recentTickets" :key="t.key"><span class="priority" :class="t.priority.toLowerCase()">{{t.priority}}</span><span><b>{{t.title}}</b><small>{{t.key}} · {{t.assignee}}</small></span><em :class="t.status.toLowerCase()">{{statusText[t.status]}}</em></div></section>
        </template>

        <template v-else-if="tab==='knowledge'">
          <section class="knowledge-toolbar panel"><div class="search"><Search :size="15" /><input v-model="docQuery" placeholder="搜索标题、编号、分类或正文" /></div><button class="primary" @click="showCreate=!showCreate"><Plus :size="15" />新增文档</button></section>
          <section v-if="showCreate" class="create-panel panel"><div class="panel-head"><h2>新增知识文档</h2><button title="关闭" @click="showCreate=false"><X :size="16" /></button></div><div class="create-grid"><label>标题<input v-model="newDoc.title" /></label><label>分类<input v-model="newDoc.category" /></label><label class="wide">正文<textarea v-model="newDoc.content" rows="5"></textarea></label><button class="primary" @click="createDocument"><Save :size="15" />发布文档</button></div></section>
          <section class="doc-grid"><article v-for="d in filteredDocs" :key="d.key" class="doc-card"><div><span class="doc-icon"><FileText :size="17" /></span><span class="tag">{{d.category}}</span></div><h2>{{d.title}}</h2><p>{{d.content}}</p><footer><span>{{d.key}}</span><span>{{d.owner}} · {{date(d.updatedAt)}}</span></footer></article></section>
        </template>

        <template v-else-if="tab==='copilot'">
          <section class="copilot-layout"><article class="panel chat-panel"><div class="suggestions"><button v-for="q in suggestions" @click="question=q">{{q}}</button></div><div class="chat"><div class="assistant-msg"><label>TraceRAG Copilot</label><p>我会检索知识库和支持工单，并为每个结论返回可点击来源。</p></div><div v-if="result" class="user-msg"><label>你的问题</label><p>{{lastQuestion}}</p></div><div v-if="result" class="assistant-msg"><label>回答 · {{result.mode}}</label><p>{{result.answer}}</p><footer><span><ShieldCheck :size="13" />置信度 {{Math.round(result.confidence*100)}}%</span><span><Fingerprint :size="13" />{{result.traceId}}</span></footer></div></div><div class="ask-box"><input v-model="question" @keyup.enter="askQuestion" placeholder="输入产品、故障或流程问题" /><button title="发送" :disabled="asking" @click="askQuestion"><Send :size="17" /></button></div></article>
            <aside class="copilot-side"><article class="panel"><div class="panel-head"><h2>证据来源</h2><span>{{result?.sources?.length||0}} / 4</span></div><div class="source-list"><div v-for="s in result?.sources" :key="s.key"><span><b>{{s.key}}</b><em>{{Math.round(s.score*100)}}%</em></span><h3>{{s.title}}</h3><p>{{s.snippet}}</p></div><p v-if="!result" class="empty">提问后显示引用证据</p></div></article><article class="panel"><div class="panel-head"><h2>执行轨迹</h2><span>{{result?.latencyMs||0}}ms</span></div><div class="pipeline"><div v-for="stage in result?.trace" :key="stage.stage"><i></i><span><b>{{stage.stage}} <em>{{stage.durationMs}}ms</em></b><small>{{stage.detail}}</small></span></div><p v-if="!result" class="empty">提问后显示 3 阶段轨迹</p></div></article></aside>
          </section>
        </template>

        <template v-else>
          <section class="eval-hero"><div><p class="eyebrow">RETRIEVAL QUALITY GATE</p><h2>离线评测集</h2><p>每次运行都在固定问题集上计算 Recall@4、MRR 与引用覆盖率。</p></div><button class="primary" :disabled="evaluating" @click="runEval"><Play :size="15" />{{evaluating?'运行中':'运行评测'}}</button></section>
          <section class="eval-metrics"><article><span>Recall@4</span><strong>{{percent(latestEval?.recallAt4)}}</strong><small>正确文档进入前四</small></article><article><span>MRR</span><strong>{{percent(latestEval?.mrr)}}</strong><small>正确文档排序质量</small></article><article><span>引用覆盖率</span><strong>{{percent(latestEval?.citationCoverage)}}</strong><small>回答绑定来源</small></article></section>
          <section class="panel eval-history"><div class="panel-head"><h2>评测运行记录</h2><span>数据库持久化</span></div><div v-for="run in overview.evalRuns" :key="run.traceId" class="eval-row"><span class="eval-icon"><FlaskConical :size="16" /></span><span><b>{{run.traceId}}</b><small>{{dateTime(run.createdAt)}} · {{run.cases}} cases</small></span><span>Recall@4 <b>{{percent(run.recallAt4)}}</b></span><span>MRR <b>{{percent(run.mrr)}}</b></span><em>PASS</em></div><p v-if="!overview.evalRuns?.length" class="empty">点击“运行评测”生成第一条记录</p></section>
        </template>
        <p v-if="toast" class="toast">{{toast}}</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, markRaw, onMounted, reactive, ref, watch } from 'vue'
import axios from 'axios'
import { ArrowRight, BookOpenText, ChevronRight, Code2, FileText, Fingerprint, FlaskConical, Gauge, KeyRound, Library, LockKeyhole, LogIn, LogOut, Menu, MessagesSquare, Play, Plus, RefreshCw, Route, Save, ScanSearch, Search, Send, ShieldCheck, Sparkles, Target, X } from '@lucide/vue'

const nav=[{id:'overview',name:'智能概览',icon:markRaw(Gauge)},{id:'knowledge',name:'知识库',icon:markRaw(BookOpenText)},{id:'copilot',name:'知识 Copilot',icon:markRaw(Sparkles)},{id:'evaluation',name:'质量评测',icon:markRaw(FlaskConical)}]
const token=ref(localStorage.getItem('tracerag_token')||''),tab=ref('overview'),menuOpen=ref(false),loading=ref(false),error=ref(''),toast=ref('')
const overview=ref({categories:{},recentTickets:[],recentTraces:[],evalRuns:[]}),documents=ref([]),credentials=reactive({username:'admin',password:'admin123'})
const docQuery=ref(''),showCreate=ref(false),newDoc=reactive({title:'',category:'',content:''}),question=ref(''),lastQuestion=ref(''),asking=ref(false),evaluating=ref(false),result=ref(null)
const suggestions=['SSO 登录提示 invalid_redirect_uri 怎么处理？','Webhook 重复消费应该如何避免？','怎样降低知识助手幻觉？','API 返回 429 后该怎么重试？']
const statusText={IN_PROGRESS:'处理中',WAITING_CUSTOMER:'等待客户',RESOLVED:'已解决'}
const pageTitle=computed(()=>({overview:'智能概览',knowledge:'知识库',copilot:'知识 Copilot',evaluation:'质量评测'})[tab.value])
const pageEyebrow=computed(()=>({overview:'KNOWLEDGE OPERATIONS',knowledge:'CURATED SOURCES',copilot:'GROUNDED ANSWERS',evaluation:'EVALUATION LAB'})[tab.value])
const pageDescription=computed(()=>({overview:'追踪知识覆盖、客户问题和 AI 查询质量。',knowledge:'维护可检索、可引用且有责任人的企业知识。',copilot:'基于实时资料回答，并展示来源、置信度和执行轨迹。',evaluation:'用固定数据集持续验证检索召回与引用完整性。'})[tab.value])
const latestEval=computed(()=>overview.value.evalRuns?.[0]),maxCategory=computed(()=>Math.max(1,...Object.values(overview.value.categories||{})))
const filteredDocs=computed(()=>documents.value.filter(d=>`${d.key} ${d.title} ${d.category} ${d.content}`.toLowerCase().includes(docQuery.value.toLowerCase())))
const api=axios.create({baseURL:'/api'});api.interceptors.request.use(c=>{if(token.value)c.headers.Authorization=`Bearer ${token.value}`;return c});api.interceptors.response.use(r=>r,e=>{if([401,403].includes(e.response?.status))logout();return Promise.reject(e)})
async function login(){loading.value=true;error.value='';try{const {data}=await api.post('/auth/login',credentials);token.value=data.token;localStorage.setItem('tracerag_token',token.value);await refresh()}catch(e){error.value=e.response?.data?.detail||'登录失败'}finally{loading.value=false}}
function logout(){token.value='';localStorage.removeItem('tracerag_token')}
async function refresh(){try{const [o,d]=await Promise.all([api.get('/overview'),api.get('/documents')]);overview.value=o.data;documents.value=d.data}catch(e){toast.value=e.response?.data?.detail||'加载失败'}}
async function askQuestion(){if(!question.value.trim()||asking.value)return;asking.value=true;lastQuestion.value=question.value;try{const {data}=await api.post('/copilot/ask',{question:question.value});result.value=data;await refresh()}catch(e){toast.value=e.response?.data?.detail||'查询失败'}finally{asking.value=false}}
async function runEval(){evaluating.value=true;try{await api.post('/evaluations/run');toast.value='评测完成，结果已保存';await refresh()}catch(e){toast.value=e.response?.data?.detail||'评测失败'}finally{evaluating.value=false;setTimeout(()=>toast.value='',2400)}}
async function createDocument(){try{await api.post('/documents',newDoc);Object.assign(newDoc,{title:'',category:'',content:''});showCreate.value=false;toast.value='文档已发布并进入检索库';await refresh()}catch(e){toast.value=e.response?.data?.detail?.[0]?.msg||e.response?.data?.detail||'发布失败'}setTimeout(()=>toast.value='',2400)}
const percent=v=>v==null?'--':`${Math.round(v*100)}%`,date=v=>v?new Date(v).toLocaleDateString('zh-CN'):'-',dateTime=v=>v?new Date(v).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}):'-'
watch(tab,()=>menuOpen.value=false);onMounted(()=>{if(token.value)refresh()})
</script>

