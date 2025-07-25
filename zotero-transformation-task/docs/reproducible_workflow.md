# Reproducible Workflow: TTL-Based Metadata Enrichment

## Overview

This document provides a complete reproducible workflow for processing publications from `original.ttl` and generating enriched Dublin Core BIBO-compliant metadata files using the SSHOC-NL Zotero pipeline.

## Prerequisites

### System Requirements
- **Python**: 3.7 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 2GB RAM (recommended 4GB for large batches)
- **Storage**: 500MB free space for cache files and generated metadata
- **Internet**: Required for initial vocabulary and author lookups (optional for cached runs)

### Input Data
- **original.ttl**: RDF/Turtle file containing 1,000+ publications from Zotero
- **Cache Files**: Pre-populated JSON files for efficient processing

## Complete Reproducible Setup

### Step 1: Repository Setup
```bash
# Clone the repository
git clone https://github.com/rsiebes/sshoc-nl-zotero.git
cd sshoc-nl-zotero/zotero-transformation-task/

# Verify directory structure
ls -la
# Expected output:
# README.md
# ttl_metadata_generator.py
# batch_metadata_generator.py (legacy)
# data/
# cache/
# examples/
# docs/
```

### Step 2: Input Data Verification
```bash
# Verify original.ttl exists and contains publications
ls -lh data/original.ttl
# Expected: File should exist and be ~500KB-1MB

# Count publications in original.ttl
grep -c "^<http" data/original.ttl
# Expected: 1000+ publications

# Preview first few publications
head -20 data/original.ttl
```

### Step 3: Cache System Verification
```bash
# Verify cache files exist
ls -la cache/
# Expected files:
# orcid_cache.json (45+ researcher profiles)
# elsst_cache.json (650+ semantic terms)
# organization_cache.json (20+ institutional profiles)

# Check cache file sizes
wc -l cache/*.json
# Expected:
# ~100 lines in orcid_cache.json
# ~1300 lines in elsst_cache.json
# ~50 lines in organization_cache.json
```

### Step 4: Example Processing (First 25 Publications)
```bash
# Process first 25 publications (reproduces example output)
python3 ttl_metadata_generator.py 1 25

# Expected output:
# ✅ Parsed 1000+ publications from data/original.ttl
# 🚀 Processing publications 1 to 25 of 1000+ total
# ✅ [  1/ 25] Generated PUBLICATION_001.ttl
# ✅ [  2/ 25] Generated PUBLICATION_002.ttl
# ...
# ✅ [ 25/ 25] Generated PUBLICATION_025.ttl
# 🎉 Successfully processed 25 publications!
```

### Step 5: Output Verification
```bash
# Verify generated files
ls data/generated/*.ttl | wc -l
# Expected: 25 files

# Check file sizes (should be substantial with enriched metadata)
ls -lh data/generated/*.ttl | head -5
# Expected: Files should be 3-8KB each

# Verify TTL syntax (basic check)
head -10 data/generated/PANTEIA_MKB_FINANCING_DATASET.ttl
# Expected: Valid RDF/Turtle syntax with proper prefixes
```

## Reproducible Example Output

### Expected Generated Files (25 publications)

#### Health Economics & Medical Research (8 files):
```
FISCHER_RIVM_DUELS_AIR_POLLUTION_MORTALITY.ttl
HOPMAN_NIVEL_MULTIPLE_CHRONIC_DISEASES.ttl
HUNT_PHARMLINES_STATINS_SEX_DISPARITIES.ttl
VAN_MAURIK_AMYLOID_PET_ALZHEIMER.ttl
WOUTERSE_BASELINE_HEALTH_HOSPITAL_COSTS.ttl
VAN_KEMPEN_RIVM_NOISE_CARDIOVASCULAR_HEALTH.ttl
STAATSEN_RIVM_HEALTH_IMPACT_ASSESSMENT.ttl
HOEK_UTRECHT_AIR_POLLUTION_MORTALITY.ttl
```

#### Economics & Business Intelligence (6 files):
```
PANTEIA_MKB_FINANCING_DATASET.ttl
ZHOU_FIRM_GROWTH_SURVIVAL.ttl
BARTELSMAN_GAUTIER_DEWIND_EMPLOYMENT_PROTECTION.ttl
PREENEN_TNO_LABOUR_PRODUCTIVITY_INNOVATION.ttl
FARIA_DOLFSMA_INNOVATION_CAPABILITIES.ttl
PANTEIA_SME_DATASET.ttl
```

#### Social Sciences & Demographics (7 files):
```
K8M9N2P5.ttl
R7T8U9V0.ttl
Q3W4E5R6.ttl
T2U3V4W5.ttl
TUIT_VAN_OURS_CORRECTED.ttl
X6Y7Z8A9.ttl
DE_HOLLANDER_RIVM_ENVIRONMENTAL_BURDEN_DISEASE.ttl
```

#### Housing & Urban Policy (2 files):
```
BOUMEESTER_DOL_HOUSING_FLEXIBILITY.ttl
TIGGELOVEN_KLOUWEN_HOUSING.ttl
```

#### Education & Technology (2 files):
```
ITS_ECONOMICS_EDUCATION_REPORT.ttl
AHTI_COVID19_DASHBOARD.ttl
```

### Sample Output Content Verification

#### Check Dublin Core BIBO Compliance:
```bash
# Verify BIBO ontology usage
grep -c "bibo:" data/generated/*.ttl | head -5
# Expected: Each file should contain multiple bibo: references

# Verify Dublin Core terms
grep -c "dc:" data/generated/*.ttl | head -5
# Expected: Each file should contain multiple dc: references
```

#### Check Author Information:
```bash
# Verify ORCID integration
grep -c "orcid" data/generated/*.ttl | head -5
# Expected: Many files should contain ORCID references

# Verify author profiles
grep -A 5 "schema:author" data/generated/FISCHER_RIVM_DUELS_AIR_POLLUTION_MORTALITY.ttl
# Expected: Complete author profile with name, affiliation, etc.
```

#### Check Organizational Context:
```bash
# Verify parent organization inclusion
grep -c "parentOrganization" data/generated/*.ttl | head -5
# Expected: All files should contain parentOrganization

# Verify ROR identifiers
grep -c "ror.org" data/generated/*.ttl | head -5
# Expected: Many files should contain ROR identifiers
```

## Quality Assurance Checks

### Metadata Completeness Verification
```bash
# Check for required Dublin Core fields
for field in "dc:title" "dc:identifier" "schema:author" "schema:parentOrganization"; do
    echo "Checking $field:"
    grep -c "$field" data/generated/*.ttl | grep ":0" | wc -l
    echo "Files missing $field: $(grep -c "$field" data/generated/*.ttl | grep ":0" | wc -l)"
done
# Expected: 0 files missing any required field
```

### Semantic Web Compliance Verification
```bash
# Check TTL syntax validity (basic)
for file in data/generated/*.ttl; do
    if ! head -1 "$file" | grep -q "@prefix"; then
        echo "Warning: $file may have syntax issues"
    fi
done
# Expected: No warnings

# Verify URI format
grep -c "^<http" data/generated/*.ttl | head -5
# Expected: Each file should contain proper URI declarations
```

### Cache Performance Verification
```bash
# Check cache hit rates (approximate)
echo "ORCID cache entries: $(grep -c '"' cache/orcid_cache.json)"
echo "ELSST cache entries: $(grep -c '"uri"' cache/elsst_cache.json)"
echo "Organization cache entries: $(grep -c '"name"' cache/organization_cache.json)"

# Expected output:
# ORCID cache entries: 45+
# ELSST cache entries: 650+
# Organization cache entries: 20+
```

## Advanced Processing Options

### Process Different Ranges
```bash
# Process next 25 publications
python3 ttl_metadata_generator.py 26 50

# Process specific small batch for testing
python3 ttl_metadata_generator.py 1 5

# Process larger batch
python3 ttl_metadata_generator.py 1 100
```

### Monitor Processing Performance
```bash
# Time the processing
time python3 ttl_metadata_generator.py 1 10

# Expected timing:
# First run (cache misses): ~5-30 seconds per publication
# Subsequent runs (cache hits): ~2-5 seconds per publication
```

### Validate Output Quality
```bash
# Check for consistent file sizes
ls -l data/generated/*.ttl | awk '{print $5}' | sort -n | head -5
# Expected: Files should be 2-10KB (substantial metadata)

# Verify cross-disciplinary coverage
grep -l "ELSST" data/generated/*.ttl | wc -l
# Expected: Most files should contain ELSST terms

# Check international collaboration
grep -l "Babson\|Washington\|München" data/generated/*.ttl | wc -l
# Expected: Some files should show international collaboration
```

## Troubleshooting

### Common Issues and Solutions

#### Issue: "original.ttl not found"
```bash
# Solution: Verify file location
ls data/original.ttl
# If missing, ensure the file is in the correct location
```

#### Issue: "No publications found to process"
```bash
# Solution: Check TTL file format
head -10 data/original.ttl
# Verify it contains lines starting with <http
```

#### Issue: Cache files missing
```bash
# Solution: Create empty cache files if needed
mkdir -p cache
echo '{}' > cache/orcid_cache.json
echo '{}' > cache/elsst_cache.json
echo '{}' > cache/organization_cache.json
```

#### Issue: Slow processing
```bash
# Solution: Check internet connection and cache hit rates
# First run will be slower due to cache population
# Subsequent runs should be much faster
```

### Performance Optimization

#### Batch Size Optimization
```bash
# For development/testing: small batches
python3 ttl_metadata_generator.py 1 5

# For production: medium batches
python3 ttl_metadata_generator.py 1 25

# For full processing: large batches
python3 ttl_metadata_generator.py 1 100
```

#### Cache Management
```bash
# Backup cache files before major processing
cp -r cache/ cache_backup/

# Monitor cache growth
ls -lh cache/*.json

# Manually edit cache files if needed (they're human-readable JSON)
```

## Integration with Research Workflows

### Knowledge Graph Integration
```bash
# Generated TTL files are ready for:
# - Triple stores (Apache Jena, Virtuoso, etc.)
# - SPARQL queries
# - Semantic web applications
# - Research data platforms
```

### Research Analytics
```bash
# Files can be used for:
# - Bibliometric analysis
# - Author network analysis
# - Cross-disciplinary research mapping
# - Policy impact assessment
```

### Data Sharing and Preservation
```bash
# Create archive for sharing
tar -czf sshoc_nl_enriched_metadata.tar.gz data/generated/

# Verify archive
tar -tzf sshoc_nl_enriched_metadata.tar.gz | wc -l
# Expected: 25 files
```

## Reproducibility Verification

### Complete Workflow Test
```bash
#!/bin/bash
# Complete reproducibility test script

echo "=== SSHOC-NL Reproducibility Test ==="

# 1. Verify setup
echo "1. Verifying setup..."
test -f data/original.ttl && echo "✅ original.ttl found" || echo "❌ original.ttl missing"
test -d cache && echo "✅ cache directory found" || echo "❌ cache directory missing"

# 2. Clean previous results
echo "2. Cleaning previous results..."
rm -rf data/generated/*

# 3. Process publications
echo "3. Processing first 25 publications..."
python3 ttl_metadata_generator.py 1 25

# 4. Verify output
echo "4. Verifying output..."
file_count=$(ls data/generated/*.ttl 2>/dev/null | wc -l)
echo "Generated files: $file_count"
test $file_count -eq 25 && echo "✅ Correct number of files" || echo "❌ Incorrect file count"

# 5. Quality checks
echo "5. Quality checks..."
for file in data/generated/*.ttl; do
    if ! grep -q "@prefix" "$file"; then
        echo "❌ $file missing prefixes"
    fi
done

echo "=== Reproducibility test complete ==="
```

## Citation and Attribution

When using this reproducible workflow, please cite:

```
Siebes, R. (2025). SSHOC-NL Zotero Pipeline: TTL-Based Metadata Enrichment. 
UCDS group, VU Amsterdam. 
https://github.com/rsiebes/sshoc-nl-zotero
```

## Support and Contact

For questions about this reproducible workflow:
- **Author**: Ronald Siebes - UCDS group - VU Amsterdam
- **Email**: r.m.siebes@vu.nl
- **Repository**: https://github.com/rsiebes/sshoc-nl-zotero

---

**Document Version**: 1.0.0  
**Last Updated**: July 2025  
**Workflow Tested**: Python 3.7+ on Linux/macOS/Windows

