# Performance Testing

This directory contains performance testing scripts and results for database query optimization.

## Test Selection Rationale

The current test suite includes 5 key tests that comprehensively cover the application's database query patterns:

### 1. **Benchmark Radar Query (Monthly)**
- **Purpose**: Tests date-range queries with theme filtering (1 month window)
- **Why it matters**: 
  - Benchmark page is a core feature that users frequently access
  - Monthly aggregation is a common query pattern across the application
  - Tests performance of date indexing and theme filtering together
  - Represents typical user interaction: "Show me last month's data"

### 2. **Year Query**
- **Purpose**: Tests larger date-range queries (full year)
- **Why it matters**:
  - Tests scalability with larger datasets
  - Year-over-year comparisons are common in analysis pages
  - Validates that indexes work well even with broader date ranges
  - Represents: "Show me all 2024 data"

### 3. **Dimension Query (Source)**
- **Purpose**: Tests filtering by dimension fields (source, language, etc.)
- **Why it matters**:
  - Users frequently filter by source (Reddit, Twitter, etc.) or language
  - Tests non-date, non-theme filtering performance
  - Validates composite index effectiveness
  - Represents: "Show me Reddit comments only"

### 4. **Dashboard KPIs**
- **Purpose**: Tests aggregate queries for dashboard metrics
- **Why it matters**:
  - Dashboard loads on every page visit - must be fast
  - Tests sentiment aggregation and theme filtering
  - Validates indexes support common aggregation patterns
  - Represents: "Calculate overall sentiment and engagement metrics"

### 5. **Filter Options**
- **Purpose**: Tests queries that fetch distinct values for filter dropdowns
- **Why it matters**:
  - Filter panels need to populate quickly
  - Tests distinct value extraction (themes, languages, sources)
  - Validates indexes help with GROUP BY / DISTINCT operations
  - Represents: "Get all available filter options"

## Why These 5 Tests Are Sufficient

### **Coverage Analysis**

1. **Query Types Covered**:
   - ✅ Date range queries (monthly, yearly)
   - ✅ Theme filtering (base_theme, sub_theme)
   - ✅ Dimension filtering (source, language)
   - ✅ Aggregation queries (KPIs, counts)
   - ✅ Distinct value queries (filter options)

2. **Index Patterns Tested**:
   - ✅ Single column indexes (date, base_theme, sub_theme)
   - ✅ Composite indexes (date + theme combinations)
   - ✅ Filter exclusion patterns (neq 'others', neq 'stock_market')

3. **Data Volume Scenarios**:
   - ✅ Small dataset (monthly: ~10K rows)
   - ✅ Medium dataset (yearly: ~100K rows)
   - ✅ Full table scans (filter options)

4. **Application Pages Covered**:
   - ✅ Benchmark page (radar queries)
   - ✅ Dashboard page (KPIs, filter options)
   - ✅ Analysis page (similar patterns to year query)
   - ✅ Chat Bot (similar patterns to dimension query)

### **Why Not Add More Tests?**

While we could add tests for Analysis page or Chat Bot specifically, they would be **redundant** because:

- **Analysis page queries** use the same patterns as Year Query (date ranges + theme filtering)
- **Chat Bot queries** use the same patterns as Dimension Query (various filters + aggregations)
- **Additional tests** would not reveal new performance bottlenecks beyond what these 5 tests already cover

### **Performance Impact**

These 5 tests measure the **critical path** queries that:
- Are executed most frequently (Dashboard KPIs, Filter Options)
- Handle the largest datasets (Year Query)
- Use the most complex filtering (Benchmark Radar Query)
- Are most sensitive to index performance (Dimension Query)

## Usage

### Running Tests

```bash
# Before adding indexes
python3 data-pre/performance_test/performance_test.py --label before

# After adding indexes  
python3 data-pre/performance_test/performance_test.py --label after
```

### Comparing Results

```bash
# Compare two result files
python3 data-pre/performance_test/performance_test.py --compare \
  results/performance_before_*.json \
  results/performance_after_*.json

# List all saved results
python3 data-pre/performance_test/performance_test.py --list
```

### Visualizing Results

```bash
# Generate visualization from latest comparison
python3 data-pre/performance_test/visualize_performance.py --latest
```

## Expected Improvements

With proper database indexes, typical improvements:
- **Date range queries**: 50-90% faster
- **Theme filtering**: 60-80% faster  
- **Dimension queries**: 40-70% faster
- **Aggregation queries**: 30-60% faster
- **Overall average**: 40-70% faster

## Directory Structure

```
performance_test/
├── performance_test.py          # Main test script
├── visualize_performance.py     # Visualization generator
├── README.md                    # This file
└── results/                     # Test results and visualizations
    ├── performance_before_*.json
    ├── performance_after_*.json
    ├── comparison_*.json
    └── visualizations/
        └── performance_comparison_*.png
```

## Notes

- Tests run each query multiple times (3-5 iterations) and report statistics (mean, median, min, max, stdev)
- Results are automatically saved to `results/` directory
- Old results are preserved for historical comparison
- Visualizations are high-resolution PNG files suitable for reports
