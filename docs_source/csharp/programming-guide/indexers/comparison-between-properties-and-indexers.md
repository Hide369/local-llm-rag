---
name: csharp
repo: dotnet/docs
ref: main
commit: 434d5f080534909ba985053aec2f2ba2e73f4c1c
source_path: docs/csharp/programming-guide/indexers/comparison-between-properties-and-indexers.md
title: Comparison Between Properties and Indexers
version: 0.0.0
fetched_at: 2026-09-13
---
# Comparison Between Properties and Indexers (C# Programming Guide)

Indexers are like properties. Except for the differences shown in the following table, all the rules that are defined for property accessors apply to indexer accessors also.  
  
|Property|Indexer|  
|--------------|-------------|  
|Allows methods to be called as if they were public data members.|Allows elements of an internal collection of an object to be accessed by using array notation on the object itself.|  
|Accessed through a simple name.|Accessed through an index.|  
|Can be a static or an instance member.|Must be an instance member.|  
|A [get](../../language-reference/keywords/get.md) accessor of a property has no parameters.|A `get` accessor of an indexer has the same formal parameter list as the indexer.|  
|A [set](../../language-reference/keywords/set.md) accessor of a property contains the implicit `value` parameter.|A `set` accessor of an indexer has the same formal parameter list as the indexer, and also to the [value](../../language-reference/keywords/value.md) parameter.|  
|Supports shortened syntax with [Automatically implemented properties](../classes-and-structs/auto-implemented-properties.md).|Supports expression bodied members for get only indexers.|  
  
## See also

- [Indexers](./index.md)
- [Properties](../classes-and-structs/properties.md)
