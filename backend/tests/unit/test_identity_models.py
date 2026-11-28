from app.models.identity import Asset, AssetIdentifier, Company


def test_identity_models_are_registered_in_metadata():
    assert {"companies", "assets", "asset_identifiers"}.issubset(
        Company.metadata.tables.keys()
    )


def test_identifier_has_temporal_and_owner_constraints():
    constraints = {constraint.name for constraint in AssetIdentifier.__table__.constraints}
    assert "ck_asset_identifiers_exactly_one_owner" in constraints
    assert "ck_asset_identifiers_valid_date_order" in constraints
    assert "uq_asset_identifiers_type_value_from" in constraints
    assert Asset.__tablename__ == "assets"


def test_company_metadata_includes_sec_sic_classification_fields():
    columns = Company.__table__.columns
    assert {"sic_code", "sic_description", "sic_verified_at"} <= set(columns.keys())
    constraints = {constraint.name for constraint in Company.__table__.constraints}
    assert "ck_companies_sic_code_format" in constraints
