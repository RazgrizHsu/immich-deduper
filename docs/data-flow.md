# Deduper Similarity Processing Data Flow Analysis

## Data Structure Overview

### Related Database Fields
- **simOk**: `INTEGER` (0=unprocessed, 1=resolved)
- **simInfos**: `TEXT` JSON array containing detailed information about similar assets
- **simGIDs**: `TEXT` JSON array containing group ID references

### Similarity Processing States
1. **Not vectorized**: `isVectored=0`
2. **Vectorized but not searched**: `isVectored=1, simOk=0, simInfos='[]'`
3. **Searched pending processing**: `isVectored=1, simOk=0, simInfos='[...]'`
4. **Resolved**: `isVectored=1, simOk=1, simGIDs='[]', simInfos='[]'`
