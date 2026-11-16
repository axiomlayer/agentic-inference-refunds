# Itemized refund and replacement-usage calculation

**Requested compensation: $4,364.57**, comprising **$2,700.84 for 67520.9760395 purchased usage credits** and **$1,663.73 as the estimated replacement value of recorded usage during active plan-allowance periods**. The owner confirmed the measured credit decrease and superseded the earlier 75,000-credit estimate. This is a calculated compensation request, not a representation that OpenAI invoiced this amount.

The original eight-hour accounting remains intact. Supplemental usage runs from 2026-11-16T03:40:23.000Z through 2026-11-16T04:05:16.874Z, end exclusive. The last allowance observation is 2026-11-16T04:05:06.499Z.

## 1. Purchased credits

| Component | Calculation | USD |
|---|---|---:|
| Observed balance decrease | (76,766.749250 − 9,245.7732105) × $0.04 | $2,700.84 |
| Requested credit restoration, confirmed by owner | 67520.9760395 × $0.04 | $2,700.84 |

The observed decrease is account-state evidence, not an invoice or complete debit ledger. The owner explicitly confirmed this measured figure. The earlier 75,000-credit estimate is superseded; no $299.16 remainder is added.

## 2. Plan allowance and reset consumption

| Plan period | Observed allowance consumption | Recorded responses | Replacement estimate |
|---|---:|---:|---:|
| Prior pro allowance | approximately 5 percentage points | 222 | $18.46 |
| Initial promax allowance | approximately 100 percentage points | 1,832 | $381.73 |
| After reset 1 | approximately 100 percentage points | 2,165 | $478.78 |
| After reset 2 | approximately 100 percentage points | 2,932 | $594.25 |
| After reset 3, original window | approximately 15 percentage points | 4,393 | $122.87 |
| Supplement after original cutoff | 30 points since last 15% snapshot; spans cutoff | 426 | $67.63 |
| **Total replacement estimate** | Plan types retained separately | **11,970** | **$1,663.73** |

Three weekly reset transitions are evidenced. Through the latest snapshot, consumption is approximately **345 percentage points of `promax` weekly allowance plus 5 points of the prior `pro` allowance**. The plan labels have different capacities and are not added as if equal. A reset is not priced as a purchased-credit pack or as a monthly subscription.

For each response, the estimate is `(uncached input × input rate + cached input × cached rate + output × output rate) / 1,000,000`. Rates are model-specific. Reasoning is already in output; it is not charged twice.

The recorded-response count includes five unpriced internal auto-review responses in the reset-1 period. They remain in the claim population without an invented dollar rate.

Allowance-period boundaries use observed 0% through first 100% snapshots, plus the final partially consumed period. These are **timestamp-based funding estimates**. They are not a verified mapping of every response to a funding source. A 52.2395-credit balance change occurs around reset 2; its cause and request allocation are unknown. **Some responses in the allowance estimate may also be represented in the purchased-credit decrease.** Thus the allowance component is a provisional replacement estimate, not a proven disjoint billed loss. Standard prices are a stated valuation convention; all 1,268 original turn contexts omit speed/service-tier metadata. OpenAI must reconcile timing and actual tier rates.

## 3. Full usage cross-check — not another amount to add

| Model | Uncached input | Cached input | Output | Rates per million: input / cache / output | Standard API value |
|---|---:|---:|---:|---|---:|
| codex-auto-review | 60,572 | 222,848 | 799 | Unverified | Unpriced |
| gpt-6-astra | 32,198,471 | 1,461,188,864 | 6,871,555 | $10 / $1 / $50 | $2,126.75 |
| gpt-6.1-sol | 6,183,769 | 357,042,432 | 994,872 | $2 / $0.1 / $10 | $58.02 |
| gpt-6.1-terra | 15,065,466 | 816,183,168 | 1,198,951 | $1 / $0.05 / $5 | $61.87 |

Original-window cross-check: **$2,179.01**. Supplemental cross-check: **$67.63** across **426** additional responses. These cross-checks include plan-funded and credit-funded activity together. Adding them to purchased-credit loss would double-count the same work.

## 4. Requested remedy and exclusions

Request **$4,364.57 in compensation or equivalent replacement usage**, subject to correction using OpenAI’s billing records. The exact sum before rounding is `2700.839041580000 + 1663.7266254 = 4364.565666980`. No unverified remainder from the earlier 75,000-credit estimate is added.

An alternative in-kind remedy is **67520.9760395 purchased credits plus restoration of approximately 345 percentage points of `promax` weekly capacity and 5 points of prior `pro` capacity**, with the three reset transitions accounted for. This is an alternative to paying the allowance replacement estimate, not an additional charge on top of it.

### Refund-audit and correction overage

The owner explicitly requested inclusion of the usage spent auditing this incident, filing and correcting the inadequate claims, and requiring repeated corrections to the arithmetic. The reporting chat and its descendants account for **295 responses / 42,008,956 processed tokens / $59.87** after the original cutoff. Other audited chats contribute **$7.76** in the same supplemental interval. Both amounts are already inside the supplemental allowance estimate above; neither is added twice.

The request disputes the failed session as a whole. It does not assert that each individual response was unauthorized. Useful or expressly authorized activity remains disclosed in the full report. Unpriced internal review remains in the claim population. Other-provider usage, duplicate observations and genuinely pre-window identities are excluded from this OpenAI calculation. Supplemental content was not re-reviewed response-by-response. Activity after the fixed cutoff is not priced here and is not waived.

## Sources and reproduction

- [Official model pricing](https://developers.openai.com/api/docs/pricing): numeric rates preserved in `rates-openai.json`.
- [Official ChatGPT credit and speed rates](https://learn.chatgpt.com/docs/pricing#token-rates): plan and purchased-credit speed multipliers differ.
- [Official reset mechanics](https://help.openai.com/en/articles/20001498-how-resets-work-in-codex): reset entitlements restore plan allowance.
- [Official paid-reset mechanics](https://help.openai.com/en/articles/20001507-paid-weekly-work-and-codex-rate-limit-resets): a purchased reset is separate from adding usage credits.
- `remedy-inputs.json`: minimal native-source-linked balance/allowance evidence and interval bounds; `usage.jsonl` and `supplemental-usage.jsonl`: deduplicated response counts.

Run `python3 calculate-remedy.py` in this directory to regenerate this document and `remedy-calculation.json`. No private files or network access are required. No refund approval or payment is claimed.
