# Batch Metadata Generation Todo

## Phase 1: Examine CSV input and create caching system ✅
- [x] Examine CSV file structure (2 papers: BMJ Heart + Springer)
- [x] Create ELSST vocabulary cache (elsst_cache.json)
- [x] Create ORCID information cache (orcid_cache.json)
- [x] Create batch processing framework (batch_metadata_generator.py)
- [x] Set up optimization structure

## Phase 2: Process papers and populate caches ✅
- [x] Process Paper 1: https://heart.bmj.com/content/100/3/239.short (ID: D66SMIX6, Project: 8184)
- [x] Process Paper 2: http://link.springer.com/10.1007/s11187-018-0115-4 (ID: 36CVE4Q2, Project: 8634)
- [x] Extract bibliographic information for both papers
- [x] Find and cache new ELSST vocabulary mappings
- [x] Find and cache new ORCID information
- [x] Update cache files with new discoveries

## Phase 3: Generate optimized metadata files ✅
- [x] Generate D66SMIX6.ttl for BMJ Heart paper
- [x] Generate 36CVE4Q2.ttl for Springer paper
- [x] Apply cached ELSST mappings
- [x] Apply cached ORCID information
- [x] Ensure proper URI formatting (DOI, ORCID, producer)
- [x] Validate metadata completeness

## Phase 4: Deliver results and documentation ✅
- [x] Create batch processing summary report
- [x] Document cache usage and efficiency gains
- [x] Provide updated cache files
- [x] Deliver all metadata files
- [x] Document optimization strategies for future use

## Optimization Notes
- Use caches to avoid repeated ELSST vocabulary lookups
- Use caches to avoid repeated ORCID searches
- Batch similar operations together
- Maintain clear documentation for future maintenance
- Keep cache files human-readable (JSON format)

