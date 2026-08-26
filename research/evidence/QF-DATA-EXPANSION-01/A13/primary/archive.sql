-- Frozen two-document diagnostic capture; not a production action feed.
-- Run from the repository root into a NEW evidence-local SQLite database.
.bail on
BEGIN IMMEDIATE;
CREATE TABLE source_documents (
    pdf_sha256 TEXT PRIMARY KEY CHECK(length(pdf_sha256)=64 AND pdf_sha256 NOT GLOB '*[^0-9a-f]*'),
    code TEXT NOT NULL,
    announcement_date TEXT NOT NULL,
    title TEXT NOT NULL,
    landing_url TEXT NOT NULL,
    pdf_url TEXT NOT NULL,
    pdf_body BLOB NOT NULL CHECK(hex(substr(pdf_body,1,5))='255044462D'),
    source_bytes INTEGER NOT NULL CHECK(source_bytes=length(pdf_body)),
    extracted_text TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    provenance TEXT NOT NULL CHECK(provenance='issuer-filing-mirrored-by-sina'),
    ledger_ready INTEGER NOT NULL DEFAULT 0 CHECK(ledger_ready=0)
);
CREATE TRIGGER source_documents_no_update BEFORE UPDATE ON source_documents
BEGIN SELECT RAISE(ABORT,'source documents are immutable'); END;
CREATE TRIGGER source_documents_no_delete BEFORE DELETE ON source_documents
BEGIN SELECT RAISE(ABORT,'source documents are immutable'); END;
INSERT INTO source_documents VALUES (
    'c610a0242cc13bbde06917cfaad3549365afc16e10a5bf278b4751f5be497917',
    'sh.600803', '2024-07-26', '新奥天然气股份有限公司2023年年度权益分派实施公告',
    'https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=10345015&stockid=600803',
    'https://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESH_STOCK/2024/2024-7/2024-07-26/10345015.PDF',
    readfile('research/evidence/QF-DATA-EXPANSION-01/A13/primary/600803-20240726.pdf'),
    370274,
    CAST(readfile('research/evidence/QF-DATA-EXPANSION-01/A13/primary/600803-20240726.txt') AS TEXT),
    strftime('%Y-%m-%dT%H:%M:%fZ','now'), 'issuer-filing-mirrored-by-sina', 0
);
INSERT INTO source_documents VALUES (
    '01338f2bb244f8fb4da8d844db9a4beb461353fcaf3313f38bb6a273a8e8b553',
    'sz.002049', '2022-08-18', '紫光国芯微电子股份有限公司2021年年度权益分派实施公告',
    'https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=8429450&stockid=002049',
    'https://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESZ_STOCK/2022/2022-8/2022-08-18/8429450.PDF',
    readfile('research/evidence/QF-DATA-EXPANSION-01/A13/primary/002049-20220818.pdf'),
    125121,
    CAST(readfile('research/evidence/QF-DATA-EXPANSION-01/A13/primary/002049-20220818.txt') AS TEXT),
    strftime('%Y-%m-%dT%H:%M:%fZ','now'), 'issuer-filing-mirrored-by-sina', 0
);
COMMIT;
