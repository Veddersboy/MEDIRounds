import pytest
from app.services.pubmed_scraper import extract_all_pmcids, normalize_pmcid


def test_normalize_pmcid():
    assert normalize_pmcid("PMC1234567") == "PMC1234567"
    assert normalize_pmcid("1234567") == "PMC1234567"
    assert normalize_pmcid("pmc999") == "PMC999"

    with pytest.raises(ValueError):
        normalize_pmcid("invalid_pmc")


def test_extract_all_pmcids():
    blob = "PMC1234567, PMC2345678 and https://pmc.ncbi.nlm.nih.gov/articles/PMC3456789/"
    extracted = extract_all_pmcids(blob)
    assert extracted == ["PMC1234567", "PMC2345678", "PMC3456789"]

    bare_numbers = "10138454 10170769"
    assert extract_all_pmcids(bare_numbers) == ["PMC10138454", "PMC10170769"]
