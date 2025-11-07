# 🎯 Sample Questions for ArthaNethra Testing & Demo

## 🚀 **Quick Start Questions**

### **Test Property Filtering (Fixed Issue)**
1. **"Which cities have accounts payable over $500,000?"** ✅
   - This should now work with property filters!
   
2. **"Show me cities with total assets over $50 million"**
3. **"Find cities with cash balance below $1 million"**
4. **"Which cities have debt over $10 million?"**

### **Test Entity Type Recognition**
5. **"Show me all cities"** (should map to Location entities)
6. **"List all locations in the document"**
7. **"What companies are mentioned?"**
8. **"Show me all loans"**

---

## 📊 **Financial Statement Questions**

### Entity Queries
1. "Show me all cities in the financial statement"
2. "What cities have the highest cash balance?"
3. "Which city has the most total assets?"
4. "List all cities with negative cash flow"
5. "Show me cities with debt over $1 million"
6. "What are the top 10 cities by total assets?"
7. "Find cities in Franklin County"
8. "Which cities have accounts payable over $500,000?"

### Metric Calculations
9. "Calculate the total cash across all cities"
10. "What's the average total assets per city?"
11. "Show me the total debt for all cities"
12. "What's the total accounts receivable?"
13. "Calculate the debt-to-assets ratio for Columbus"

### Comparisons
14. "Compare cash balances between Columbus and Cleveland"
15. "Which city has more investments: Cincinnati or Dayton?"
16. "Show me cities with assets greater than Columbus"

---

## 🔗 **Relationship & Graph Queries**

### Graph Traversal
17. "Show me all entities connected to City Of Columbus"
18. "What entities are related to City Of Warren?"
19. "Find all relationships for City Of Cleveland"
20. "Show me entities connected to City Of Westerville through 2 hops"

### Path Finding
21. "How are City Of Columbus and City Of Cleveland connected?"
22. "Find the path between City Of Worthington and City Of Dublin"
23. "Show me the connection path from City Of Akron to City Of Canton"

### Pattern Matching
24. "Find all cities with more than 5 relationships"
25. "Show me entities with the most connections"
26. "Which cities have relationships with multiple counties?"

---

## 💰 **Loan Agreement Questions**

27. "What loans are in the document?"
28. "Show me all loans with interest rates above 5%"
29. "Which loans have variable interest rates?"
30. "Find loans maturing within the next 12 months"
31. "What's the total principal amount of all loans?"
32. "Show me loans with collateral"
33. "Which borrower has the most loans?"
34. "What are the loan covenants?"
35. "Find loans with prepayment penalties"
36. "Show me loans with origination fees"

### Loan Relationships
37. "Show me all loans connected to Bank of America"
38. "What entities are related to the loan agreement?"
39. "Find all lenders in the document"

---

## 📄 **Contract Questions**

40. "What parties are in the contract?"
41. "Show me all contract clauses"
42. "What are the payment terms?"
43. "When does this contract expire?"
44. "What are the obligations in the contract?"
45. "Show me warranty clauses"
46. "What's the governing law?"
47. "Find all termination clauses"
48. "What are the confidentiality terms?"

### Contract Relationships
49. "Show me all parties connected to this contract"
50. "What entities are mentioned in the agreement?"
51. "Find all obligations related to Company X"

---

## 📝 **Invoice Questions**

52. "What invoices are in the document?"
53. "Show me all line items from the invoice"
54. "What's the total amount on the invoice?"
55. "Who is the vendor?"
56. "What's the invoice due date?"
57. "Show me invoices over $10,000"
58. "What items are on invoice #12345?"
59. "Find all invoices from Acme Corp"
60. "Calculate the total tax across all invoices"
61. "Show me unpaid invoices"

### Invoice Relationships
62. "What vendors are in the invoices?"
63. "Show me all customers who have invoices"
64. "Find invoices connected to Company X"

---

## ⚠️ **Risk Detection Questions**

65. "What risks were detected in the document?"
66. "Show me high-severity risks"
67. "What are the financial risks?"
68. "Which entities have the most risks?"
69. "Show me risks related to debt"
70. "What are the recommendations for the detected risks?"
71. "Find risks with debt ratios above threshold"
72. "Show me compliance risks"
73. "What entities are flagged for negative cash flow?"

---

## 🔍 **General Discovery Questions**

74. "What are all the companies mentioned?"
75. "Show me all locations in the document"
76. "What financial metrics are tracked?"
77. "Find all monetary values over $1 million"
78. "What are the key dates in the document?"
79. "Show me all entities of type Company"
80. "What are the main topics in this document?"
81. "Summarize the financial position"
82. "What are the key findings?"

---

## 🎯 **Complex Multi-Step Questions (Analytics Engine)**

### Generic Analytics
83. "Group cities by county and show where assets drop by more than 30%"
84. "Find cities where inventory held for resale exceeds materials inventory by 20%"
85. "Which companies have debt-to-asset ratio over 70%?"
86. "Show me loans maturing in 12 months with balance over $1M"
87. "What's the total assets by county for all cities?"
88. "Find companies where revenue is less than 10% of total assets"

### Financial Health Analysis
89. "Show me cities with high assets but low cash reserves" (liquidity_analysis)
90. "Find entities with multiple risk factors"
91. "Which cities are asset rich but cash poor?"
92. "Show companies with declining revenue compared to industry average"
93. "Find loans with high interest rates approaching maturity"
94. "Which entities have concerning debt levels?"

---

## 📈 **Trend & Analysis Questions**

91. "What's the financial health of City Of Columbus?"
92. "Compare the financial position of all cities"
93. "Which city has the best debt-to-assets ratio?"
94. "Show me cities with improving financial metrics"
95. "What are the financial trends?"
96. "Which entities show concerning patterns?"
97. "What's the overall financial summary?"
98. "Identify entities with unusual financial structures"

---

## 🎨 **Demo & Presentation Questions**

### For Quick Demo (30 seconds)
1. "Show me all cities" - Shows entity extraction
2. "What risks were detected?" - Shows risk analysis
3. "How are City Of Columbus and City Of Cleveland connected?" - Shows graph traversal

### For Detailed Demo (5 minutes)
1. "Show me all cities with cash over $10 million"
2. "What are the top 5 cities by total assets?"
3. "Find all relationships for City Of Columbus"
4. "What risks were detected and why?"
5. "Calculate the total debt across all cities"

### For Full Feature Demo (10 minutes)
1. Start with upload → Show progress modal
2. "Show me all entities" → Demonstrate entity extraction
3. "What are the relationships?" → Show graph construction
4. "Find risks" → Show risk detection
5. "How are City X and City Y connected?" → Show graph traversal
6. "What's the total cash?" → Show metric calculation
7. "Show me cities with high debt" → Show complex queries

---

## 🧪 **Testing Questions**

### Graph Traversal Testing
- "Show entities connected to [ENTITY_NAME]"
- "Find path between [ENTITY1] and [ENTITY2]"
- "Show entities with relationship type OWNS"
- "Find entities 2 hops away from [ENTITY_NAME]"

### Edge Cases
- "What entities don't have any relationships?"
- "Show me entities with the longest names"
- "Find duplicate entities"
- "What entities have missing data?"
- "Show me entities with unusual property values"

### Error Handling
- "Find entity that doesn't exist"
- "Show me relationships for unknown entity"
- "What's the path between unrelated entities?"

---

## 💡 **Pro Tips for Testing**

1. **Start Simple**: Begin with basic entity queries
2. **Build Complexity**: Progress to relationship queries
3. **Test Edge Cases**: Try invalid queries to test error handling
4. **Mix Query Types**: Combine entity, relationship, and metric queries
5. **Use Real Data**: Test with actual document names from your uploads

---

## 📝 **Question Categories by Use Case**

### **Loan Risk Assessment**
- "Show me all variable-rate loans"
- "Find loans with high interest rates"
- "What loans are approaching maturity?"
- "Show me loans without collateral"

### **Compliance Audit**
- "What contracts have expired?"
- "Find missing compliance clauses"
- "Show me entities with compliance issues"
- "What are the regulatory requirements?"

### **Financial Analysis**
- "What's the total financial exposure?"
- "Show me entities with declining metrics"
- "Compare financial positions"
- "What are the financial trends?"

### **Invoice Reconciliation**
- "Find unmatched invoices"
- "Show me duplicate invoices"
- "What invoices are overdue?"
- "Calculate total invoice amounts"

---

**Ready to test!** 🚀

