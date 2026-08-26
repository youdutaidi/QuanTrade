# A5 issuer-document counterexamples

Purpose: distinguish substantive source disagreements from representational
rounding before any account consumer is admitted. No portfolio return was read
or calculated. These two public issuer filings are hosted by a mirror; they are
not independent exchange-host authenticity checks or exhaustive issuer coverage.

## 600803, ex-date 2024-08-01

[Issuer filing landing page](https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=10345015&stockid=600803).
Original PDF `600803-20240726.pdf`, SHA256
`c610a0242cc13bbde06917cfaad3549365afc16e10a5bf278b4751f5be497917`.
Rendered pages 1 and 2 were inspected; all four pages were text-extracted.

The document specifies gross cash of 0.91 yuan per eligible share, record date
2024-07-31, and ex/payment date 2024-08-01. Repurchased/cancel-pending shares are
excluded. The reference-price adjustment instead uses virtual cash of 0.9054
yuan, reflecting the excluded shares. This agrees with the raw gross numeric
field but contradicts the source description's 0.66 yuan equivalent. It is not
merely a tiny decimal-rounding discrepancy, and cash paid must not be replaced
by the reference-price adjustment.

The local market rows are 19.63 prior close and 18.72 ex-date preclose. Applying
the issuer's reference formula rounds to 18.72, as checked separately. This does
not validate investor-specific net cash or authorize a generic source-field
override for other dates/securities.

## 002049, ex-date 2022-08-24

[Issuer filing landing page](https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=8429450&stockid=002049).
Original PDF `002049-20220818.pdf`, SHA256
`01338f2bb244f8fb4da8d844db9a4beb461353fcaf3313f38bb6a273a8e8b553`.
All three rendered pages were inspected and text-extracted.

The document specifies cash of 0.324998 yuan and reserve shares of 0.3999976 per
share. The latter agrees with the source description divided by ten, not its
six-decimal numeric reserve field (0.399998). Record date is 2022-08-23;
ex-date, share credit and cash distribution are 2022-08-24. The 242 prior close
maps to 172.63 reference price under the stated formula.

Its fractional-share method uses ranked remainders with random tie ordering,
not unconditional flooring. The document also displays 242,744,034 new shares
in its calculation and 242,744,038 in the final capital table. That internal
total discrepancy is retained, not silently reconciled. Exact investor share
allocation and tax treatment are still unadmitted.

## Local recovery and claim boundary

`archive.sql` is an immutable two-document evidence recipe, not an active Python
runner. It created the previously absent `source_documents.sqlite`, storing PDF
BLOBs, text, source URLs, claimed announcement dates and actual retrieval times.
Updates/deletes are refused and repeated primary keys cannot replace bytes.
`archive-verification.json` records byte equality and the in-memory immutability
probes. Originals were not edited/re-exported; PNGs are reading intermediates.

`reference-price-rows.json` contains the four actual daily rows;
`reference-formula-check.json` contains exact Decimal calculations and cent-level
comparisons. The first diagnostic query used the nonexistent column `date`; it
failed before reading results or changing data, then was corrected to the real
`trade_date` schema. All monetary observations here are source diagnosis, not a
new economic policy, certified settlement, or a strategy-performance result.
