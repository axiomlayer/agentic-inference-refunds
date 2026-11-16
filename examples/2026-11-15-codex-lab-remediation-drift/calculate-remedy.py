"""Reproduce the itemized compensation estimate; no network or private files."""
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).parent
inputs = json.loads((HERE/'remedy-inputs.json').read_text())
rates = json.loads((HERE/'rates-openai.json').read_text())['models']
original = [json.loads(s) for s in (HERE/'usage.jsonl').open() if s.strip()]
supplement = [json.loads(s) for s in (HERE/'supplemental-usage.jsonl').open() if s.strip()]
rows = [r for r in original if r['provider']=='openai'] + supplement
assert len({r['request_id'] for r in rows}) == len(rows), 'Duplicate response identity'
assert all(r['timestamp'] >= inputs['original_window_end'] for r in supplement)
def instant(s): return datetime.fromisoformat(s.replace('Z','+00:00'))
def money(x): return f'${D(x).quantize(D("0.01"),rounding=ROUND_HALF_UP):,}'
def price(r):
    rate=rates.get(r['model'])
    if rate is None:return None
    assert not any(r.get(k,0) for k in ['cache_write_tokens','cache_write_5m_tokens','cache_write_1h_tokens']), 'Unmodeled cache-write fee'
    return sum(D(r[field])*D(str(rate[key])) for field,key in [('input_tokens','input'),('cache_read_tokens','cache_read'),('output_tokens','output')])/D(1000000)
def summary(rs):
    out=dict(responses=len(rs),input_tokens=sum(r['input_tokens'] for r in rs),cache_read_tokens=sum(r['cache_read_tokens'] for r in rs),output_tokens=sum(r['output_tokens'] for r in rs))
    out['processed_tokens']=out['input_tokens']+out['cache_read_tokens']+out['output_tokens']
    out['unpriced_responses']=sum(price(r) is None for r in rs)
    out['standard_api_usd']=str(sum((price(r) or D(0) for r in rs),D(0)))
    return out
intervals=[];allocated=set()
for index,i in enumerate(inputs['allowance_intervals']):
    start,end=instant(i['start']),instant(i['end'])
    selected=[r for r in rows if start<=instant(r['timestamp']) and (instant(r['timestamp'])<=end if index<4 else instant(r['timestamp'])<end)]
    ids={r['request_id'] for r in selected}
    assert not ids & allocated, 'Allowance intervals overlap'
    allocated |= ids
    intervals.append(dict(**i,**summary(selected)))
plan_value=sum((D(i['standard_api_usd']) for i in intervals),D(0))
observed_credits=D(inputs['observed_credit_start'])-D(inputs['observed_credit_end'])
reported_credits=D(inputs['requested_credit_loss']);unit=D(inputs['usd_per_credit'])
observed_cash=observed_credits*unit;gap_credits=reported_credits-observed_credits
requested=reported_credits*unit+plan_value
models={m:summary([r for r in rows if r['model']==m]) for m in sorted({r['model'] for r in rows})}
latest=max(inputs['snapshots'],key=lambda r:r['timestamp'])
capacity=dict(original_promax_percentage_points=315,increase_since_last_original_snapshot_percentage_points=latest['primary']['used_percent']-15,
              through_snapshot_promax_percentage_points=300+latest['primary']['used_percent'],prior_pro_percentage_points=5,
              observed_reset_transitions=3)
result=dict(status='itemized_requested_compensation_estimate_not_verified_bill',
    requested_refund_usd=str(requested.quantize(D('0.01'),rounding=ROUND_HALF_UP)),requested_unrounded_usd=str(requested),
    purchased_credit_component=dict(observed_decrease_credits=str(observed_credits),observed_replacement_usd=str(observed_cash),
      unreconciled_reported_remainder_credits=str(gap_credits),unreconciled_reported_remainder_usd=str(gap_credits*unit),
      requested_credits=str(reported_credits),requested_usd=str(reported_credits*unit)),
    allowance_replacement_estimate_usd=str(plan_value),allowance_capacity=capacity,allowance_intervals=intervals,
    recorded_credit_decrease_plus_allowance_estimate_usd=str(observed_cash+plan_value),
    full_original_openai=summary([r for r in original if r['provider']=='openai']),supplement=summary(supplement),models=models,
    reporting_and_correction_overage=summary([r for r in supplement if r.get('reporting_and_correction_work')]),
    other_supplement=summary([r for r in supplement if not r.get('reporting_and_correction_work')]),
    funding_allocation_verified=False,speed_tiers_verified=False,refund_approved=False,
    non_additivity='The full token-price total is an alternate cross-check, not added to purchased credits. Restore plan/reset entitlements OR pay their replacement estimate; do not add both.',
    limits=inputs['limits'])
(HERE/'remedy-calculation.json').write_text(json.dumps(result,indent=2)+'\n')
lines=['# Itemized refund and replacement-usage calculation','',
 f'**Requested compensation: {money(requested)}**, comprising **{money(reported_credits*unit)} for {reported_credits} purchased usage credits** and **{money(plan_value)} as the estimated replacement value of recorded usage during active plan-allowance periods**. The owner confirmed the measured credit decrease and superseded the earlier 75,000-credit estimate. This is a calculated compensation request, not a representation that OpenAI invoiced this amount.',
 '',f'The original eight-hour accounting remains intact. Supplemental usage runs from {inputs["original_window_end"]} through {inputs["supplement_end_exclusive"]}, end exclusive. The last allowance observation is {latest["timestamp"]}.',
 '', '## 1. Purchased credits','',
 '| Component | Calculation | USD |','|---|---|---:|',
 f'| Observed balance decrease | (76,766.749250 − 9,245.7732105) × $0.04 | {money(observed_cash)} |',
 f'| Requested credit restoration, confirmed by owner | {reported_credits} × $0.04 | {money(reported_credits*unit)} |',
 '', 'The observed decrease is account-state evidence, not an invoice or complete debit ledger. The owner explicitly confirmed this measured figure. The earlier 75,000-credit estimate is superseded; no $299.16 remainder is added.',
 '', '## 2. Plan allowance and reset consumption','',
 '| Plan period | Observed allowance consumption | Recorded responses | Replacement estimate |','|---|---:|---:|---:|']
for i in intervals:
    pct=i['percentage_points']
    pct_text=f'approximately {pct:g} percentage points' if pct is not None else f'{capacity["increase_since_last_original_snapshot_percentage_points"]:g} points since last 15% snapshot; spans cutoff'
    lines.append(f'| {i["name"]} | {pct_text} | {i["responses"]:,} | {money(i["standard_api_usd"])} |')
lines += [f'| **Total replacement estimate** | Plan types retained separately | **{sum(i["responses"] for i in intervals):,}** | **{money(plan_value)}** |','',
 f'Three weekly reset transitions are evidenced. Through the latest snapshot, consumption is approximately **{capacity["through_snapshot_promax_percentage_points"]:g} percentage points of `promax` weekly allowance plus 5 points of the prior `pro` allowance**. The plan labels have different capacities and are not added as if equal. A reset is not priced as a purchased-credit pack or as a monthly subscription.',
 '', 'For each response, the estimate is `(uncached input × input rate + cached input × cached rate + output × output rate) / 1,000,000`. Rates are model-specific. Reasoning is already in output; it is not charged twice.',
 '', 'The recorded-response count includes five unpriced internal auto-review responses in the reset-1 period. They remain in the claim population without an invented dollar rate.',
 '', 'Allowance-period boundaries use observed 0% through first 100% snapshots, plus the final partially consumed period. These are **timestamp-based funding estimates**. They are not a verified mapping of every response to a funding source. A 52.2395-credit balance change occurs around reset 2; its cause and request allocation are unknown. **Some responses in the allowance estimate may also be represented in the purchased-credit decrease.** Thus the allowance component is a provisional replacement estimate, not a proven disjoint billed loss. Standard prices are a stated valuation convention; all 1,268 original turn contexts omit speed/service-tier metadata. OpenAI must reconcile timing and actual tier rates.',
 '', '## 3. Full usage cross-check — not another amount to add','',
 '| Model | Uncached input | Cached input | Output | Rates per million: input / cache / output | Standard API value |','|---|---:|---:|---:|---|---:|']
for m,s in models.items():
    rate=rates.get(m)
    rate_text='Unverified' if rate is None else ' / '.join('$'+str(rate[k]) for k in ['input','cache_read','output'])
    lines.append(f'| {m} | {s["input_tokens"]:,} | {s["cache_read_tokens"]:,} | {s["output_tokens"]:,} | {rate_text} | {"Unpriced" if s["unpriced_responses"] else money(s["standard_api_usd"])} |')
lines += ['',f'Original-window cross-check: **{money(result["full_original_openai"]["standard_api_usd"])}**. Supplemental cross-check: **{money(result["supplement"]["standard_api_usd"])}** across **{len(supplement):,}** additional responses. These cross-checks include plan-funded and credit-funded activity together. Adding them to purchased-credit loss would double-count the same work.',
 '', '## 4. Requested remedy and exclusions','',
 f'Request **{money(requested)} in compensation or equivalent replacement usage**, subject to correction using OpenAI’s billing records. The exact sum before rounding is `{observed_cash} + {plan_value} = {requested}`. No unverified remainder from the earlier 75,000-credit estimate is added.',
 '',f'An alternative in-kind remedy is **{reported_credits} purchased credits plus restoration of approximately {capacity["through_snapshot_promax_percentage_points"]:g} percentage points of `promax` weekly capacity and 5 points of prior `pro` capacity**, with the three reset transitions accounted for. This is an alternative to paying the allowance replacement estimate, not an additional charge on top of it.',
 '', '### Refund-audit and correction overage', '',
 f'The owner explicitly requested inclusion of the usage spent auditing this incident, filing and correcting the inadequate claims, and requiring repeated corrections to the arithmetic. The reporting chat and its descendants account for **{result["reporting_and_correction_overage"]["responses"]:,} responses / {result["reporting_and_correction_overage"]["processed_tokens"]:,} processed tokens / {money(result["reporting_and_correction_overage"]["standard_api_usd"])}** after the original cutoff. Other audited chats contribute **{money(result["other_supplement"]["standard_api_usd"])}** in the same supplemental interval. Both amounts are already inside the supplemental allowance estimate above; neither is added twice.',
 '', 'The request disputes the failed session as a whole. It does not assert that each individual response was unauthorized. Useful or expressly authorized activity remains disclosed in the full report. Unpriced internal review remains in the claim population. Other-provider usage, duplicate observations and genuinely pre-window identities are excluded from this OpenAI calculation. Supplemental content was not re-reviewed response-by-response. Activity after the fixed cutoff is not priced here and is not waived.',
 '', '## Sources and reproduction','',
 '- [Official model pricing](https://developers.openai.com/api/docs/pricing): numeric rates preserved in `rates-openai.json`.',
 '- [Official ChatGPT credit and speed rates](https://learn.chatgpt.com/docs/pricing#token-rates): plan and purchased-credit speed multipliers differ.',
 '- [Official reset mechanics](https://help.openai.com/en/articles/20001498-how-resets-work-in-codex): reset entitlements restore plan allowance.',
 '- [Official paid-reset mechanics](https://help.openai.com/en/articles/20001507-paid-weekly-work-and-codex-rate-limit-resets): a purchased reset is separate from adding usage credits.',
 '- `remedy-inputs.json`: minimal native-source-linked balance/allowance evidence and interval bounds; `usage.jsonl` and `supplemental-usage.jsonl`: deduplicated response counts.',
 '', 'Run `python3 calculate-remedy.py` in this directory to regenerate this document and `remedy-calculation.json`. No private files or network access are required. No refund approval or payment is claimed.','']
(HERE/'remedy-calculation.md').write_text('\n'.join(lines))
print(json.dumps({k:result[k] for k in ['requested_refund_usd','allowance_replacement_estimate_usd','recorded_credit_decrease_plus_allowance_estimate_usd','allowance_capacity','supplement']},indent=2))
