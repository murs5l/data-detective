# 🕵️ Data Detective Report

**Data Health Score: 64/100 (Fair)**

<details>
<summary>Score breakdown</summary>

| Category | Deduction |
|---|---|
| Missing Values | -15.8 |
| Outliers | -15 |
| Skewed Distributions | -5 |

</details>

**Shape:** 1000 rows &times; 10 columns &nbsp;|&nbsp; **Duplicate rows:** 2

## Insights
- 🚨 Column 'notes' has high missingness (86.5%).
- 🆔 Column 'id' looks like an ID (very high uniqueness).
- 🆔 Column 'signup_date' looks like an ID (very high uniqueness).
- 🆔 Column 'email' looks like an ID (very high uniqueness).
- 📊 Column 'income' has 3 potential outlier(s) (MAD method).
- 📊 Column 'score' has 55 potential outlier(s) (MAD method).
- 📅 Column 'signup_date' looks like it contains dates (consider parsing as datetime).
- 📐 Column 'income' is heavily skewed (skew=15.922).
- 📐 Column 'score' is heavily skewed (skew=2.367).

<details>
<summary>Full technical report</summary>

### Missing values (%)
| Column | Value |
|---|---|
| id | 0.0 |
| age | 0.0 |
| income | 3.8 |
| score | 0.0 |
| signup_date | 0.0 |
| category | 0.0 |
| region | 0.0 |
| notes | 86.5 |
| email | 0.0 |
| active | 0.0 |

### Outliers (MAD)
| Column | Value |
|---|---|
| id | 0 |
| age | 0 |
| income | 3 |
| score | 55 |

### Outliers (IQR)
| Column | Value |
|---|---|
| id | 0 |
| age | 0 |
| income | 11 |
| score | 64 |

### High-cardinality columns
- `id`
- `signup_date`
- `email`

### Constant columns
_None found._

### Near-constant columns
_None found._

### Possible target column
_None found._

### Duplicate columns
_None found._

### Correlated pairs
_None found._

### Correlation matrix
| | id | age | income | score |
|---|---|---|---|---|
| **id** | 1.00 | -0.01 | 0.03 | -0.02 |
| **age** | -0.01 | 1.00 | 0.01 | -0.01 |
| **income** | 0.03 | 0.01 | 1.00 | 0.02 |
| **score** | -0.02 | -0.01 | 0.02 | 1.00 |

### Date-like columns
- `signup_date`

### Mixed-type columns
_None found._

### Negative values (unexpected)
_None found._

### Memory usage (KB)
| Column | Value |
|---|---|
| id | 1.95 |
| age | 3.91 |
| income | 7.81 |
| score | 3.91 |
| signup_date | 74.22 |
| category | 56.64 |
| region | 60.36 |
| notes | 35.51 |
| email | 74.11 |
| active | 0.98 |

</details>
