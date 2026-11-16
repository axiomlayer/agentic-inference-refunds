# /// script
# requires-python = ">=3.12"
# dependencies = ["matplotlib>=3.9,<4"]
# ///
"""Build the offline dashboard and GitHub previews from the filed calculation.

Run: uv run build-dashboard.py
No browser, network request, private transcript, or billing mutation is used.
"""
from datetime import datetime
from decimal import Decimal as D, ROUND_HALF_UP
from html import escape
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

P = Path(__file__).parent
R = json.loads((P/'remedy-calculation.json').read_text())
I = json.loads((P/'remedy-inputs.json').read_text())
RATES = json.loads((P/'rates-openai.json').read_text())['models']
OUT = P/'filed'
BASE = 'https://github.com/axiomlayer/agentic-inference-refunds'
CASE = BASE+'/blob/main/examples/2026-11-15-codex-lab-remediation-drift/'
ISSUE = 'https://github.com/openai/codex/issues/61739'
def money(x): return f'${D(x).quantize(D("0.01"),rounding=ROUND_HALF_UP):,}'
def number(x): return f'{int(x):,}'
def compact(x): return f'{x/1e9:.3f} B' if x>=1e9 else f'{x/1e6:.2f} M'
def local(ts): return datetime.fromisoformat(ts.replace('Z','+00:00')).astimezone(ZoneInfo('America/Los_Angeles'))
cutoff = local(I['supplement_end_exclusive'])
stamp = cutoff.strftime('%b %d, %Y · %-I:%M:%S %p PST')
credit = D(R['purchased_credit_component']['requested_usd'])
plan = D(R['allowance_replacement_estimate_usd'])
request = D(R['requested_refund_usd'])
overage = D(R['reporting_and_correction_overage']['standard_api_usd'])
models = R['models']
count = sum(m['responses'] for m in models.values())
tokens = sum(m['processed_tokens'] for m in models.values())
output = sum(m['output_tokens'] for m in models.values())
cross = sum(D(m['standard_api_usd']) for m in models.values())
intervals = R['allowance_intervals']
capacity = R['allowance_capacity']
allowance_count = sum(i['responses'] for i in intervals)
allowance_unpriced = sum(i['unpriced_responses'] for i in intervals)
reset_count = capacity['observed_reset_transitions']
capacity_total = capacity['through_snapshot_promax_percentage_points']
last_capacity = capacity_total - 300
prior_capacity = capacity['prior_pro_percentage_points']
exact_credit = format(credit.normalize(),'f')
exact_plan = format(plan.normalize(),'f')
exact_total = format((credit+plan).normalize(),'f')
lost_credits = format(D(I['requested_credit_loss']).normalize(),'f')
before_balance = format(D(I['observed_credit_start']).normalize(),',f')
after_balance = format(D(I['observed_credit_end']).normalize(),',f')
assert reset_count==3, 'Update the cycle layout if additional resets are captured'
assert not R['refund_approved'], 'Update filing status if a refund is approved'
assert (credit+plan).quantize(D('.01'),rounding=ROUND_HALF_UP)==request
assert sum(D(x['standard_api_usd']) for x in intervals)==plan
assert overage+D(R['other_supplement']['standard_api_usd'])==D(R['supplement']['standard_api_usd'])
assert I['user_confirmed_credit_loss']

COLORS = dict(bg='#191a18',panel='#242621',text='#f4f3ed',muted='#c0c2b7',line='#3b3e35',blue='#599af3',green='#59c8a5',purple='#b1a0ec',amber='#f0c362')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':13,'svg.fonttype':'none','savefig.facecolor':COLORS['bg']})
fig = plt.figure(figsize=(12,16.6),facecolor=COLORS['bg'])
def text(x,y,s,size=13,color='text',weight='normal',ha='left',va='top',**kw):
    return fig.text(x,y,s,fontsize=size,color=COLORS.get(color,color),weight=weight,ha=ha,va=va,**kw)
def panel(x,y,w,h,color='panel',radius=.009):
    fig.add_artist(FancyBboxPatch((x,y),w,h,boxstyle=f'round,pad=0,rounding_size={radius}',transform=fig.transFigure,facecolor=COLORS.get(color,color),edgecolor='none',zorder=0))
def rule(y):
    fig.add_artist(Rectangle((.05,y),.90,.001,transform=fig.transFigure,color=COLORS['line'],zorder=0))
def bar(x,y,w,h,color):
    fig.add_artist(Rectangle((x,y),w,h,transform=fig.transFigure,color=COLORS[color],zorder=1))

text(.05,.972,'What the failed Codex session cost',27,weight='bold')
text(.05,.939,'Credit loss, consumed plan allowance, and the cost of correcting the refund claim.',13,'muted')
text(.05,.919,'FIXED SNAPSHOT  '+stamp,10.5,'muted')
text(.95,.918,'FILED · OPEN · NOT REFUNDED',10.5,'amber',ha='right',weight='bold')
cards=[(money(request),'Calculated compensation request','blue'),(money(credit),'Confirmed credit-loss value','green'),(str(reset_count),'Observed weekly reset transitions','purple'),(money(overage),'Correction overage · included','amber')]
for idx,(value,label,color) in enumerate(cards):
    x=.05+idx*.228
    panel(x,.821,.216,.073)
    text(x+.012,.879,value,27,color,weight='bold')
    text(x+.012,.84,label,9.6,'muted')

text(.05,.799,'How the request adds up',18,weight='bold')
text(.05,.775,money(credit)+' credit component  +  '+money(plan)+' plan replacement estimate  =  '+money(request),14,weight='bold')
bar(.05,.742,.90*float(credit/(credit+plan)),.018,'green')
bar(.05+.90*float(credit/(credit+plan)),.742,.90*float(plan/(credit+plan)),.018,'blue')
text(.05,.734,'Credit decrease × $0.04',11,'green')
text(.95,.734,'Plan estimate includes the '+money(overage)+' correction overage',11,'blue',ha='right')
panel(.05,.663,.90,.055)
text(.063,.707,'ESTIMATE, NOT A VERIFIED BILL',11,'amber',weight='bold')
text(.063,.69,'Per-response funding and speed are unverified; overlap with credit deductions is possible.\nOpenAI must reconcile the allocation. Restoring plan capacity is an alternative to its dollar estimate.',11,'muted',linespacing=1.55)

text(.05,.641,'Plan-period replacement estimates',17,weight='bold')
text(.05,.619,'Model-specific rates applied to recorded responses in active-allowance periods.',11,'muted')
maxcost=max(D(i['standard_api_usd']) for i in intervals)
labels=['Prior pro allowance','Initial promax allowance','After reset 1','After reset 2','After reset 3 · original window','Supplement after original cutoff']
for idx,(i,label) in enumerate(zip(intervals,labels)):
    y=.590-idx*.031
    text(.05,y+.008,label,11.5)
    bar(.355,y-.005,.20*float(D(i['standard_api_usd'])/maxcost),.009,'purple' if idx==5 else 'blue')
    text(.635,y+.008,money(i['standard_api_usd']),12,ha='right',weight='bold')
text(.05,.402,f'{number(allowance_count)} recorded responses; {allowance_unpriced} internal reviews remain unpriced.',10.5,'muted')
text(.635,.401,money(plan)+' total',12,'blue',ha='right',weight='bold')

text(.69,.642,'Allowance consumed',16,weight='bold')
text(.69,.617,'promax · across weekly cycles',10.5,'muted')
for idx,(label,pct) in enumerate([('Initial',100),('Reset 1',100),('Reset 2',100),('Reset 3',last_capacity)]):
    y=.584-idx*.039
    text(.69,y+.014,label,10.5,'muted')
    bar(.69,y-.005,.205,.008,'line')
    bar(.69,y-.005,.205*pct/100,.008,'purple')
    text(.945,y+.010,f'{pct:g}%',11,'purple',ha='right',weight='bold')
text(.69,.423,f'{capacity_total:g} percentage points',13,'purple',weight='bold')
text(.69,.405,f'+ {prior_capacity:g} points of prior pro, separately',10,'muted')
text(.69,.389,'Rounded observations; not equal plan sizes.',9.4,'muted')

rule(.372)
text(.05,.355,'The measured credit loss',17,weight='bold')
text(.05,.329,f'{before_balance}  −  {after_balance}',18,'green',weight='bold')
text(.05,.302,f'= {D(lost_credits):,f} credits × ${I["usd_per_credit"]}',14)
text(.05,.280,f'= ${exact_credit} before rounding',12,'muted')
text(.05,.258,'Owner confirmed this decrease; the earlier 75,000 estimate is superseded.',10.6,'muted')
text(.64,.355,'The correction itself cost',17,weight='bold')
text(.64,.329,money(overage),25,'amber',weight='bold')
text(.64,.299,number(R['reporting_and_correction_overage']['responses'])+' responses · '+compact(R['reporting_and_correction_overage']['processed_tokens'])+' tokens',12,'muted')
text(.64,.278,'Refund audit, incorrect filings, repeated corrections.',10.4,'muted')
text(.64,.260,'Already included in the plan estimate. Counted once.',10.4,'amber')

rule(.238)
text(.05,.222,'Full recorded usage · a separate cross-check',17,weight='bold')
text(.05,.197,f'{number(count)} responses  ·  {compact(tokens)} processed tokens  ·  {compact(output)} output tokens',12,'muted')
text(.95,.222,money(cross),21,'blue',ha='right',weight='bold')
text(.95,.197,'Do not add this to the request.',11,'amber',ha='right')
text(.05,.169,'MODEL',10,'muted',weight='bold')
text(.40,.169,'RESPONSES',10,'muted',weight='bold',ha='right')
text(.72,.169,'INPUT / CACHED / OUTPUT · PER 1M',10,'muted',weight='bold',ha='right')
text(.95,.169,'API VALUE',10,'muted',weight='bold',ha='right')
for idx,(m,label) in enumerate([('gpt-6-astra','Astra'),('gpt-6.1-terra','Terra 6.1'),('gpt-6.1-sol','Sol 6.1'),('codex-auto-review','Internal auto-review')]):
    row=models[m];rate=RATES.get(m);y=.148-idx*.020
    text(.05,y,label,11)
    text(.40,y,number(row['responses']),11,ha='right')
    text(.72,y,' / '.join('$'+str(rate[k]) for k in ['input','cache_read','output']) if rate else 'No verified rate',10.5,'muted',ha='right')
    text(.95,y,money(row['standard_api_usd']) if rate else 'Unpriced',11,ha='right')
rule(.061)
text(.05,.048,'Original window: Nov 15, 11:40:23 AM–7:40:23 PM PST. Supplement ends '+cutoff.strftime('%-I:%M:%S %p')+'.',10,'muted')
text(.05,.032,'Cached input is included; reasoning is already in output. Whole-session dispute ≠ every response proved unauthorized.',9.6,'muted')
text(.05,.016,'OpenAI issue #61739  ·  axiomlayer/agentic-inference-refunds  ·  sources and calculator available on main',9.4,'muted')
fig.savefig(OUT/'cost-chart.png',dpi=160)
fig.savefig(OUT/'cost-chart.svg')
plt.close(fig)

def link(path,label):return f'<a href="{CASE+path}">{escape(label)}</a>'
tiles=''.join(f'<article class="tile"><strong class="{color}">{value}</strong><span>{label}</span></article>' for value,label,color in cards)
bars=[]
for i,label in zip(intervals,labels):
    tooltip=f'{number(i["responses"])} recorded responses · {number(i["processed_tokens"])} tokens · {number(i["output_tokens"])} output · {i["unpriced_responses"]} unpriced. {i["start"]} to {i["end"]}'
    bars.append(f'<li class="bar-row" tabindex="0"><span>{escape(label)}</span><span class="track"><i style="width:{float(D(i["standard_api_usd"])/maxcost)*100:.4f}%"></i></span><b>{money(i["standard_api_usd"])}</b><span class="tooltip">{escape(tooltip)}</span></li>')
rate_rows=[]
for m,s in models.items():
    rate=RATES.get(m)
    rate_rows.append('<tr>'+''.join(f'<td>{escape(str(v))}</td>' for v in [m,number(s['responses']),number(s['input_tokens']),number(s['cache_read_tokens']),number(s['output_tokens']),(' / '.join('$'+str(rate[k]) for k in ['input','cache_read','output']) if rate else 'Unverified'),money(s['standard_api_usd']) if rate else 'Unpriced'])+'</tr>')
period_rows=[]
for i in intervals:
    period_rows.append('<tr>'+''.join(f'<td>{escape(str(v))}</td>' for v in [i['name'],local(i['start']).strftime('%-I:%M:%S %p'),local(i['end']).strftime('%-I:%M:%S %p'),number(i['responses']),number(i['processed_tokens']),money(i['standard_api_usd'])])+'</tr>')
html='''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Codex refund dashboard — @@REQUEST@@ calculated request</title>
<style>
:root{color-scheme:dark;--bg:#191a18;--panel:#242621;--text:#f4f3ed;--muted:#c0c2b7;--line:#3b3e35;--blue:#599af3;--green:#59c8a5;--purple:#b1a0ec;--amber:#f0c362}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 system-ui,sans-serif}main{max-width:1140px;margin:auto;padding:32px 24px 48px}h1{font-size:32px;line-height:1.15;margin:0 0 12px}h2{font-size:20px;margin:0 0 8px}h3{font-size:16px;margin:0 0 8px}p{margin:0 0 14px}.muted,.note{color:var(--muted)}.note{font-size:13px}a{color:#8db9ff}a:focus-visible,summary:focus-visible,.bar-row:focus-visible{outline:2px solid var(--amber);outline-offset:4px}.meta{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:18px 0;font-size:12px}.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:22px 0}.tile{padding:18px 14px;border-radius:10px;background:var(--panel);display:flex;flex-direction:column}.tile strong{font-size:31px;line-height:1.2}.tile span{font-size:12px;color:var(--muted);margin-top:10px}.green{color:var(--green)}.blue{color:var(--blue)}.purple{color:var(--purple)}.amber{color:var(--amber)}section{margin:30px 0}.equation{font-size:20px;font-weight:650}.stack{display:flex;height:22px;margin:14px 0 10px}.stack .credit{background:var(--green)}.stack .plan{background:var(--blue)}.legend{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;font-size:13px}.caution{background:var(--panel);border-left:3px solid var(--amber);padding:14px 18px;border-radius:4px;margin:20px 0}.caution p{margin:5px 0 0;font-size:13px}.split{display:grid;grid-template-columns:1.6fr 1fr;gap:40px}.bars{list-style:none;margin:16px 0;padding:0}.bar-row{position:relative;display:grid;grid-template-columns:minmax(140px,1fr) 1fr 72px;align-items:center;gap:12px;padding:10px 0;font-size:13px}.bar-row b{text-align:right;font-variant-numeric:tabular-nums}.track{display:block;height:14px;background:#20221e}.track i{display:block;height:14px;background:var(--blue);border-radius:0 4px 4px 0}.tooltip{display:none;position:absolute;top:100%;left:0;right:0;padding:10px;background:#e9e9df;color:#10120e;border-radius:5px;z-index:2}.bar-row:hover .tooltip,.bar-row:focus .tooltip{display:block}.capacity{display:grid;grid-template-columns:66px 1fr 42px;align-items:center;gap:10px;font-size:13px;margin:16px 0}.capacity progress{width:100%;accent-color:var(--purple)}.math{font-size:20px;line-height:1.8;font-variant-numeric:tabular-nums}.overage{font-size:32px;font-weight:650}.divider{border-top:1px solid var(--line);padding-top:25px}.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}th,td{text-align:right;padding:10px 8px;border-bottom:1px solid var(--line);white-space:nowrap}th:first-child,td:first-child{text-align:left}th{color:var(--muted);font-weight:600}details{margin:18px 0}summary{cursor:pointer;font-weight:600}details p{margin:12px 0}.links{display:flex;gap:10px 20px;flex-wrap:wrap}footer{border-top:1px solid var(--line);padding-top:20px;color:var(--muted);font-size:12px}
@media(max-width:760px){.tiles{grid-template-columns:repeat(2,1fr)}.split{grid-template-columns:1fr;gap:24px}.tile strong{font-size:28px}h1{font-size:27px}main{padding:24px 16px}.bar-row{grid-template-columns:minmax(130px,1fr) 1fr 65px;gap:8px}}@media(max-width:400px){.tile strong{font-size:25px}.bar-row{grid-template-columns:1fr 65px}.bar-row>span:first-child{grid-column:1/-1}.equation{font-size:17px}}@media print{body{background:white;color:black}.tile,.caution{border:1px solid #999;background:white}details{display:block}.tooltip{display:none!important}a{color:inherit}.note,.muted{color:#333}}
</style></head><body><main>
'''
html=html.replace('@@REQUEST@@',money(request))
html+=f'''<h1>What the failed Codex session cost</h1><p class="muted">Credit loss, consumed plan allowance, and the cost of correcting the refund claim.</p>
<div class="meta"><span>FIXED SNAPSHOT · {stamp}</span><a href="{ISSUE}">FILED · OPENAI #61739 · NOT REFUNDED</a></div>
<div class="tiles">{tiles}</div>
<section><h2>How the request adds up</h2><p class="equation">{money(credit)} credit component + {money(plan)} plan replacement estimate = {money(request)}</p>
<div class="stack" role="img" aria-label="{money(credit)} credit loss plus {money(plan)} estimated plan replacement"><span class="credit" style="width:{float(credit/(credit+plan))*100}%"></span><span class="plan" style="width:{float(plan/(credit+plan))*100}%"></span></div>
<div class="legend"><span class="green">Credit decrease × $0.04</span><span class="blue">Plan estimate includes the {money(overage)} correction overage</span></div>
<aside class="caution"><strong class="amber">Estimate, not a verified bill or approved refund</strong><p>Per-response funding and speed are unverified; overlap with credit deductions is possible. OpenAI must reconcile the allocation. Restoring plan capacity is an alternative to its dollar estimate, not another amount to add.</p></aside></section>
<section class="split"><div><h2>Plan-period replacement estimates</h2><p class="note">Model-specific rates applied to recorded responses in active-allowance periods. Hover or focus a bar for counts and boundaries.</p><ol class="bars">{''.join(bars)}</ol><p class="note">{number(allowance_count)} recorded responses; {allowance_unpriced} internal reviews remain unpriced. <strong class="blue">Total: {money(plan)}</strong></p></div>
<div><h2>Allowance consumed</h2><p class="note">promax · across observed weekly cycles</p>'''
for label,pct in [('Initial',100),('Reset 1',100),('Reset 2',100),('Reset 3',last_capacity)]:
    html+=f'<label class="capacity"><span>{label}</span><progress max="100" value="{pct}" aria-label="{label}, {pct} percent consumed"></progress><b class="purple">{pct}%</b></label>'
html+=f'''<p><strong class="purple">{capacity_total:g} percentage points of promax allowance</strong><br><span class="note">Plus {prior_capacity:g} points of the earlier pro allowance, separately. The plan capacities are not equivalent.</span></p><p class="note">Rounded observations. The increase from 15% to {last_capacity:g}% spans the original cutoff; it is not attributed entirely to the supplemental interval.</p></div></section>'''
html+=f'''<section class="split divider"><div><h2>The measured credit loss</h2><p class="math green">{before_balance} − {after_balance}<br>= {D(lost_credits):,f} credits</p><p>× ${I['usd_per_credit']} = <strong>${exact_credit}</strong> before rounding</p><p class="note">Owner confirmed this decrease. The earlier 75,000 estimate is superseded. Balance observations are not a complete debit ledger.</p></div><div><h2>The correction itself cost</h2><p class="overage amber">{money(overage)}</p><p>{number(R['reporting_and_correction_overage']['responses'])} responses · {compact(R['reporting_and_correction_overage']['processed_tokens'])} processed tokens</p><p class="note">Refund audit, incorrect filings, and repeated corrections the owner had to demand. Already included in the plan estimate, counted once.</p><p class="note">Other continuing audited chats add {money(R['other_supplement']['standard_api_usd'])}; together they form the {money(R['supplement']['standard_api_usd'])} supplemental estimate.</p></div></section>
<section class="divider"><h2>Full recorded usage · a separate cross-check</h2><p>{number(count)} responses · {compact(tokens)} processed tokens · {compact(output)} output tokens</p><p><strong class="blue">{money(cross)} at standard API rates</strong> <span class="amber">— do not add this to the compensation request.</span></p><div class="scroll"><table><caption class="note">All recorded OpenAI usage, original window plus supplement. Rates are USD per million tokens.</caption><thead><tr><th>Model</th><th>Responses</th><th>Input</th><th>Cached input</th><th>Output</th><th>Input / cached / output rates</th><th>API value</th></tr></thead><tbody>{''.join(rate_rows)}</tbody></table></div></section>
<details><summary>Exact period counts and time boundaries</summary><div class="scroll"><table><caption class="note">All times November 15, 2026, Pacific. First four interval ends inclusive; final two exclusive.</caption><thead><tr><th>Period</th><th>Start</th><th>End</th><th>Recorded responses</th><th>Processed tokens</th><th>Estimate</th></tr></thead><tbody>{''.join(period_rows)}</tbody></table></div></details>
<details><summary>Method, limitations, and requested remedy</summary><p>Each response is priced as (uncached input × input rate + cached input × cache rate + output × output rate) / 1,000,000. The rates vary by model. Cached inputs are included in processed tokens; reasoning is already included in output.</p><p>The original {number(R['full_original_openai']['responses'])} OpenAI response records reconcile across 90 threads. The supplement adds {R['supplement']['responses']} responses. Six internal reviews remain unpriced overall; {allowance_unpriced} fall within the active-allowance estimates. No price is invented for them.</p><p>The request disputes the session as a whole; it does not assert that every individual response was unauthorized. A 52.2395-credit change near reset 2 has an unknown cause and allocation. These time-based estimates require billing reconciliation, including actual speed tiers. Supplemental contents were not re-reviewed response by response.</p><p>Alternative remedy: restore {lost_credits} credits and the consumed plan capacity, accounting for {reset_count} reset transitions. Do not add restored allowance and its replacement estimate together. Later costs are not waived.</p><p>Exact request: ${exact_credit} + ${exact_plan} = ${exact_total}, rounded once to {money(request)}.</p></details>
<section><h2>Evidence and reproduction</h2><nav class="links" aria-label="Evidence links">{link('remedy-calculation.md','Itemized math')}{link('remedy-calculation.json','Calculation JSON')}{link('remedy-inputs.json','Balance and reset evidence')}{link('calculate-remedy.py','Calculator')}{link('full-report.md','Full report')}{link('exclusions.md','Historical exclusions')}<a href="{ISSUE}">Filed bug report</a><a href="{BASE}">Repository</a></nav><p class="note" style="margin-top:16px">Regenerate the calculation with <code>python3 calculate-remedy.py</code>, then this dashboard with <code>uv run build-dashboard.py</code>. The dashboard reads the calculation JSON and requires no browser.</p></section>
<footer>Original window: November 15, 11:40:23 AM–7:40:23 PM PST. Supplement ends at {cutoff.strftime('%-I:%M:%S %p')} PST. Original transcripts remain private; redacted evidence and reproduction code are on main. No refund approval or payment is claimed.</footer></main></body></html>'''
(OUT/'cost-chart.html').write_text(html)
print(json.dumps(dict(requested=money(request),credit=money(credit),plan=money(plan),overage=money(overage),responses=count,tokens=tokens,files=['filed/cost-chart.html','filed/cost-chart.png','filed/cost-chart.svg']),indent=2))
