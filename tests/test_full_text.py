import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modules.literature.full_text import FullTextRetriever


def test_retriever_creates():
    r = FullTextRetriever()
    assert r is not None


def test_tier1_europe_pmc_has_pmcid_no_network():
    r = FullTextRetriever()
    paper = {"pmid": "12345678", "pmcid": "PMC123456", "title": "Test Paper", "source": "pubmed"}
    result = r._tier1_europe_pmc(paper)
    assert result is None


def test_tier1_europe_pmc_no_pmcid():
    r = FullTextRetriever()
    paper = {"doi": "10.1234/test", "title": "No PMCID"}
    result = r._tier1_europe_pmc(paper)
    assert result is None


def test_tier2_pdf_download_no_url():
    r = FullTextRetriever()
    paper = {"title": "No PDF URL"}
    text, pdf = r._tier2_pdf_download(paper)
    assert text is None
    assert pdf is None


def test_tier3_hacker_agent_no_doi_no_url():
    r = FullTextRetriever()
    paper = {"title": "No identifiers"}
    result = r._tier3_hacker_agent(paper)
    assert result is None


def test_retrieve_all_tiers_fail():
    r = FullTextRetriever()
    paper = {"title": "No identifiers at all", "source": "unknown"}
    result = r.retrieve(paper)
    assert result is None


def test_get_last_pdf_bytes_initially_none():
    r = FullTextRetriever()
    assert r.get_last_pdf_bytes() is None


def test_is_substantial_text():
    r = FullTextRetriever()
    assert r._is_substantial_text("Short.\n\nText.") is False
    long_text = (
        "Introduction paragraph with enough content to be considered substantial. "
        * 5
        + "\n\nMethods section with more detailed content about the methodology used. "
        * 5
    )
    assert r._is_substantial_text(long_text) is True
