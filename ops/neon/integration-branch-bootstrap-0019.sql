BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_initial_schema

INSERT INTO alembic_version (version_num) VALUES ('0001_initial_schema') RETURNING alembic_version.version_num;

-- Running upgrade 0001_initial_schema -> 0002_asset_identity

CREATE TABLE companies (
    legal_name VARCHAR(300) NOT NULL, 
    display_name VARCHAR(300), 
    country_code VARCHAR(2), 
    status VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    CONSTRAINT pk_companies PRIMARY KEY (id)
);

CREATE INDEX ix_companies_name ON companies (legal_name);

CREATE TABLE assets (
    company_id UUID NOT NULL, 
    asset_type VARCHAR(30) NOT NULL, 
    name VARCHAR(300) NOT NULL, 
    status VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    CONSTRAINT pk_assets PRIMARY KEY (id), 
    CONSTRAINT fk_assets_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE RESTRICT
);

CREATE INDEX ix_assets_company_type ON assets (company_id, asset_type);

CREATE TABLE asset_identifiers (
    company_id UUID, 
    asset_id UUID, 
    identifier_type VARCHAR(30) NOT NULL, 
    value VARCHAR(160) NOT NULL, 
    exchange_mic VARCHAR(4), 
    exchange_name VARCHAR(120), 
    valid_from DATE, 
    valid_to DATE, 
    verification_status VARCHAR(30) DEFAULT 'UNVERIFIED' NOT NULL, 
    source_name VARCHAR(100), 
    source_url VARCHAR(500), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    CONSTRAINT pk_asset_identifiers PRIMARY KEY (id), 
    CONSTRAINT ck_asset_identifiers_ck_asset_identifiers_exactly_one_owner CHECK ((company_id IS NOT NULL AND asset_id IS NULL) OR (company_id IS NULL AND asset_id IS NOT NULL)), 
    CONSTRAINT ck_asset_identifiers_ck_asset_identifiers_valid_date_order CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from), 
    CONSTRAINT uq_asset_identifiers_type_value_from UNIQUE (identifier_type, value, valid_from), 
    CONSTRAINT fk_asset_identifiers_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_asset_identifiers_asset_id_assets FOREIGN KEY(asset_id) REFERENCES assets (id) ON DELETE RESTRICT
);

CREATE INDEX ix_asset_identifiers_lookup ON asset_identifiers (identifier_type, value);

UPDATE alembic_version SET version_num='0002_asset_identity' WHERE alembic_version.version_num = '0001_initial_schema';

-- Running upgrade 0002_asset_identity -> 0003_sec_financial_data

CREATE TABLE sec_raw_company_facts (
    company_id UUID NOT NULL, 
    cik VARCHAR(10) NOT NULL, 
    provider VARCHAR(30) DEFAULT 'SEC' NOT NULL, 
    source_url VARCHAR(500) NOT NULL, 
    payload_hash VARCHAR(64) NOT NULL, 
    payload_text TEXT NOT NULL, 
    retrieved_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    connector_version VARCHAR(40) DEFAULT 'sec-companyfacts-v1' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    CONSTRAINT pk_sec_raw_company_facts PRIMARY KEY (id), 
    CONSTRAINT uq_sec_raw_company_facts_cik_hash UNIQUE (cik, payload_hash), 
    CONSTRAINT fk_sec_raw_company_facts_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE RESTRICT
);

CREATE INDEX ix_sec_raw_company_facts_cik_retrieved ON sec_raw_company_facts (cik, retrieved_at);

CREATE TABLE financial_facts (
    company_id UUID NOT NULL, 
    raw_record_id UUID NOT NULL, 
    cik VARCHAR(10) NOT NULL, 
    external_fact_key VARCHAR(64) NOT NULL, 
    metric_id VARCHAR(80) NOT NULL, 
    taxonomy VARCHAR(40) NOT NULL, 
    tag VARCHAR(160) NOT NULL, 
    value NUMERIC(38, 10) NOT NULL, 
    unit VARCHAR(40) NOT NULL, 
    currency VARCHAR(3), 
    period_kind VARCHAR(20) NOT NULL, 
    start_date DATE, 
    end_date DATE NOT NULL, 
    fiscal_year INTEGER, 
    fiscal_period VARCHAR(8), 
    form VARCHAR(20), 
    accession_number VARCHAR(30), 
    filed_at DATE, 
    frame VARCHAR(40), 
    retrieved_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    mapping_version VARCHAR(40) DEFAULT 'sec-us-gaap-v1' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    CONSTRAINT pk_financial_facts PRIMARY KEY (id), 
    CONSTRAINT uq_financial_facts_external_key UNIQUE (external_fact_key), 
    CONSTRAINT fk_financial_facts_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_financial_facts_raw_record_id_sec_raw_company_facts FOREIGN KEY(raw_record_id) REFERENCES sec_raw_company_facts (id) ON DELETE RESTRICT
);

CREATE INDEX ix_financial_facts_company_metric_period ON financial_facts (company_id, metric_id, end_date);

CREATE INDEX ix_financial_facts_cik_filed ON financial_facts (cik, filed_at);

CREATE TABLE normalized_financial_facts (
    company_id UUID NOT NULL, 
    source_fact_id UUID NOT NULL, 
    metric_id VARCHAR(80) NOT NULL, 
    value NUMERIC(38, 10) NOT NULL, 
    unit VARCHAR(40) NOT NULL, 
    currency VARCHAR(3), 
    period_kind VARCHAR(20) NOT NULL, 
    fiscal_year INTEGER, 
    fiscal_period VARCHAR(8), 
    start_date DATE, 
    end_date DATE NOT NULL, 
    origin VARCHAR(20) DEFAULT 'REPORTED' NOT NULL, 
    derivation_version VARCHAR(40), 
    normalized_key VARCHAR(64) NOT NULL, 
    filed_at DATE, 
    available_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    CONSTRAINT pk_normalized_financial_facts PRIMARY KEY (id), 
    CONSTRAINT uq_normalized_financial_facts_key UNIQUE (normalized_key), 
    CONSTRAINT fk_normalized_financial_facts_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_normalized_financial_facts_source_fact_id_financial_facts FOREIGN KEY(source_fact_id) REFERENCES financial_facts (id) ON DELETE RESTRICT
);

CREATE INDEX ix_normalized_facts_company_metric_year ON normalized_financial_facts (company_id, metric_id, fiscal_year);

CREATE TABLE financial_fact_lineage (
    normalized_fact_id UUID NOT NULL, 
    source_fact_id UUID NOT NULL, 
    role VARCHAR(30) DEFAULT 'DIRECT_SOURCE' NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    CONSTRAINT pk_financial_fact_lineage PRIMARY KEY (id), 
    CONSTRAINT uq_financial_fact_lineage_edge UNIQUE (normalized_fact_id, source_fact_id, role), 
    CONSTRAINT fk_financial_fact_lineage_normalized_fact_id_normalized_0209 FOREIGN KEY(normalized_fact_id) REFERENCES normalized_financial_facts (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_financial_fact_lineage_source_fact_id_financial_facts FOREIGN KEY(source_fact_id) REFERENCES financial_facts (id) ON DELETE RESTRICT
);

CREATE FUNCTION reject_financial_data_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'financial source and normalized records are append-only';
        END;
        $$ LANGUAGE plpgsql;;

CREATE TRIGGER trg_sec_raw_company_facts_append_only BEFORE UPDATE OR DELETE ON sec_raw_company_facts FOR EACH ROW EXECUTE FUNCTION reject_financial_data_mutation();

CREATE TRIGGER trg_financial_facts_append_only BEFORE UPDATE OR DELETE ON financial_facts FOR EACH ROW EXECUTE FUNCTION reject_financial_data_mutation();

CREATE TRIGGER trg_normalized_financial_facts_append_only BEFORE UPDATE OR DELETE ON normalized_financial_facts FOR EACH ROW EXECUTE FUNCTION reject_financial_data_mutation();

CREATE TRIGGER trg_financial_fact_lineage_append_only BEFORE UPDATE OR DELETE ON financial_fact_lineage FOR EACH ROW EXECUTE FUNCTION reject_financial_data_mutation();

UPDATE alembic_version SET version_num='0003_sec_financial_data' WHERE alembic_version.version_num = '0002_asset_identity';

-- Running upgrade 0003_sec_financial_data -> 0004_financial_metrics_quality

CREATE TABLE financial_metric_runs (
    company_id UUID NOT NULL, 
    fiscal_year INTEGER NOT NULL, 
    resolution_policy VARCHAR(30) NOT NULL, 
    as_known_at DATE, 
    engine_version VARCHAR(40) NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    CONSTRAINT pk_financial_metric_runs PRIMARY KEY (id), 
    CONSTRAINT fk_financial_metric_runs_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE RESTRICT
);

CREATE INDEX ix_metric_runs_company_created ON financial_metric_runs (company_id, created_at);

CREATE TABLE financial_metric_results (
    run_id UUID NOT NULL, 
    company_id UUID NOT NULL, 
    fiscal_year INTEGER NOT NULL, 
    metric_id VARCHAR(80) NOT NULL, 
    value NUMERIC(38, 16), 
    unit VARCHAR(30) NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    reason TEXT, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    CONSTRAINT pk_financial_metric_results PRIMARY KEY (id), 
    CONSTRAINT uq_metric_result_run_metric UNIQUE (run_id, metric_id), 
    CONSTRAINT fk_financial_metric_results_run_id_financial_metric_runs FOREIGN KEY(run_id) REFERENCES financial_metric_runs (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_financial_metric_results_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE RESTRICT
);

CREATE INDEX ix_metric_results_company_year ON financial_metric_results (company_id, fiscal_year);

CREATE TABLE financial_metric_lineage (
    result_id UUID NOT NULL, 
    normalized_fact_id UUID NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    CONSTRAINT pk_financial_metric_lineage PRIMARY KEY (id), 
    CONSTRAINT uq_metric_lineage_result_fact UNIQUE (result_id, normalized_fact_id), 
    CONSTRAINT fk_financial_metric_lineage_result_id_financial_metric_results FOREIGN KEY(result_id) REFERENCES financial_metric_results (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_financial_metric_lineage_normalized_fact_id_normaliz_6205 FOREIGN KEY(normalized_fact_id) REFERENCES normalized_financial_facts (id) ON DELETE RESTRICT
);

CREATE TABLE financial_quality_findings (
    company_id UUID NOT NULL, 
    fiscal_year INTEGER NOT NULL, 
    run_id UUID, 
    rule_id VARCHAR(80) NOT NULL, 
    severity VARCHAR(20) NOT NULL, 
    message TEXT NOT NULL, 
    metric_id VARCHAR(80), 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    CONSTRAINT pk_financial_quality_findings PRIMARY KEY (id), 
    CONSTRAINT fk_financial_quality_findings_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_financial_quality_findings_run_id_financial_metric_runs FOREIGN KEY(run_id) REFERENCES financial_metric_runs (id) ON DELETE RESTRICT
);

CREATE INDEX ix_fin_quality_company_year ON financial_quality_findings (company_id, fiscal_year);

CREATE TRIGGER trg_financial_metric_runs_append_only BEFORE UPDATE OR DELETE ON financial_metric_runs FOR EACH ROW EXECUTE FUNCTION reject_financial_data_mutation();

CREATE TRIGGER trg_financial_metric_results_append_only BEFORE UPDATE OR DELETE ON financial_metric_results FOR EACH ROW EXECUTE FUNCTION reject_financial_data_mutation();

CREATE TRIGGER trg_financial_metric_lineage_append_only BEFORE UPDATE OR DELETE ON financial_metric_lineage FOR EACH ROW EXECUTE FUNCTION reject_financial_data_mutation();

CREATE TRIGGER trg_financial_quality_findings_append_only BEFORE UPDATE OR DELETE ON financial_quality_findings FOR EACH ROW EXECUTE FUNCTION reject_financial_data_mutation();

UPDATE alembic_version SET version_num='0004_financial_metrics_quality' WHERE alembic_version.version_num = '0003_sec_financial_data';

-- Running upgrade 0004_financial_metrics_quality -> 0005_sec_provider_cache

CREATE TABLE sec_provider_cache (
    provider VARCHAR(30) DEFAULT 'SEC' NOT NULL, 
    cache_key VARCHAR(300) NOT NULL, 
    source_url VARCHAR(500) NOT NULL, 
    payload_hash VARCHAR(64) NOT NULL, 
    payload_text TEXT NOT NULL, 
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    CONSTRAINT pk_sec_provider_cache PRIMARY KEY (id), 
    CONSTRAINT uq_sec_provider_cache_provider_key UNIQUE (provider, cache_key)
);

CREATE INDEX ix_sec_provider_cache_expires ON sec_provider_cache (expires_at);

UPDATE alembic_version SET version_num='0005_sec_provider_cache' WHERE alembic_version.version_num = '0004_financial_metrics_quality';

-- Running upgrade 0005_sec_provider_cache -> 0006_bq_assessments

CREATE TABLE business_quality_assessments (
    company_id UUID NOT NULL, 
    engine_version VARCHAR(40) NOT NULL, 
    rubric_version VARCHAR(40) NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    overall_score NUMERIC(6, 2), 
    classification VARCHAR(30) NOT NULL, 
    completeness_pct NUMERIC(6, 2) NOT NULL, 
    analysis_confidence VARCHAR(20) NOT NULL, 
    observations JSONB NOT NULL, 
    results JSONB NOT NULL, 
    analyst_id VARCHAR(120), 
    notes TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    CONSTRAINT pk_business_quality_assessments PRIMARY KEY (id), 
    CONSTRAINT fk_business_quality_assessments_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE RESTRICT
);

CREATE INDEX ix_bq_assessments_company_created ON business_quality_assessments (company_id, created_at);

UPDATE alembic_version SET version_num='0006_bq_assessments' WHERE alembic_version.version_num = '0005_sec_provider_cache';

-- Running upgrade 0006_bq_assessments -> 0007_bq_review_events

CREATE TABLE business_quality_review_events (
    assessment_id UUID NOT NULL, 
    from_status VARCHAR(20) NOT NULL, 
    to_status VARCHAR(20) NOT NULL, 
    action VARCHAR(20) NOT NULL, 
    actor_id VARCHAR(120) NOT NULL, 
    comment TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    CONSTRAINT pk_business_quality_review_events PRIMARY KEY (id), 
    CONSTRAINT fk_business_quality_review_events_assessment_id_busines_8253 FOREIGN KEY(assessment_id) REFERENCES business_quality_assessments (id) ON DELETE RESTRICT
);

CREATE INDEX ix_bq_review_events_assessment_created ON business_quality_review_events (assessment_id, created_at);

UPDATE alembic_version SET version_num='0007_bq_review_events' WHERE alembic_version.version_num = '0006_bq_assessments';

-- Running upgrade 0007_bq_review_events -> 0008_business_quality_evidence

CREATE TABLE bq_source_documents (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    company_id UUID NOT NULL, 
    accession_number VARCHAR(32) NOT NULL, 
    form_type VARCHAR(12) NOT NULL, 
    filed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    published_at TIMESTAMP WITH TIME ZONE, 
    source_url TEXT NOT NULL, 
    content_type VARCHAR(120) NOT NULL, 
    document_hash VARCHAR(64) NOT NULL, 
    original_content BYTEA NOT NULL, 
    extraction_version VARCHAR(40) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_bq_source_documents PRIMARY KEY (id), 
    CONSTRAINT uq_bq_source_document_identity UNIQUE (company_id, accession_number, document_hash), 
    CONSTRAINT fk_bq_source_documents_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE RESTRICT
);

CREATE INDEX ix_bq_source_documents_company_filed ON bq_source_documents (company_id, filed_at);

CREATE TABLE bq_document_sections (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    document_id UUID NOT NULL, 
    section_key VARCHAR(80) NOT NULL, 
    heading VARCHAR(500) NOT NULL, 
    sequence_number INTEGER NOT NULL, 
    text_content TEXT NOT NULL, 
    content_hash VARCHAR(64) NOT NULL, 
    extraction_method VARCHAR(40) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_bq_document_sections PRIMARY KEY (id), 
    CONSTRAINT uq_bq_section_sequence UNIQUE (document_id, section_key, sequence_number), 
    CONSTRAINT fk_bq_document_sections_document_id_bq_source_documents FOREIGN KEY(document_id) REFERENCES bq_source_documents (id) ON DELETE RESTRICT
);

CREATE INDEX ix_bq_document_sections_document ON bq_document_sections (document_id);

CREATE TABLE bq_evidence_candidates (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    company_id UUID NOT NULL, 
    document_id UUID NOT NULL, 
    section_id UUID, 
    criterion_key VARCHAR(100) NOT NULL, 
    passage TEXT NOT NULL, 
    rationale TEXT NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    source_locator VARCHAR(500) NOT NULL, 
    evidence_hash VARCHAR(64) NOT NULL, 
    created_by VARCHAR(120) NOT NULL, 
    reviewed_by VARCHAR(120), 
    review_comment TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_bq_evidence_candidates PRIMARY KEY (id), 
    CONSTRAINT fk_bq_evidence_candidates_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_bq_evidence_candidates_document_id_bq_source_documents FOREIGN KEY(document_id) REFERENCES bq_source_documents (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_bq_evidence_candidates_section_id_bq_document_sections FOREIGN KEY(section_id) REFERENCES bq_document_sections (id) ON DELETE RESTRICT
);

CREATE INDEX ix_bq_evidence_candidates_company_status ON bq_evidence_candidates (company_id, status);

UPDATE alembic_version SET version_num='0008_business_quality_evidence' WHERE alembic_version.version_num = '0007_bq_review_events';

-- Running upgrade 0008_business_quality_evidence -> 0009_bq_evidence_audit_pit

CREATE TABLE bq_evidence_review_events (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    candidate_id UUID NOT NULL, 
    from_status VARCHAR(20), 
    to_status VARCHAR(20) NOT NULL, 
    actor_id VARCHAR(120) NOT NULL, 
    comment TEXT, 
    previous_event_hash VARCHAR(64), 
    event_hash VARCHAR(64) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_bq_evidence_review_events PRIMARY KEY (id), 
    CONSTRAINT fk_bq_evidence_review_events_candidate_id_bq_evidence_c_1a22 FOREIGN KEY(candidate_id) REFERENCES bq_evidence_candidates (id) ON DELETE RESTRICT, 
    CONSTRAINT uq_bq_evidence_review_events_event_hash UNIQUE (event_hash)
);

CREATE INDEX ix_bq_evidence_review_events_candidate_created ON bq_evidence_review_events (candidate_id, created_at);

CREATE TABLE bq_assessment_evidence_links (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    assessment_id UUID NOT NULL, 
    candidate_id UUID NOT NULL, 
    as_of TIMESTAMP WITH TIME ZONE NOT NULL, 
    eligible BOOLEAN NOT NULL, 
    decision_reason VARCHAR(60) NOT NULL, 
    policy_version VARCHAR(40) NOT NULL, 
    evidence_hash VARCHAR(64) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_bq_assessment_evidence_links PRIMARY KEY (id), 
    CONSTRAINT uq_bq_assessment_evidence_link UNIQUE (assessment_id, candidate_id), 
    CONSTRAINT fk_bq_assessment_evidence_links_assessment_id_business__b49a FOREIGN KEY(assessment_id) REFERENCES business_quality_assessments (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_bq_assessment_evidence_links_candidate_id_bq_evidenc_d360 FOREIGN KEY(candidate_id) REFERENCES bq_evidence_candidates (id) ON DELETE RESTRICT
);

CREATE INDEX ix_bq_assessment_evidence_assessment ON bq_assessment_evidence_links (assessment_id);

UPDATE alembic_version SET version_num='0009_bq_evidence_audit_pit' WHERE alembic_version.version_num = '0008_business_quality_evidence';

-- Running upgrade 0009_bq_evidence_audit_pit -> 0010_auth_rbac

CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    email VARCHAR(320) NOT NULL, 
    password_hash VARCHAR(256) NOT NULL, 
    display_name VARCHAR(160) NOT NULL, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_users PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE company_memberships (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID NOT NULL, 
    company_id UUID NOT NULL, 
    role VARCHAR(20) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_company_memberships PRIMARY KEY (id), 
    CONSTRAINT uq_company_membership_user_company UNIQUE (user_id, company_id), 
    CONSTRAINT ck_company_memberships_company_membership_role_valid CHECK (role IN ('ANALYST','REVIEWER','ADMIN')), 
    CONSTRAINT fk_company_memberships_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_company_memberships_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE CASCADE
);

CREATE INDEX ix_company_memberships_company ON company_memberships (company_id);

UPDATE alembic_version SET version_num='0010_auth_rbac' WHERE alembic_version.version_num = '0009_bq_evidence_audit_pit';

-- Running upgrade 0010_auth_rbac -> 0011_auth_security

CREATE TABLE auth_sessions (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID NOT NULL, 
    refresh_token_hash VARCHAR(64) NOT NULL, 
    csrf_token_hash VARCHAR(64) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    last_used_at TIMESTAMP WITH TIME ZONE, 
    revoked_at TIMESTAMP WITH TIME ZONE, 
    user_agent VARCHAR(500), 
    ip_address VARCHAR(64), 
    CONSTRAINT pk_auth_sessions PRIMARY KEY (id), 
    CONSTRAINT fk_auth_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_auth_sessions_refresh_token_hash UNIQUE (refresh_token_hash)
);

CREATE INDEX ix_auth_sessions_user_active ON auth_sessions (user_id, revoked_at, expires_at);

CREATE TABLE auth_audit_events (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID, 
    event_type VARCHAR(40) NOT NULL, 
    success BOOLEAN NOT NULL, 
    ip_address VARCHAR(64), 
    user_agent VARCHAR(500), 
    details VARCHAR(1000), 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_auth_audit_events PRIMARY KEY (id), 
    CONSTRAINT fk_auth_audit_events_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_auth_audit_user_created ON auth_audit_events (user_id, created_at);

CREATE TABLE auth_refresh_token_history (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    session_id UUID NOT NULL, 
    token_hash VARCHAR(64) NOT NULL, 
    issued_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    consumed_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_auth_refresh_token_history PRIMARY KEY (id), 
    CONSTRAINT fk_auth_refresh_token_history_session_id_auth_sessions FOREIGN KEY(session_id) REFERENCES auth_sessions (id) ON DELETE CASCADE, 
    CONSTRAINT uq_auth_refresh_token_history_token_hash UNIQUE (token_hash)
);

CREATE INDEX ix_auth_refresh_history_session ON auth_refresh_token_history (session_id, consumed_at);

CREATE TABLE login_rate_limits (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    key_hash VARCHAR(64) NOT NULL, 
    window_started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    attempts INTEGER DEFAULT '0' NOT NULL, 
    blocked_until TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_login_rate_limits PRIMARY KEY (id), 
    CONSTRAINT uq_login_rate_limits_key_hash UNIQUE (key_hash), 
    CONSTRAINT ck_login_rate_limits_login_rate_limit_attempts_nonnegative CHECK (attempts >= 0)
);

CREATE FUNCTION reject_auth_audit_mutation() RETURNS trigger AS $$
    BEGIN
      RAISE EXCEPTION 'auth_audit_events is append-only';
    END;
    $$ LANGUAGE plpgsql;;

CREATE TRIGGER trg_auth_audit_events_immutable
    BEFORE UPDATE OR DELETE ON auth_audit_events
    FOR EACH ROW EXECUTE FUNCTION reject_auth_audit_mutation();;

UPDATE alembic_version SET version_num='0011_auth_security' WHERE alembic_version.version_num = '0010_auth_rbac';

-- Running upgrade 0011_auth_security -> 0012_investment_thesis

CREATE TABLE investment_theses (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    company_id UUID NOT NULL, 
    owner_user_id UUID NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    status VARCHAR(30) DEFAULT 'ACTIVE' NOT NULL, 
    current_version_number INTEGER DEFAULT '1' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_investment_theses PRIMARY KEY (id), 
    CONSTRAINT fk_investment_theses_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_investment_theses_owner_user_id_users FOREIGN KEY(owner_user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_investment_theses_company_owner ON investment_theses (company_id, owner_user_id, updated_at);

CREATE TABLE investment_thesis_versions (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    thesis_id UUID NOT NULL, 
    version_number INTEGER NOT NULL, 
    summary TEXT NOT NULL, 
    rationale TEXT NOT NULL, 
    assumptions JSONB NOT NULL, 
    risks JSONB NOT NULL, 
    evidence_references JSONB NOT NULL, 
    author_user_id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_investment_thesis_versions PRIMARY KEY (id), 
    CONSTRAINT uq_thesis_version_number UNIQUE (thesis_id, version_number), 
    CONSTRAINT fk_investment_thesis_versions_thesis_id_investment_theses FOREIGN KEY(thesis_id) REFERENCES investment_theses (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_investment_thesis_versions_author_user_id_users FOREIGN KEY(author_user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_thesis_versions_created ON investment_thesis_versions (thesis_id, created_at);

CREATE TABLE investment_thesis_events (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    thesis_id UUID NOT NULL, 
    version_id UUID NOT NULL, 
    event_type VARCHAR(40) NOT NULL, 
    decision VARCHAR(40) NOT NULL, 
    payload JSONB NOT NULL, 
    actor_user_id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_investment_thesis_events PRIMARY KEY (id), 
    CONSTRAINT fk_investment_thesis_events_thesis_id_investment_theses FOREIGN KEY(thesis_id) REFERENCES investment_theses (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_investment_thesis_events_version_id_investment_thesi_ea64 FOREIGN KEY(version_id) REFERENCES investment_thesis_versions (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_investment_thesis_events_actor_user_id_users FOREIGN KEY(actor_user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_thesis_events_thesis_created ON investment_thesis_events (thesis_id, created_at);

CREATE FUNCTION reject_thesis_history_mutation() RETURNS trigger AS $$
    BEGIN
      RAISE EXCEPTION 'investment thesis versions and events are append-only';
    END;
    $$ LANGUAGE plpgsql;;

CREATE TRIGGER trg_thesis_versions_immutable
    BEFORE UPDATE OR DELETE ON investment_thesis_versions
    FOR EACH ROW EXECUTE FUNCTION reject_thesis_history_mutation();;

CREATE TRIGGER trg_thesis_events_immutable
    BEFORE UPDATE OR DELETE ON investment_thesis_events
    FOR EACH ROW EXECUTE FUNCTION reject_thesis_history_mutation();;

UPDATE alembic_version SET version_num='0012_investment_thesis' WHERE alembic_version.version_num = '0011_auth_security';

-- Running upgrade 0012_investment_thesis -> 0013_thesis_evidence_links

CREATE TABLE investment_thesis_evidence_links (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    thesis_id UUID NOT NULL, 
    version_id UUID NOT NULL, 
    assumption_id VARCHAR(80) NOT NULL, 
    evidence_candidate_id UUID, 
    metric_result_id UUID, 
    relationship VARCHAR(20) NOT NULL, 
    rationale TEXT NOT NULL, 
    created_by UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_investment_thesis_evidence_links PRIMARY KEY (id), 
    CONSTRAINT ck_investment_thesis_evidence_links_ck_thesis_evidence__4484 CHECK ((evidence_candidate_id IS NOT NULL AND metric_result_id IS NULL) OR (evidence_candidate_id IS NULL AND metric_result_id IS NOT NULL)), 
    CONSTRAINT ck_investment_thesis_evidence_links_ck_thesis_evidence__5b76 CHECK (relationship IN ('SUPPORTS','CONTRADICTS','QUALIFIES')), 
    CONSTRAINT fk_investment_thesis_evidence_links_thesis_id_investment_theses FOREIGN KEY(thesis_id) REFERENCES investment_theses (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_investment_thesis_evidence_links_version_id_investme_ba29 FOREIGN KEY(version_id) REFERENCES investment_thesis_versions (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_investment_thesis_evidence_links_evidence_candidate__0d7c FOREIGN KEY(evidence_candidate_id) REFERENCES bq_evidence_candidates (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_investment_thesis_evidence_links_metric_result_id_fi_58f0 FOREIGN KEY(metric_result_id) REFERENCES financial_metric_results (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_investment_thesis_evidence_links_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_thesis_evidence_version_assumption ON investment_thesis_evidence_links (version_id, assumption_id);

CREATE TRIGGER trg_thesis_evidence_links_immutable BEFORE UPDATE OR DELETE ON investment_thesis_evidence_links FOR EACH ROW EXECUTE FUNCTION reject_thesis_history_mutation();

UPDATE alembic_version SET version_num='0013_thesis_evidence_links' WHERE alembic_version.version_num = '0012_investment_thesis';

-- Running upgrade 0013_thesis_evidence_links -> 0014_thesis_monitoring_alerts

CREATE TABLE investment_thesis_alerts (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    thesis_id UUID NOT NULL, 
    version_id UUID NOT NULL, 
    assumption_id VARCHAR(80) NOT NULL, 
    metric_run_id UUID NOT NULL, 
    alert_type VARCHAR(40) NOT NULL, 
    status VARCHAR(20) DEFAULT 'PENDING' NOT NULL, 
    summary TEXT NOT NULL, 
    details JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_investment_thesis_alerts PRIMARY KEY (id), 
    CONSTRAINT uq_thesis_alert_detection UNIQUE (thesis_id, version_id, assumption_id, metric_run_id, alert_type), 
    CONSTRAINT ck_investment_thesis_alerts_ck_thesis_alert_status CHECK (status IN ('PENDING','REVIEWED','RESOLVED')), 
    CONSTRAINT ck_investment_thesis_alerts_ck_thesis_alert_type CHECK (alert_type IN ('THRESHOLD_BREACH','MATERIAL_CHANGE')), 
    CONSTRAINT fk_investment_thesis_alerts_thesis_id_investment_theses FOREIGN KEY(thesis_id) REFERENCES investment_theses (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_investment_thesis_alerts_version_id_investment_thesi_4d7d FOREIGN KEY(version_id) REFERENCES investment_thesis_versions (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_investment_thesis_alerts_metric_run_id_financial_metric_runs FOREIGN KEY(metric_run_id) REFERENCES financial_metric_runs (id) ON DELETE RESTRICT
);

CREATE INDEX ix_thesis_alerts_thesis_status_created ON investment_thesis_alerts (thesis_id, status, created_at);

CREATE TABLE investment_thesis_alert_events (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    alert_id UUID NOT NULL, 
    from_status VARCHAR(20), 
    to_status VARCHAR(20) NOT NULL, 
    actor_user_id UUID NOT NULL, 
    comment TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_investment_thesis_alert_events PRIMARY KEY (id), 
    CONSTRAINT ck_investment_thesis_alert_events_ck_thesis_alert_event_5dc9 CHECK (to_status IN ('PENDING','REVIEWED','RESOLVED')), 
    CONSTRAINT fk_investment_thesis_alert_events_alert_id_investment_t_8682 FOREIGN KEY(alert_id) REFERENCES investment_thesis_alerts (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_investment_thesis_alert_events_actor_user_id_users FOREIGN KEY(actor_user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_thesis_alert_events_alert_created ON investment_thesis_alert_events (alert_id, created_at);

CREATE TRIGGER trg_thesis_alert_events_immutable BEFORE UPDATE OR DELETE ON investment_thesis_alert_events FOR EACH ROW EXECUTE FUNCTION reject_thesis_history_mutation();

UPDATE alembic_version SET version_num='0014_thesis_monitoring_alerts' WHERE alembic_version.version_num = '0013_thesis_evidence_links';

-- Running upgrade 0014_thesis_monitoring_alerts -> 0015_integration_readiness

UPDATE alembic_version SET version_num='0015_integration_readiness' WHERE alembic_version.version_num = '0014_thesis_monitoring_alerts';

-- Running upgrade 0015_integration_readiness -> 0016_connection_hardening

UPDATE alembic_version SET version_num='0016_connection_hardening' WHERE alembic_version.version_num = '0015_integration_readiness';

-- Running upgrade 0016_connection_hardening -> 0017_sec_preservation

UPDATE alembic_version SET version_num='0017_sec_preservation' WHERE alembic_version.version_num = '0016_connection_hardening';

-- Running upgrade 0017_sec_preservation -> 0018_point_in_time_contract

UPDATE alembic_version SET version_num='0018_point_in_time_contract' WHERE alembic_version.version_num = '0017_sec_preservation';

-- Running upgrade 0018_point_in_time_contract -> 0019_neon_operational_indexes

CREATE INDEX ix_financial_facts_company_metric_filed_accession ON financial_facts (company_id, metric_id, end_date, filed_at, accession_number);

CREATE INDEX ix_normalized_facts_company_metric_available ON normalized_financial_facts (company_id, metric_id, end_date, available_at);

UPDATE alembic_version SET version_num='0019_neon_operational_indexes' WHERE alembic_version.version_num = '0018_point_in_time_contract';

COMMIT;

