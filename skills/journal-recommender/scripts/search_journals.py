"""
Journal search helper for the journal-recommender skill.
Usage: python search_journals.py --keywords "oncology,machine learning" --indexing both --oa no_pref --limit 120
"""
import argparse
import sqlite3
import os
import json

DB = os.path.join(os.path.dirname(__file__), '..', 'assets', 'journals.db')

def search(keywords, indexing='no_pref', oa='no_pref', limit=120):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    filters = []
    params = []

    if indexing == 'wos_only':
        filters.append('wos_indexed = 1')
    elif indexing == 'scopus_only':
        filters.append('scopus_indexed = 1')
    elif indexing == 'both':
        filters.append('wos_indexed = 1 AND scopus_indexed = 1')

    if oa == 'oa_only':
        filters.append("oa_status = 'Open Access'")
    elif oa == 'subscription_only':
        filters.append("oa_status = 'Subscription'")

    kw_list = [k.strip() for k in keywords.split(',') if k.strip()]
    if kw_list:
        clauses = []
        for kw in kw_list:
            clauses.append("(wos_categories LIKE ? OR scopus_subjects LIKE ? OR title LIKE ?)")
            params.extend([f'%{kw}%', f'%{kw}%', f'%{kw}%'])
        filters.append('(' + ' OR '.join(clauses) + ')')

    where = ' AND '.join(filters) if filters else '1=1'
    query = f"""
        SELECT title, publisher, oa_status,
               wos_indexed, scopus_indexed,
               wos_categories, scopus_subjects,
               issn, eissn
        FROM journals
        WHERE {where}
        ORDER BY (wos_indexed + scopus_indexed) DESC, title ASC
        LIMIT {int(limit)}
    """
    rows = conn.execute(query, params).fetchall()
    conn.close()

    results = [dict(r) for r in rows]
    print(json.dumps(results, indent=2))
    return results

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--keywords', required=True, help='Comma-separated keywords')
    parser.add_argument('--indexing', default='no_pref', choices=['wos_only','scopus_only','both','no_pref'])
    parser.add_argument('--oa', default='no_pref', choices=['oa_only','subscription_only','no_pref'])
    parser.add_argument('--limit', type=int, default=120)
    args = parser.parse_args()
    search(args.keywords, args.indexing, args.oa, args.limit)
